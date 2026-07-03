"""Real tests land at Phase 2 with workflow.py (full pipeline, all externals mocked)."""

def test_workflow_module_imports():
    import pulseflow.workflow  # noqa: F401
