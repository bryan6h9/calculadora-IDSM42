# Calculadora y panel de automatización

La calculadora HTML se publica en GitHub Pages, Azure y GHCR. El panel Flask se
ejecuta localmente y usa GitHub Actions para operar el proyecto.

## Demostración en Mac

```bash
git clone https://github.com/bryan6h9/calculadora-IDSM42.git
cd calculadora-IDSM42
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
open -e .env
```

En el archivo local, rellena `PANEL_GITHUB_TOKEN` y opcionalmente `PANEL_KEY`.
Deja `PANEL_REF=main` para usar todo el flujo. El valor `feature/panel-automatizacion`
permite probar los workflows IA de esa rama en simulación, siempre que el
workflow con ese nombre ya exista en la rama predeterminada de GitHub.

```bash
set -a
source .env
set +a
python -m flask --app panel.app:create_app run --host 127.0.0.1 --port 5050
```

Abre [el panel local](http://127.0.0.1:5050). Si configuraste `PANEL_KEY`,
escríbela en el panel para habilitar los envíos. Usa la interfaz solo en
loopback. No actives el modo debug y no publiques el servidor. El panel requiere
origen local y token CSRF para solicitudes de escritura.

## Permisos

Crea un token fine-grained para **solo este repositorio**. Asigna Actions
read/write, Pull requests read/write, Issues read/write y Metadata read.
Asigna Contents read/write para que el botón **Aprobar merge** pueda usar la API
de merge. Si solo vas a demostrar simulación, basta Contents read. La creación
de ramas, commits y PR ocurre en Actions con `GITHUB_TOKEN`. Permite que
GitHub Actions cree pull requests en **Settings → Actions → General**.

La revisión requiere el secreto de Actions `GOOGLE_API_KEY`. Pages usa GitHub
Actions como origen. Azure requiere las credenciales OIDC y la aplicación
`practica-azure` configuradas en GitHub y Azure. El registry usa el token de
Actions con permisos de escritura de paquetes. Para evitar cambios concurrentes
en la base durante un merge, configura en GitHub comprobaciones obligatorias y
ramas actualizadas, y evita excepciones de bypass para el usuario del token.

## Ciclo de mantenimiento

1. Elige archivo y describe el problema. Empieza con **Solo probar propuesta**
   o con **Ejecutar mantenimiento IA** en simulación.
2. Abre los pasos de la ejecución en el historial. Cuando aparezca el artifact,
   pulsa **Ver resultado** para consultar el diagnóstico y el diff. Puedes
   crear un Issue a partir del diagnóstico.
3. Para una simulación exitosa sobre el SHA actual de main, **Aprobar cambio y
   abrir PR** publica el mismo archivo que se validó. Si desactivas simulación
   antes de iniciar, el workflow abre el PR tras validar. Abrir el PR activa
   pruebas, comprobación Docker y revisión Gemini del commit exacto. GitHub
   también puede solicitar aprobación de las ejecuciones asociadas al propio
   evento del PR. Si aparece ese aviso y bloquea la integración, selecciona
   **Approve workflows to run** en el PR.
4. Revisa el PR. **Aprobar merge** exige coincidencia del SHA mostrado, base
   actual, pruebas y Docker exitosos, revisión Gemini y conformidad con las
   reglas de GitHub. El merge usa el token local y el evento push inicia
   Pages, GHCR y Azure. Sus ejecuciones se pueden seguir o iniciar por separado
   desde el panel.
5. **Rechazar PR** cierra un PR sin integrarlo. Descartar una simulación cierra
   su vista y conserva el artifact. El modo demo trabaja sobre una simulación
   o rama feature, sin introducir fallos en main.

En una propuesta Python se comprueba sintaxis y se ejecuta pytest en un
contenedor sin red y sin credenciales. Para la calculadora web se comprueba el
empaquetado y el workflow de GHCR verifica el contenido servido por HTTP.

```bash
python -m pip install pytest
python -m pytest -v
```
