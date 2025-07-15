def test_app_creation(app):
    """Test that the Flask app can be created successfully."""
    assert app is not None
    assert app.config["TESTING"] is True
    assert app.config["WTF_CSRF_ENABLED"] is False
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"

    # Check that essential Flask app attributes exist
    assert app.name == "app"
    assert hasattr(app, "route")
    assert hasattr(app, "test_client")
