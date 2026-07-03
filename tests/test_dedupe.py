"""Real tests land at Phase 2 with dedupe.py."""

def test_dedupe_module_imports():
    import pulseflow.dedupe  # noqa: F401
