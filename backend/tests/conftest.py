import pytest


@pytest.fixture(autouse=True)
def writable_by_default(monkeypatch):
    # Der Nur-Lesen-Modus ist standardmäßig aktiv; die bestehenden Tests prüfen
    # Schreib-Endpunkte und laufen deshalb im Schreibmodus.
    monkeypatch.setenv("CBKS_READ_ONLY", "0")
