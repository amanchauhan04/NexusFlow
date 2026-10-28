from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict

TaskKind = Literal["echo", "transform", "sleep", "fail_once"]

class TaskSpec(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    kind: TaskKind = "echo"
    payload: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    retries: int = Field(default=1, ge=0, le=5)

class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    tasks: list[TaskSpec] = Field(min_length=1, max_length=100)

class WorkflowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    status: str
    created_at: str
    definition: dict[str, Any]

class RunOut(BaseModel):
    workflow_id: str
    status: str
    message: str
