# BillingPulse

Automate medical billing insurance calls with AI. Phase 1 implementation.

**Developed by:** [siripuramGanesh](https://github.com/siripuramGanesh)

## Quick start

### 1. Start database

```bash
docker-compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### 4. Register & use

1. Register with email, password, practice name
2. Complete practice details (Practice page)
3. Add payers (insurance companies + phone numbers)
4. Upload claims via CSV or Excel

## CSV/Excel format

Columns (flexible naming):

- `claim_number` / `claim_no` / `claim#`
- `patient_name` / `patient`
- `patient_dob` / `dob`
- `date_of_service` / `dos`
- `amount` / `balance`
- `denial_reason` / `denial`
- `denial_code` / `code`
- `payer_id` (or pass as query param when uploading)

## Phase 2: Voice & Telephony

1. Create a [Vapi](https://vapi.ai) account
2. Create an assistant in Vapi dashboard (or use a transient one)
3. Import a Twilio phone number into Vapi (or use a free Vapi number)
4. Add to `.env`:
   - `VAPI_API_KEY`
   - `VAPI_ASSISTANT_ID`
   - `VAPI_PHONE_NUMBER_ID`
5. Configure webhook in Vapi: Set Server URL to `https://your-domain/api/webhooks/vapi`
   - Enable: `end-of-call-report`, `status-update`
6. For local dev, use [ngrok](https://ngrok.com) to expose your backend: `ngrok http 8000`

## Phase 5: Dashboard & Real-Time UI

- Metrics API: calls/day, resolution rate, revenue recovered
- Dashboard: enhanced with metrics, charts, in-progress calls
- Call detail: modal with full transcript and AI summary
- Real-time: polling every 5–10s on Claims and Calls pages
- Search: claim # or patient name on Claims page

## Phase 4: Call Queue

1. Start Redis: `docker-compose up -d redis` (or full `docker-compose up -d`)
2. Start Celery worker: `cd backend && celery -A app.celery_app worker --loglevel=info`
3. Use "Call selected" on Claims page to queue multiple claims for background calls
4. Rate limit: 2 calls per payer per 5 minutes (configurable in config)

## Phase 3: Agentic AI

1. Run migration: `cd backend && alembic upgrade head`
2. Add `OPENAI_API_KEY` to `.env` for LLM-based outcome extraction
2. When a call ends, the system automatically:
   - Extracts claim status, denial reason, next steps from the transcript
   - Updates the claim with the extracted data
   - Stores the extraction in the call record
3. Add IVR notes to payers (Practice → Payers) so the AI knows how to navigate menus

## Phase 6: Payer Intelligence, RAG & Scheduling

1. **RAG (denial codes & payer policies)**  
   - Chroma + OpenAI embeddings store denial code and payer policy knowledge.  
   - Ingest via API: `POST /api/rag/denial-codes` (body: `{"entries": [{"code": "CO-16", "description": "...", "remedy": "..."}]}`),  
     `POST /api/rag/payer-policies` (body: `{"entries": [{"payer_name": "Aetna", "text": "..."}]}`).  
   - Outcome extraction automatically queries RAG using the claim’s denial code and payer name to improve extraction.

2. **Structured IVR config**  
   - Payers support an `ivr_config` JSON field:  
     `{"steps": [{"prompt": "Press 1 for claims", "options": {"1": "claims", "2": "billing"}}]}`.  
   - If set, the call context uses this instead of the free-text `ivr_notes`.

3. **Scheduled follow-up calls**  
   - `POST /api/scheduled-calls` – schedule a call for a claim (`claim_id`, `call_after`, optional `reason`).  
   - `GET /api/scheduled-calls` – list (optional `claim_id` filter).  
   - `DELETE /api/scheduled-calls/{id}` – cancel.  
   - Run **Celery Beat** so due scheduled calls are enqueued:  
     `celery -A app.celery_app beat --loglevel=info`  
   - Beat runs `process_scheduled_calls` every 60 seconds.

4. **Migrations**  
   - Run `alembic upgrade head` to add `scheduled_calls` table and `ivr_config` on payers.

## Workflows

Post-call processing is implemented as a **LangGraph workflow** (`backend/app/workflows/post_call_workflow.py`):

1. **Extract** – LLM + RAG outcome extraction from the transcript.
2. **Apply** – Update claim and call record.
3. **Decide follow-up** – If the extraction says to call back (e.g. "call back in 3 days"), set a follow-up date.
4. **Schedule** – Create a `ScheduledCall` so Celery Beat will queue the call when due.

So when a rep says "we’ll reprocess; call back in 5 days", the workflow will create a scheduled follow-up call automatically. See `backend/app/workflows/README.md` for extension points.

## Email (claimer notifications)

After each call, the practice (claimer) receives an email with the call outcome (claim #, patient, payer, status, summary, next steps).

1. **Configure SMTP** in `.env`: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM_EMAIL`, `MAIL_FROM_NAME`. See `.env.example`.
2. **Recipients**: Set **Practice → Notification email** (one address for all call alerts), or leave blank to send to all active users in the practice.
3. **Claim**: When an email is sent, the claim’s `claimer_notified_at` is set (exposed in API and optional in UI).

If SMTP is not configured, the workflow still runs but no email is sent.

## Phase 7: Compliance, Reporting & Scale

1. **Audit logs** – Actions (login, claim update/delete, call initiate) are logged with practice, user, resource, and optional IP. `GET /api/audit` lists logs for the practice (filter by `action`, `resource_type`).

2. **Access** – Users have a `role` (`staff` | `admin`). Exposed in `GET /api/auth/me`. All list/detail APIs remain practice-scoped.

3. **Encryption at rest** – Set `ENCRYPT_SENSITIVE_FIELDS=true` and `ENCRYPTION_KEY` (Fernet key). Claim fields `notes` and `denial_reason` are encrypted in the DB and decrypted when returned. Generate a key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

4. **Reporting** – `GET /api/reports/denial-trends?days=90` – denial code counts. `GET /api/reports/payer-performance?days=90` – per-payer resolution rate and call counts. `GET /api/reports/export/claims?format=csv` or `format=xlsx` – export claims (decrypted).

5. **Production** – `APP_ENV` (development | staging | production). `GET /health` – liveness. `GET /health/ready` – DB and Redis connectivity. Every response includes `X-Request-ID`. Optional `SENTRY_DSN` for error tracking.

**MCP option:** Set `USE_MCP_EMAIL=true` to send email via the built-in MCP email server: the app spawns `python -m app.mcp_email_server` as a subprocess and calls the `send_email` tool. The same SMTP env vars are passed into the server. You can also run the MCP server from your IDE (add to MCP config) to send emails from the agent.

## Git / Contributing

- **Commit messages:** Use neutral wording only; do not reference any specific IDE or product names.

## API docs

http://localhost:8000/docs
