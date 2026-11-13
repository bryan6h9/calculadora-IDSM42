import subprocess
import sys


def test_calculadora_desde_la_consola():
    proceso = subprocess.run(
        [sys.executable, "app.py"],
        input="1\n2\n3\n5\n",
        text=True,
        capture_output=True,
        check=True,
        timeout=5,
    )

    assert "Resultado: 5.0" in proceso.stdout
