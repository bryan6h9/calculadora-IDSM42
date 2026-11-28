import json
from io import StringIO

import revisor


def test_terminal_review_and_iteration(monkeypatch, tmp_path, capsys):
    original = tmp_path / "original.js"
    original.write_text("let x = 1;\n")
    saved = tmp_path / "propuesta.js"
    monkeypatch.setenv("GEMINI_API_KEY", "clave-de-prueba")
    choices = iter([
        "2", str(original), "4", "Usa const", "s",
        "7", str(original), "7", str(saved), "6",
        "3", "", "s", "1", "Python", "print(1)", ":fin", "3", "", "s", "0",
    ])
    monkeypatch.setattr("builtins.input", lambda *args: next(choices))
    calls = []

    def fake_response(request, timeout):
        payload = json.loads(request.data)
        context = json.loads(payload["contents"][0]["parts"][0]["text"])
        calls.append(context)
        assert request.get_header("X-goog-api-key") == "clave-de-prueba"
        proposal = "const x = 1;\n" if context["modo"] == "propuesta" else ""
        return StringIO(json.dumps({"candidates": [{
            "finishReason": "STOP", "content": {"parts": [{
                "text": json.dumps({"diagnostico": "Revisión recibida", "codigo": proposal}),
            }]},
        }]}))

    monkeypatch.setattr(revisor, "urlopen", fake_response)
    revisor.main()
    assert original.read_text() == "let x = 1;\n"
    assert saved.read_text() == "const x = 1;\n"
    assert [call["codigo"] for call in calls] == [
        "let x = 1;\n", "const x = 1;\n", "print(1)\n",
    ]
    output = capsys.readouterr().out
    assert "+const x = 1;" in output
    assert "Esa ruta ya existe." in output
    assert "clave-de-prueba" not in output
