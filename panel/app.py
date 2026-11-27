"""Panel local para el repositorio de la calculadora."""
import hmac
import io
import os
import re
import secrets
import zipfile

import requests
from flask import Flask, abort, jsonify, request, session

REPO = "bryan6h9/calculadora-IDSM42"
REPO_URL = f"https://github.com/{REPO}"
FILES = {"index.html", "calculadora.py", "app.py"}
WORKFLOWS = {
    "analisis-ia.yml", "correccion-ia.yml", "mantenimiento-ia.yml",
    "publicar-propuesta.yml", "test.yml", "contenedor.yml",
    "deploy.yml", "main_practica-azure.yml",
}
AI = {"analisis-ia.yml", "correccion-ia.yml", "mantenimiento-ia.yml"}
ARTIFACT_FILES = {
    "propuesta-gemini": {"propuesta.txt", "diagnostico.txt", "cambio.diff"},
    "revision-gemini": {"revision.md"},
}
LIMIT = 512 * 1024


class GitHubError(Exception):
    pass


class GitHub:
    def __init__(self, token):
        self.token = token

    def call(self, path="", method="GET", **kwargs):
        if not self.token:
            raise GitHubError("Configura PANEL_GITHUB_TOKEN para conectar el panel.")
        try:
            response = requests.request(
                method, f"https://api.github.com/repos/{REPO}{path}",
                headers={"Authorization": f"Bearer {self.token}",
                         "Accept": "application/vnd.github+json",
                         "X-GitHub-Api-Version": "2022-11-28"},
                timeout=(5, 15), allow_redirects=False, **kwargs,
            )
        except requests.RequestException:
            raise GitHubError("No se pudo conectar con GitHub.") from None
        if not response.ok:
            messages = {401: "Token inválido o caducado.", 403: "Revisa los permisos del token y los límites de API.",
                        404: "Recurso ausente o sin acceso.", 405: "GitHub bloqueó la operación con sus reglas.",
                        409: "El estado del repositorio cambió. Actualiza el panel.",
                        422: "GitHub rechazó la operación. Revisa la rama, el workflow y las reglas del repositorio."}
            raise GitHubError(f"GitHub ({response.status_code}). {messages.get(response.status_code, '')}")
        return response

    def get(self, path="", **params):
        return self.call(path, params=params).json()

    def dispatch(self, workflow, ref="main", inputs=None):
        response = self.call(
            f"/actions/workflows/{workflow}/dispatches", "POST",
            json={"ref": ref, "inputs": inputs or {}},
        )
        result = response.json() if response.content else {}
        return {"url": result.get("html_url") or result.get("workflow_run_url")
                or f"{REPO_URL}/actions/workflows/{workflow}"}

    def files(self, artifact):
        response = self.call(f"/actions/artifacts/{artifact['id']}/zip")
        url = response.headers.get("Location", "")
        if not url.startswith("https://"):
            raise GitHubError("GitHub no devolvió un enlace de descarga seguro.")
        try:
            with requests.get(url, timeout=(5, 15), stream=True, allow_redirects=False) as download:
                if download.status_code != 200:
                    raise GitHubError("No se pudo descargar el artifact.")
                data = bytearray()
                for chunk in download.iter_content(16384):
                    data.extend(chunk)
                    if len(data) > LIMIT:
                        raise GitHubError("El artifact supera el tamaño permitido.")
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                allowed = ARTIFACT_FILES[artifact["name"]]
                return {item.filename: archive.read(item).decode("utf-8", "replace")
                        for item in archive.infolist()
                        if item.filename in allowed and item.file_size <= LIMIT}
        except (requests.RequestException, zipfile.BadZipFile, RuntimeError):
            raise GitHubError("El artifact no está disponible o no se puede leer.") from None


def proposal_branch(pr):
    return (pr["head"]["repo"] or {}).get("full_name") == REPO and re.fullmatch(
        r"gemini/correccion-\d+(?:-\d+)?", pr["head"]["ref"]
    ) and pr["base"]["ref"] == "main"


