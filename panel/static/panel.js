const el = id => document.getElementById(id);
const text = (tag, value) => Object.assign(document.createElement(tag), {textContent: value});
const state = {session: null, selected: null, loading: false, version: 0};
const labels = {success: "correcto", failure: "falló", queued: "en cola",
  completed: "finalizado", in_progress: "en curso", skipped: "omitido",
  cancelled: "cancelado", open: "abierto", closed: "cerrado"};
const label = value => labels[value] || value || "pendiente";

function link(title, url) {
  const item = text("a", title);
  if (typeof url === "string" && url.startsWith("https://github.com/bryan6h9/calculadora-IDSM42")) {
    item.href = url;
    item.target = "_blank";
    item.rel = "noopener noreferrer";
  }
  return item;
}

async function api(path, data) {
  const options = data === undefined ? {} : {
    method: "POST",
    headers: {"Content-Type": "application/json", "X-CSRF": state.session.csrf,
      "X-Panel-Key": el("panel-key").value},
    body: JSON.stringify(data)
  };
  const response = await fetch(path, options);
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || "La solicitud falló.");
  return value;
}

async function action(button, operation) {
  button.disabled = true;
  try {
    await operation();
  } catch (error) {
    el("notice").textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

function report(message, url) {
  el("notice").replaceChildren(message);
  if (url) el("notice").append(" ", link("Abrir en GitHub", url));
}

function statusBadge(value) {
  const badge = text("span", label(value));
  badge.className = "status-badge";
  badge.dataset.status = value || "pending";
  return badge;
}

function addButton(parent, title, operation) {
  const button = text("button", title);
  button.addEventListener("click", () => action(button, operation));
  parent.append(button);
}

function renderList(id, nodes) {
  el(id).replaceChildren(...nodes);
}

async function refresh() {
  if (state.loading) return;
  state.loading = true;
  try {
    const {repo, workflows, runs, prs} = await api("/api/estado");
    el("repo").replaceChildren(link(repo.full_name, repo.html_url),
      " · Rama principal " + repo.default_branch + " · IA en " + state.session.ref);
    renderList("workflows", workflows.map(workflow => {
      const row = text("li", "");
      const run = runs.find(item => item.workflow_id === workflow.id);
      row.append(link(workflow.name, workflow.html_url),
        statusBadge(run ? run.conclusion || run.status : workflow.state));
      return row;
    }));
    renderList("runs", runs.map(run => {
      const row = text("li", "");
      const details = text("div", "");
      details.append(link(run.display_title + " #" + run.run_number, run.html_url),
        text("small", run.head_branch + " · " + new Date(run.created_at).toLocaleString()));
      row.append(details, statusBadge(run.conclusion || run.status));
      addButton(row, "Ver pasos", () => showRun(run.id));
      return row;
    }));
    renderList("prs", prs.map(pr => {
      const row = text("li", "");
      row.append(link("#" + pr.number + " " + pr.title, pr.html_url),
        statusBadge(pr.merged_at ? "integrado" : pr.state));
      if (pr.state === "open" && pr.head.repo?.full_name === repo.full_name &&
          /^gemini\/correccion-\d+(?:-\d+)?$/.test(pr.head.ref) && pr.base.ref === repo.default_branch) {
        row.append(text("small", "Espera de decisión · " + pr.head.sha.slice(0, 8)));
        for (const [decision, title] of [["merge", "Aprobar merge"], ["rechazar", "Rechazar PR"]]) {
          addButton(row, title, async () => {
            if (!window.confirm(title + " #" + pr.number + " (" + pr.head.sha.slice(0, 8) + ")")) return;
            const result = await api("/api/prs/" + pr.number + "/" + decision, {sha: pr.head.sha});
            report(decision === "merge" ? "PR integrado. Los despliegues se inician por el cambio en main."
              : "PR cerrado.", result.url);
            await refresh();
          });
        }
      }
      return row;
    }));
  } finally {
    state.loading = false;
  }
}

async function showRun(id, scroll = true) {
  const version = ++state.version;
  const {run, jobs, artifacts} = await api("/api/runs/" + id);
  if (version !== state.version) return;
  if (state.selected !== id) {
    el("proposal").hidden = true;
    el("issue").hidden = true;
    el("approve").hidden = true;
    el("discard").hidden = true;
  }
  state.selected = id;
  el("details").hidden = false;
  el("run").replaceChildren(link(run.display_title, run.html_url), " · " + label(run.conclusion || run.status));
  renderList("steps", jobs.flatMap(job => [
    text("li", job.name + " · " + label(job.conclusion || job.status)),
    ...(job.steps || []).map(step => text("li", "↳ " + step.name + " · " + label(step.conclusion || step.status)))
  ]));
  renderList("artifacts", artifacts.map(artifact => {
    const row = text("li", "");
    row.append(link(artifact.name, artifact.url));
    if (artifact.preview) addButton(row, "Ver resultado", async () => {
      const files = await api("/api/runs/" + id + "/artifacts/" + artifact.id);
      if (state.selected !== id) return;
      const diagnosis = files["diagnostico.txt"] || files["revision.md"] || "";
      el("diagnosis").textContent = diagnosis;
      el("diff").textContent = files["cambio.diff"] || "";
      el("proposal").hidden = false;
      el("issue").hidden = !diagnosis;
      el("issue-title").value = "Hallazgo de Gemini en ejecución " + id;
      el("issue-body").value = diagnosis.slice(0, 6800) + "\n\nEjecución: " + run.html_url;
      const validated = jobs.some(job => job.name === "validar" && job.conclusion === "success");
      el("approve").hidden = !(validated && run.conclusion === "success" &&
        run.head_branch === "main" && files["cambio.diff"] && !jobs.some(job =>
          job.name.includes("publicar") && job.conclusion === "success"));
      el("discard").hidden = !files["cambio.diff"];
    });
    return row;
  }));
  if (scroll) el("details").scrollIntoView({behavior: "smooth"});
}

async function dispatch(workflow, values) {
  const result = await api("/api/ejecutar", {workflow, ...values});
  report("Ejecución solicitada. Aparecerá en el historial cuando GitHub la registre.", result.url);
  await refresh();
}

document.querySelectorAll("[data-workflow]").forEach(button => {
  button.addEventListener("click", () => action(button, () => dispatch(button.dataset.workflow, {
    archivo: el("archivo").value,
    solicitud: el("solicitud").value,
    simulacion: button.hasAttribute("data-test") || el("simulacion").checked
  })));
});
el("approve").addEventListener("click", () => action(el("approve"), async () => {
  if (window.confirm("¿Abrir un PR para esta propuesta validada?")) {
    await dispatch("publicar-propuesta.yml", {origen: state.selected});
    el("approve").hidden = true;
  }
}));
el("discard").addEventListener("click", () => {
  el("proposal").hidden = true;
  el("issue").hidden = true;
  el("approve").hidden = true;
  el("discard").hidden = true;
  report("Propuesta descartada de la vista. El artifact sigue disponible en el historial.");
});
el("issue").addEventListener("submit", event => {
  event.preventDefault();
  action(event.submitter, async () => {
    const result = await api("/api/issues", {title: el("issue-title").value, body: el("issue-body").value});
    report("Issue creado.", result.url);
  });
});
el("refresh").addEventListener("click", () => action(el("refresh"), refresh));

async function start() {
  state.session = await api("/api/sesion");
  el("key-label").hidden = el("panel-key").hidden = !state.session.key_required;
  if (state.session.ref !== "main") {
    el("simulacion").checked = true;
    el("simulacion").disabled = true;
  }
  await refresh();
}
start().catch(error => report(error.message));
setInterval(() => {
  if (!state.session || document.hidden) return;
  refresh().catch(error => report(error.message));
  if (state.selected && !el("proposal").hidden) return;
  if (state.selected) showRun(state.selected, false).catch(error => report(error.message));
}, 20000);
