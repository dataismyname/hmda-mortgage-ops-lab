from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Fail loudly if any test tries to hit the network."""
    import socket

    def guard(*a, **k):
        raise RuntimeError("Network access is not allowed in unit tests")

    monkeypatch.setattr(socket, "create_connection", guard)
    monkeypatch.setattr(socket.socket, "connect", guard)
