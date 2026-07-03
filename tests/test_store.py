"""Real tests land at Phase 2 with store.py (error sanitizer: no secrets in persisted errors)."""

def test_store_module_imports():
    import pulseflow.store  # noqa: F401
