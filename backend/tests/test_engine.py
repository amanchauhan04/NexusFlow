import pytest
from app.engine import validate_dag, WorkflowValidationError, execute_task

def test_valid_dag_returns_topological_order():
    tasks = [{"id":"a","depends_on":[]},{"id":"b","depends_on":["a"]},{"id":"c","depends_on":["a"]}]
    order = validate_dag(tasks)
    assert order.index("a") < order.index("b") and order.index("a") < order.index("c")

def test_cycle_rejected():
    with pytest.raises(WorkflowValidationError, match="cycle"):
        validate_dag([{"id":"a","depends_on":["b"]},{"id":"b","depends_on":["a"]}])

def test_unknown_dependency_rejected():
    with pytest.raises(WorkflowValidationError, match="unknown dependencies"):
        validate_dag([{"id":"a","depends_on":["missing"]}])

def test_transform_task():
    assert execute_task({"kind":"transform","payload":{"value":6,"multiplier":7}}, {})["value"] == 42
