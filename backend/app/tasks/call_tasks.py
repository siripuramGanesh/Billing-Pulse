"""Celery tasks for call queue and scheduled calls."""

import asyncio
from datetime import datetime, timezone

from app.celery_app import celery_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models import Claim, Payer, Call, ScheduledCall
from app.services.vapi_service import create_outbound_call
from app.agents.call_context import build_call_system_prompt, build_first_message

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Rate limit: max calls per payer per window (seconds)
RATE_LIMIT_WINDOW = 300  # 5 minutes
RATE_LIMIT_MAX_CALLS_PER_PAYER = 2


def _check_rate_limit(payer_id: int) -> bool:
    """Check if we can call this payer (rate limit). Returns True if allowed."""
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        key = f"call_rate:payer:{payer_id}"
        current = r.get(key)
        if current is None:
            return True
        if int(current) >= RATE_LIMIT_MAX_CALLS_PER_PAYER:
            return False
        return True
    except Exception:
        return True  # Allow on Redis error


def _increment_rate_limit(payer_id: int) -> None:
    """Increment rate limit counter for payer."""
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        key = f"call_rate:payer:{payer_id}"
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, RATE_LIMIT_WINDOW)
        pipe.execute()
    except Exception:
        pass


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def initiate_call_for_claim(self, claim_id: int):
    """
    Initiate an outbound call for a claim. Runs in Celery worker.
    Retries on failure with exponential backoff.
    """
    db = Session()
    try:
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            return {"status": "error", "message": "Claim not found"}

        # Skip if already in progress
        if claim.status == "in_progress":
            return {"status": "skipped", "message": "Claim already in progress"}

        payer = db.get(Payer, claim.payer_id)
        if not payer or not payer.phone:
            return {"status": "error", "message": "Payer has no phone number"}

        # Rate limit check
        if not _check_rate_limit(payer.id):
            raise self.retry(countdown=120)  # Retry in 2 min when rate limited

        claim_context = {
            "system_prompt": build_call_system_prompt(claim, payer),
            "first_message": build_first_message(claim, payer),
        }

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                create_outbound_call(
                    customer_phone=payer.phone,
                    claim_context=claim_context,
                    metadata={
                        "claim_id": str(claim.id),
                        "claim_number": claim.claim_number,
                        "practice_id": str(claim.practice_id),
                    },
                )
            )
        finally:
            loop.close()

        external_id = result.get("id") or result.get("callId") or str(result)
        if isinstance(external_id, dict):
            external_id = external_id.get("id", str(external_id))

        call = Call(
            claim_id=claim.id,
            status="initiated",
            external_id=str(external_id),
        )
        db.add(call)
        claim.status = "in_progress"
        _increment_rate_limit(payer.id)
        db.commit()

        return {"status": "ok", "call_id": call.id, "external_id": str(external_id)}
    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task
def process_scheduled_calls():
    """
    Find scheduled_calls with call_after <= now, enqueue initiate_call_for_claim for each,
    then delete the scheduled row. Run periodically via Celery Beat (e.g. every minute).
    """
    db = Session()
    try:
        now = datetime.now(timezone.utc)
        due = (
            db.query(ScheduledCall)
            .filter(ScheduledCall.call_after <= now)
            .all()
        )
        for row in due:
            initiate_call_for_claim.delay(row.claim_id)
            db.delete(row)
        db.commit()
        return {"processed": len(due)}
    finally:
        db.close()