def verify_merge(gh, pr, sha):
    if not proposal_branch(pr) or pr["state"] != "open" or pr["draft"] or pr["head"]["sha"] != sha:
        raise GitHubError("El PR no es una propuesta abierta o cambió desde tu revisión.")
    if pr["mergeable"] is not True or pr["mergeable_state"] != "clean":
        raise GitHubError("GitHub aún no declara el PR listo para integrar. Revisa conflictos, reglas y aprobaciones.")
    base = gh.get("/git/ref/heads/main")["object"]["sha"]
    if gh.get(f"/compare/{base}...{sha}")["merge_base_commit"]["sha"] != base:
        raise GitHubError("main avanzó. Genera otra propuesta sobre la versión actual.")
    for workflow in ("test.yml", "contenedor.yml"):
        runs = gh.get(f"/actions/workflows/{workflow}/runs", head_sha=sha, per_page=1)["workflow_runs"]
        if not runs or runs[0]["conclusion"] != "success":
            raise GitHubError(f"Falta una ejecución exitosa de {workflow} para este commit.")
    checks = gh.get(f"/commits/{sha}/check-runs", filter="latest", per_page=100)
    if checks["total_count"] > len(checks["check_runs"]) or any(
        check["conclusion"] not in {"success", "neutral", "skipped"}
        for check in checks["check_runs"]
    ):
        raise GitHubError("Hay comprobaciones pendientes o fallidas. Revisa el PR.")
    combined = gh.get(f"/commits/{sha}/status")
    if combined["total_count"] and combined["state"] != "success":
        raise GitHubError("Hay estados de CI pendientes o fallidos.")
    comments = gh.get(f"/issues/{pr['number']}/comments", per_page=100,
                      sort="created", direction="desc")
    if not any(comment["user"]["login"] == "github-actions[bot]"
               and comment["body"].startswith(f"<!-- gemini-revision:{sha} -->\n")
               for comment in comments):
        raise GitHubError("Falta la revisión de Gemini para el commit mostrado.")


