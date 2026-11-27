#!/usr/bin/env bash
set -euo pipefail

contexto=$(mktemp -d)
trap 'rm -rf "$contexto"' EXIT
cp app.py calculadora.py requirements.txt "$contexto/"
mkdir "$contexto/test"
cp test/test_calculadora.py test/test_app.py "$contexto/test/"
docker build -t calculadora:pytest -f - "$contexto" <<'DOCKERFILE'
FROM python:3.10-slim
WORKDIR /proyecto
COPY requirements.txt .
RUN pip install --no-cache-dir pytest -r requirements.txt
COPY . .
USER 65534:65534
CMD ["python", "-B", "-m", "pytest", "-p", "no:cacheprovider", "-v"]
DOCKERFILE
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:rw,nosuid,size=32m --memory 256m --pids-limit 64 calculadora:pytest
