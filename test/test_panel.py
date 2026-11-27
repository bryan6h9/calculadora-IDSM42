from unittest.mock import Mock

import pytest

from panel.app import GitHub, GitHubError, REPO, create_app, verify_merge
from scripts.propuesta import parse


@pytest.fixture
def panel(monkeypatch):
    monkeypatch.setenv("PANEL_KEY", "demo")
    monkeypatch.setenv("PANEL_REF", "main")
    client = create_app().test_client()
    csrf = client.get("/api/sesion").json["csrf"]
    return client, {"Origin": "http://localhost", "X-CSRF": csrf, "X-Panel-Key": "demo"}


def test_dispatch_allowlist_and_guards(panel, monkeypatch):
    client, headers = panel
    dispatch = Mock(return_value={"url": "https://github.com/" + REPO})
    monkeypatch.setattr(GitHub, "dispatch", dispatch)
    payload = {"workflow": "correccion-ia.yml", "archivo": "app.py", "solicitud": "  Ajusta los mensajes  "}
    assert client.post("/api/ejecutar", json=payload).status_code == 403
    assert client.post("/api/ejecutar", json=payload, headers={**headers, "X-Panel-Key": ""}).status_code == 403
    assert client.post("/api/ejecutar", json={**payload, "archivo": "../app.py"}, headers=headers).status_code == 400
    assert client.post("/api/ejecutar", json={**payload, "workflow": "otro.yml"}, headers=headers).status_code == 400
    dispatch.assert_not_called()
    response = client.post("/api/ejecutar", json=payload, headers=headers)
    assert response.status_code == 200
    dispatch.assert_called_once_with("correccion-ia.yml", "main", {
        "archivo": "app.py", "solicitud": "Ajusta los mensajes", "simulacion": "true",
    })


def test_demo_blocks_publication(panel, monkeypatch):
    client, headers = panel
    monkeypatch.setenv("PANEL_REF", "feature/panel-automatizacion")
    response = client.post("/api/ejecutar", json={
        "workflow": "mantenimiento-ia.yml", "archivo": "app.py", "simulacion": False,
    }, headers=headers)
    assert response.status_code == 400


def test_merge_verifies_sha_runs_and_review():
    sha = "a" * 40
    base = "b" * 40
    pr = {"number": 10, "state": "open", "draft": False, "mergeable": True,
          "mergeable_state": "clean", "base": {"ref": "main"},
          "head": {"repo": {"full_name": REPO}, "ref": "gemini/correccion-1", "sha": sha}}
    responses = {
        "/git/ref/heads/main": {"object": {"sha": base}},
        f"/compare/{base}...{sha}": {"merge_base_commit": {"sha": base}},
        "/actions/workflows/test.yml/runs": {"workflow_runs": [{"conclusion": "success"}]},
        "/actions/workflows/contenedor.yml/runs": {"workflow_runs": [{"conclusion": "success"}]},
        f"/commits/{sha}/check-runs": {"total_count": 1, "check_runs": [{"conclusion": "success"}]},
        f"/commits/{sha}/status": {"total_count": 0},
        "/issues/10/comments": [{"user": {"login": "github-actions[bot]"},
                                "body": f"<!-- gemini-revision:{sha} -->\nRevisión"}],
    }
    gh = Mock()
    gh.get.side_effect = lambda path, **kwargs: responses[path]
    verify_merge(gh, pr, sha)
    with pytest.raises(GitHubError, match="cambió"):
        verify_merge(gh, pr, base)
    responses["/actions/workflows/test.yml/runs"]["workflow_runs"][0]["conclusion"] = "failure"
    with pytest.raises(GitHubError, match="test.yml"):
        verify_merge(gh, pr, sha)


def test_parser_handles_diagnosis_and_rejects_multiple_blocks():
    assert parse("Diagnóstico\n```python\nprint(1)\n```", "app.py") == ("Diagnóstico", "print(1)\n")
    with pytest.raises(ValueError):
        parse("```python\npass\n```\n```python\npass\n```", "app.py")
    with pytest.raises(SyntaxError):
        parse("```python\nif\n```", "app.py")


def test_parser_accepts_diagnosis_after_a_single_block():
    assert parse(
        "```python3\nprint(1)\n```\nNota de verificación.", "app.py"
    ) == ("Nota de verificación.", "print(1)\n")
    assert parse("**SIN_CAMBIOS**", "app.py") == ("SIN_CAMBIOS", None)
