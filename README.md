# NexusFlow — Intelligent Workflow Orchestration Platform

NexusFlow is a portfolio-grade workflow automation platform built around a FastAPI API, a SQLite-backed job store, a dependency-aware workflow engine, retries, event logs, and a React dashboard.

> Status: MVP / educational reference implementation. Not production-hardened for multi-tenant or mission-critical workloads.

## Highlights
- Define workflows as directed acyclic graphs (DAGs) of tasks
- Validate dependencies and reject cycles before execution
- Execute ready tasks concurrently with configurable worker limits
- Retry transient task failures with exponential backoff
- Track workflow/task states and append-only execution events
- REST API with OpenAPI docs
- React dashboard for creating, running, and inspecting workflows
- Docker Compose setup and automated tests

## Quick start (backend)
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs.

## Quick start (frontend)
```bash
cd frontend
npm install
npm run dev
```
Open the URL printed by Vite. Set `VITE_API_URL=http://127.0.0.1:8000` if needed.

## Docker
```bash
docker compose up --build
```

## Example workflow
```json
{
  "name": "daily-analytics",
  "tasks": [
    {"id":"extract","kind":"echo","payload":{"message":"extract data"},"depends_on":[]},
    {"id":"transform","kind":"transform","payload":{"value":21,"multiplier":2},"depends_on":["extract"]},
    {"id":"report","kind":"echo","payload":{"message":"publish report"},"depends_on":["transform"]}
  ]
}
```
Create with `POST /workflows`, then run with `POST /workflows/{workflow_id}/run`.

## Built-in task kinds
- `echo`: returns the payload
- `transform`: multiplies numeric `value` by `multiplier`
- `sleep`: sleeps for `seconds` (max 10 seconds)
- `fail_once`: intentionally fails on the first attempt to demonstrate retries

## API overview
- `GET /health`
- `POST /workflows`
- `GET /workflows`
- `GET /workflows/{workflow_id}`
- `POST /workflows/{workflow_id}/run`
- `GET /workflows/{workflow_id}/events`
- `GET /metrics`

## Roadmap
- [ ] PostgreSQL + Alembic migrations
- [ ] Redis-backed distributed workers
- [ ] OAuth / RBAC and per-workspace tenancy
- [ ] WebSocket live updates
- [ ] Cron scheduling
- [ ] OpenTelemetry tracing and Prometheus exporter
- [ ] Secrets manager integration
- [ ] Plugin SDK and task sandboxing

## Security notes
Do not expose this demo API directly to the public internet. Add authentication, rate limits, secrets handling, and task isolation before production use.

## License
MIT
