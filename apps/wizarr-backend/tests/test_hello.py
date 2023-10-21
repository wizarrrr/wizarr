"""Hello unit test module."""

from wizarr_backend.hello import hello


def test_hello():
    """Test the hello function."""
    assert hello() == "Hello wizarr-backend"
