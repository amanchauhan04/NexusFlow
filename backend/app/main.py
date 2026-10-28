import json, os
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from .db import Base, engine, get_db, SessionLocal
from .models import Workflow, TaskRun, Event
from .schemas import WorkflowCreate
from .engine import validate_dag, WorkflowValidationError, run_workflow
Base.metadata.create_all(bind=engine)
app = FastAPI(title="NexusFlow API", version="1.0.0", description="Dependency-aware workflow orchestration demo.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
def serialize_workflow(w): return {"id": w.id, "name": w.name, "status": w.status, "created_at": w.created_at, "definition": json.loads(w.definition)}
@app.get("/health")
def health(): return {"status": "ok", "service": "nexusflow-api"}
@app.post("/workflows", status_code=201)
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)):
    definition = payload.model_dump()
    try: validate_dag(definition["tasks"])
    except WorkflowValidationError as exc: raise HTTPException(status_code=422, detail=str(exc))
    workflow = Workflow(name=payload.name, definition=json.dumps(definition)); db.add(workflow); db.commit(); db.refresh(workflow); return serialize_workflow(workflow)
@app.get("/workflows")
def list_workflows(db: Session = Depends(get_db)):
    return [serialize_workflow(w) for w in db.scalars(select(Workflow).order_by(Workflow.created_at.desc())).all()]
@app.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str, db: Session = Depends(get_db)):
    workflow = db.get(Workflow, workflow_id)
    if not workflow: raise HTTPException(status_code=404, detail="Workflow not found.")
    runs = db.scalars(select(TaskRun).where(TaskRun.workflow_id == workflow_id)).all()
    return {**serialize_workflow(workflow), "tasks": [{"task_id": r.task_id, "status": r.status, "attempts": r.attempts, "output": json.loads(r.output or "{}"), "error": r.error} for r in runs]}
@app.post("/workflows/{workflow_id}/run")
def run(workflow_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    workflow = db.get(Workflow, workflow_id)
    if not workflow: raise HTTPException(status_code=404, detail="Workflow not found.")
    if workflow.status == "running": raise HTTPException(status_code=409, detail="Workflow is already running.")
    background_tasks.add_task(_run_background, workflow_id); return {"workflow_id": workflow_id, "status": "queued", "message": "Workflow execution queued."}
def _run_background(workflow_id: str):
    db = SessionLocal()
    try:
        workflow = db.get(Workflow, workflow_id)
        if workflow and workflow.status != "running": run_workflow(db, workflow, MAX_WORKERS)
    finally: db.close()
@app.get("/workflows/{workflow_id}/events")
def workflow_events(workflow_id: str, db: Session = Depends(get_db)):
    if not db.get(Workflow, workflow_id): raise HTTPException(status_code=404, detail="Workflow not found.")
    events = db.scalars(select(Event).where(Event.workflow_id == workflow_id).order_by(Event.id.asc())).all()
    return [{"id": e.id, "task_id": e.task_id, "type": e.event_type, "message": e.message, "created_at": e.created_at} for e in events]
@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(Workflow)) or 0
    statuses = {s: db.scalar(select(func.count()).select_from(Workflow).where(Workflow.status == s)) or 0 for s in ("pending", "running", "success", "failed")}
    return {"workflows_total": total, "workflows_by_status": statuses}
