import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.agents.prefrontal import OllamaLLMClient
from backend.services.agents.temporal import OllamaEmbeddingClient
from backend.services.vault_index import _ensure_id
import json


@pytest.fixture(autouse=True)
def fake_ollama(monkeypatch):
    monkeypatch.setattr(OllamaEmbeddingClient, "embed", lambda self, text: [1.0] + [0.0] * 1023)
    monkeypatch.setattr(
        OllamaLLMClient,
        "generate",
        lambda self, prompt, format="": json.dumps({"classification": "document", "entities": []}),
    )


@pytest.fixture()
def ro_client(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setenv("CBKS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("CBKS_VAULT_DIR", str(vault))
    monkeypatch.delenv("CBKS_API_KEY", raising=False)
    monkeypatch.setenv("CBKS_READ_ONLY", "1")
    with TestClient(app) as c:
        yield c, vault


WRITE_CALLS = [
    ("POST", "/notes", {"json": {"text": "x"}}),
    ("POST", "/documents", {"files": {"file": ("a.txt", b"x")}}),
    ("DELETE", "/nodes/abc", {}),
    ("POST", "/dedupe", {}),
    ("PUT", "/vault/file", {"json": {"path": "n.md", "content": "x"}}),
    ("DELETE", "/vault/file", {"params": {"path": "n.md"}}),
    ("POST", "/vault/rename", {"json": {"source": "a.md", "target": "b.md"}}),
    ("POST", "/vault/attachment", {"files": {"file": ("a.png", b"x")}}),
]


@pytest.mark.parametrize("method,path,kwargs", WRITE_CALLS)
def test_write_endpoints_blocked_in_read_only(ro_client, method, path, kwargs):
    client, _ = ro_client
    assert client.request(method, path, **kwargs).status_code == 403


def test_settings_toggle_enables_writes_and_persists(ro_client):
    client, _ = ro_client
    assert client.get("/settings").json() == {"read_only": True}

    assert client.put("/settings", json={"read_only": False}).json() == {"read_only": False}
    assert client.get("/settings").json() == {"read_only": False}
    assert client.put("/vault/file", json={"path": "n.md", "content": "x"}).status_code == 200

    client.put("/settings", json={"read_only": True})
    assert client.put("/vault/file", json={"path": "n.md", "content": "y"}).status_code == 403


def test_scan_does_not_modify_vault_files(ro_client):
    client, vault = ro_client
    note = vault / "n.md"
    note.write_text("Nur Text, keine id")
    client.post("/vault/rescan")
    assert note.read_text() == "Nur Text, keine id"


def test_derived_id_is_stable_and_respects_frontmatter(tmp_path):
    note = tmp_path / "a" / "n.md"
    note.parent.mkdir()
    first, _ = _ensure_id(note, tmp_path, "Text")
    again, _ = _ensure_id(note, tmp_path, "anderer Text")
    assert first == again
    explicit, _ = _ensure_id(note, tmp_path, "---\nid: fest-123\n---\nText")
    assert explicit == "fest-123"