def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.update(SECRET_KEY=secrets.token_hex(32), MAX_CONTENT_LENGTH=16384,
                      SESSION_COOKIE_SAMESITE="Strict", SESSION_COOKIE_HTTPONLY=True,
                      TRUSTED_HOSTS=["127.0.0.1", "localhost", "::1"])
    gh = GitHub(os.getenv("PANEL_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN"))

    @app.before_request
    def protect():
        if request.remote_addr not in {"127.0.0.1", "::1"}:
            abort(403)
        if request.method == "POST":
            if request.headers.get("Origin") != request.host_url.rstrip("/"):
                abort(403)
            expected = session.get("csrf")
            if not expected or not hmac.compare_digest(expected, request.headers.get("X-CSRF", "")):
                abort(403)
            key = os.getenv("PANEL_KEY")
            if key and not hmac.compare_digest(key.encode(), request.headers.get("X-Panel-Key", "").encode()):
                abort(403, "PANEL_KEY incorrecta.")

    @app.after_request
    def secure(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        return response

    @app.errorhandler(GitHubError)
    def github_error(error):
        app.logger.warning("Operación GitHub rechazada en %s", request.endpoint)
        return jsonify(error=str(error)), 502

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(415)
    def invalid(error):
        return jsonify(error=str(error.description)), error.code

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.get("/api/estado")
    def status():
        repo = gh.get()
        return jsonify(
            repo={key: repo[key] for key in ("full_name", "default_branch", "html_url", "updated_at")},
            workflows=gh.get("/actions/workflows", per_page=50)["workflows"],
            runs=gh.get("/actions/runs", per_page=25)["workflow_runs"],
            prs=gh.get("/pulls", state="all", per_page=25),
        )

    @app.get("/api/sesion")
    def login():
        return jsonify(csrf=session.setdefault("csrf", secrets.token_hex(32)),
                       key_required=bool(os.getenv("PANEL_KEY")), ref=os.getenv("PANEL_REF", "main"))

    @app.post("/api/ejecutar")
    def dispatch():
        data = request.get_json()
        if not isinstance(data, dict) or not isinstance(data.get("workflow"), str):
            abort(400, "Solicitud inválida.")
        workflow = data["workflow"]
        if workflow not in WORKFLOWS:
            abort(400, "Workflow fuera del panel.")
        inputs = {}
        ref = "main"
        if workflow in AI:
            ref = os.getenv("PANEL_REF", "main")
            if not re.fullmatch(r"main|feature/[a-zA-Z0-9_-]{1,80}", ref):
                abort(400, "PANEL_REF debe ser main o una rama feature/ válida.")
            filename = data.get("archivo")
            if not isinstance(filename, str) or filename not in FILES:
                abort(400, "Archivo no permitido.")
            inputs["archivo"] = filename
        if workflow in AI - {"analisis-ia.yml"}:
            simulate = data.get("simulacion", True)
            if not isinstance(simulate, bool) or (ref != "main" and not simulate):
                abort(400, "Una rama de demostración solo permite simulación.")
            inputs["simulacion"] = str(simulate).lower()
        if workflow == "correccion-ia.yml":
            instruction = data.get("solicitud")
            if not isinstance(instruction, str) or not 1 <= len(instruction.strip()) <= 2000:
                abort(400, "Describe el cambio en 1 a 2000 caracteres.")
            inputs["solicitud"] = instruction.strip()
        if workflow == "publicar-propuesta.yml":
            source = data.get("origen")
            if type(source) is not int or source < 1:
                abort(400, "Selecciona una ejecución de propuesta válida.")
            inputs["origen"] = str(source)
        return jsonify(gh.dispatch(workflow, ref, inputs))

    @app.get("/api/runs/<int:run>")
    def run_details(run):
        path = f"/actions/runs/{run}"
        artifacts = gh.get(path + "/artifacts", per_page=30)["artifacts"]
        return jsonify(run=gh.get(path), jobs=gh.get(path + "/jobs", per_page=40)["jobs"],
                       artifacts=[{"id": item["id"], "name": item["name"],
                                   "url": f"{REPO_URL}/actions/runs/{run}/artifacts/{item['id']}",
                                   "preview": item["name"] in ARTIFACT_FILES and not item["expired"]}
                                  for item in artifacts])

    @app.get("/api/runs/<int:run>/artifacts/<int:artifact_id>")
    def artifact_details(run, artifact_id):
        data = gh.get(f"/actions/runs/{run}/artifacts", per_page=30)
        for artifact in data["artifacts"]:
            if artifact["id"] == artifact_id and artifact["name"] in ARTIFACT_FILES and not artifact["expired"]:
                return jsonify(gh.files(artifact))
        abort(400, "Artifact fuera del alcance o caducado.")

    @app.post("/api/issues")
    def issue():
        data = request.get_json()
        if not isinstance(data, dict):
            abort(400, "Solicitud inválida.")
        title, body = data.get("title"), data.get("body")
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 150:
            abort(400, "Escribe un título de hasta 150 caracteres.")
        if not isinstance(body, str) or not 1 <= len(body.strip()) <= 7000:
            abort(400, "Escribe una descripción de hasta 7000 caracteres.")
        result = gh.call("/issues", "POST", json={"title": title.strip(), "body": body.strip()}).json()
        return jsonify(url=result["html_url"])

    @app.post("/api/prs/<int:number>/<any(merge,rechazar):decision>")
    def decide(number, decision):
        data = request.get_json()
        sha = data.get("sha") if isinstance(data, dict) else None
        if not isinstance(sha, str) or not re.fullmatch("[0-9a-f]{40}", sha):
            abort(400, "Selecciona el commit actual del PR.")
        pr = gh.get(f"/pulls/{number}")
        if not proposal_branch(pr) or pr["head"]["sha"] != sha or pr["state"] != "open":
            abort(400, "El PR cambió o está fuera del flujo de propuestas.")
        if decision == "rechazar":
            gh.call(f"/pulls/{number}", "PATCH", json={"state": "closed"})
        else:
            verify_merge(gh, pr, sha)
            result = gh.call(f"/pulls/{number}/merge", "PUT",
                             json={"sha": sha, "merge_method": "merge"}).json()
            if not result.get("merged"):
                raise GitHubError("GitHub no confirmó el merge. Revisa el PR.")
        return jsonify(url=pr["html_url"])

    return app
