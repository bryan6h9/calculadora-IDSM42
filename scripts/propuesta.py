"""Convierte una respuesta de Gemini en archivos de revisión, sin ejecutar código."""
import difflib
import json
import os
import re
from pathlib import Path

ALLOWED_FILES = ("index.html", "calculadora.py", "app.py")


def parse(response, filename):
    response = re.split(r"(?m)^========== RETRY ATTEMPT .* ==========$", response)[-1].strip()
    sentinel = re.fullmatch(r"[*_` ]*(SIN_CAMBIOS|FUERA_DE_ALCANCE)[*_` .]*", response)
    if sentinel:
        return sentinel[1], None
    match = re.search(
        r"(?m)^[ \t]*```[ \t]*([a-zA-Z0-9_-]*)[ \t]*\n([\s\S]+?)\n[ \t]*```[ \t]*$",
        response,
    )
    languages = ("", "python", "python3", "py") if filename.endswith(".py") else ("", "html")
    if not match or match[1].lower() not in languages or response.count("```") != 2:
        raise ValueError("Gemini debe devolver un solo bloque con el archivo completo.")
    diagnosis = "\n\n".join(part for part in (
        response[:match.start()].strip(), response[match.end():].strip()
    ) if part)
    code = match[2]
    proposal = code + "\n"
    if filename.endswith(".py"):
        compile(proposal, filename, "exec")
    return diagnosis or "Propuesta de Gemini", proposal


def main():
    filename = os.environ["ARCHIVO"]
    if filename not in ALLOWED_FILES:
        raise ValueError("Archivo fuera del alcance.")
    source = Path(filename).read_text()
    diagnosis, proposal = parse(Path(os.environ["OUTPUT_FILE"]).read_text(), filename)
    directory = Path("revision")
    directory.mkdir()
    (directory / "diagnostico.txt").write_text(diagnosis)
    if proposal is None or proposal == source:
        return
    (directory / "propuesta.txt").write_text(proposal)
    diff = difflib.unified_diff(source.splitlines(True), proposal.splitlines(True),
                                "Antes/" + filename, "Propuesta/" + filename)
    (directory / "cambio.diff").write_text("".join(diff))
    (directory / "metadata.json").write_text(json.dumps({
        "file": filename, "sha": os.environ["GITHUB_SHA"],
    }))
    with open(os.environ["GITHUB_OUTPUT"], "a") as outputs:
        outputs.write("existe=true\n")


if __name__ == "__main__":
    main()
