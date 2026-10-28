import json, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from sqlalchemy.orm import Session
from .models import Workflow, TaskRun, Event
class WorkflowValidationError(ValueError): pass
def validate_dag(tasks: list[dict[str, Any]]) -> list[str]:
    by_id = {task["id"]: task for task in tasks}
    if len(by_id) != len(tasks): raise WorkflowValidationError("Task IDs must be unique.")
    for task in tasks:
        unknown = set(task.get("depends_on", [])) - set(by_id)
        if unknown: raise WorkflowValidationError(f"Task '{task['id']}' has unknown dependencies: {sorted(unknown)}")
        if task["id"] in task.get("depends_on", []): raise WorkflowValidationError(f"Task '{task['id']}' cannot depend on itself.")
    indegree = {task_id: 0 for task_id in by_id}; children = {task_id: [] for task_id in by_id}
    for task in tasks:
        for dep in task.get("depends_on", []): indegree[task["id"]] += 1; children[dep].append(task["id"])
    queue = [key for key, degree in indegree.items() if degree == 0]; order = []
    while queue:
        node = queue.pop(0); order.append(node)
        for child in children[node]:
            indegree[child] -= 1
            if indegree[child] == 0: queue.append(child)
    if len(order) != len(tasks): raise WorkflowValidationError("Workflow contains a dependency cycle.")
    return order
def execute_task(task: dict[str, Any], prior_outputs: dict[str, Any]) -> Any:
    kind, payload = task.get("kind", "echo"), task.get("payload", {})
    if kind == "echo": return payload
    if kind == "transform":
        value, multiplier = payload.get("value", 0), payload.get("multiplier", 1)
        if not isinstance(value, (int, float)) or not isinstance(multiplier, (int, float)): raise ValueError("transform expects numeric 'value' and 'multiplier'.")
        return {"value": value * multiplier, "source": value, "multiplier": multiplier}
    if kind == "sleep":
        seconds = min(max(float(payload.get("seconds", 1)), 0), 10); time.sleep(seconds); return {"slept_seconds": seconds, "completed": True}
    if kind == "fail_once":
        if not task.get("_already_failed"):
            task["_already_failed"] = True; raise RuntimeError("Intentional first-attempt failure for retry demonstration.")
        return {"recovered": True}
    raise ValueError(f"Unsupported task kind: {kind}")
def add_event(db: Session, workflow_id: str, event_type: str, message: str, task_id: str = ""):
    db.add(Event(workflow_id=workflow_id, task_id=task_id, event_type=event_type, message=message)); db.commit()
def _with_retries(task, outputs):
    retries = int(task.get("retries", 1))
    for attempt in range(1, retries + 2):
        try: return execute_task(task, outputs), attempt
        except Exception:
            if attempt > retries: raise
            time.sleep(min(0.1 * (2 ** (attempt - 1)), 1.0))
def run_workflow(db: Session, workflow: Workflow, max_workers: int = 4) -> dict[str, Any]:
    tasks = json.loads(workflow.definition)["tasks"]; validate_dag(tasks)
    workflow.status = "running"; db.commit(); add_event(db, workflow.id, "workflow.started", f"Workflow '{workflow.name}' started.")
    outputs: dict[str, Any] = {}; states = {t["id"]: "pending" for t in tasks}; runs = {}
    for task in tasks:
        run = TaskRun(workflow_id=workflow.id, task_id=task["id"], status="pending"); db.add(run); runs[task["id"]] = run
    db.commit()
    while any(state == "pending" for state in states.values()):
        ready = [t for t in tasks if states[t["id"]] == "pending" and all(states[d] == "success" for d in t.get("depends_on", []))]
        blocked = [t for t in tasks if states[t["id"]] == "pending" and any(states[d] in ("failed", "blocked") for d in t.get("depends_on", []))]
        for task in blocked:
            states[task["id"]] = "blocked"; runs[task["id"]].status = "blocked"; add_event(db, workflow.id, "task.blocked", "Dependency failed; task was not executed.", task["id"])
        if not ready:
            if not blocked and any(s == "pending" for s in states.values()): raise RuntimeError("Scheduler stalled: no runnable tasks remain.")
            continue
        for task in ready: states[task["id"]] = "running"; runs[task["id"]].status = "running"
        db.commit()
        with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(ready)))) as pool:
            futures = {pool.submit(_with_retries, task, outputs): task for task in ready}
            for future in as_completed(futures):
                task = futures[future]; tid = task["id"]
                try:
                    result, attempts = future.result(); outputs[tid] = result; states[tid] = "success"; runs[tid].status = "success"; runs[tid].attempts = attempts; runs[tid].output = json.dumps(result)
                    add_event(db, workflow.id, "task.succeeded", f"Task completed in {attempts} attempt(s).", tid)
                except Exception as exc:
                    states[tid] = "failed"; runs[tid].status = "failed"; runs[tid].error = str(exc); add_event(db, workflow.id, "task.failed", str(exc), tid)
        db.commit()
    workflow.status = "success" if all(s == "success" for s in states.values()) else "failed"; db.commit()
    add_event(db, workflow.id, "workflow.finished", f"Workflow finished with status: {workflow.status}.")
    return {"workflow_id": workflow.id, "status": workflow.status, "outputs": outputs, "tasks": states}
