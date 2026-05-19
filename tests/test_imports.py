def test_backend_modules_import():
    import api.app  # noqa: F401
    import admin.app  # noqa: F401
    import task.worker  # noqa: F401
