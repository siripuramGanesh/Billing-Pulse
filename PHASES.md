# BillingPulse – Build Phases

## Phase 1: Foundation (Current)
- Project structure (backend + frontend)
- PostgreSQL + SQLAlchemy models
- FastAPI backend skeleton
- React + Vite + TypeScript frontend
- Docker Compose for local dev

## Phase 2: Auth & Core Features
- User auth (Supabase Auth or JWT)
- Practice onboarding
- Claim CSV/Excel upload & parsing
- Payer management
- Basic dashboard UI

## Phase 3: Voice AI Integration
- Twilio setup
- Vapi or Bland AI integration
- Real outbound call flow
- Webhook handlers for call events

## Phase 4: Agentic AI Layer
- LangGraph agent for call orchestration
- LLM-powered decision logic
- IVR navigation tools
- Transcript extraction & outcome capture

## Phase 5: Production Ready
- Call queue (Celery + Redis)
- Real-time dashboard updates
- Reporting & analytics
- HIPAA considerations

## Phase 6: Payer Intelligence, RAG & Scheduling
- RAG (Chroma + embeddings): denial codes & payer policies
- Agent–RAG integration in outcome extraction
- Structured IVR config per payer
- Scheduled follow-up calls (API + Celery Beat)
- Post-call workflow (LangGraph): extract → apply → notify → optional schedule

## Phase 7: Compliance, Reporting & Scale
- HIPAA-oriented controls: audit logs, access controls, encryption at rest/transit
- Deeper reporting & analytics: denial trends, payer performance, export (CSV/Excel)
- Production hardening: staging/prod envs, monitoring, error tracking
- Optional: PMS/EHR or third-party API integrations
