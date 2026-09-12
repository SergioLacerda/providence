// Prevent flash of unstyled content before boot() runs
(function () {
  const saved = localStorage.getItem("sdd-theme");
  const dark = saved ? saved === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.theme = dark ? "dark" : "light";
})();

const STRINGS = {
  en: {
    title:          "SDD Selector",
    subtitle:       "Select governed items and export a JSON artifact.",
    searchPlaceholder: "Search items",
    export:         "Export JSON",
    import:         "Import JSON",
    clear:          "Clear",
    selected:       (n) => `${n} selected`,
    depends:        (ids) => `Depends: ${ids}`,
    mandatory:      "mandatory",
    optional:       "optional",
    imported:       (n) => `Imported ${n} selected item(s).`,
    cleared:        "Selection cleared.",
    errReadFile:    "Failed to read selection file.",
    errImportJson:  "Failed to import selection JSON.",
    errImportFormat: "Invalid file: import a selection file exported via 'Export JSON', not data.json.",
    errUnknownId:   (id) => `Unknown selector ID: ${id}`,
    warnUnknown:    (id) => `Unknown selected item: ${id}`,
    warnMissingDep: (a, b) => `${a} references missing dependency ${b}`,
    warnRequires:   (a, b) => `${a} requires ${b}`,
  },
  pt: {
    title:          "SDD Selector",
    subtitle:       "Selecione itens governados e exporte um artefato JSON.",
    searchPlaceholder: "Buscar itens",
    export:         "Exportar JSON",
    import:         "Importar JSON",
    clear:          "Limpar",
    selected:       (n) => `${n} selecionado(s)`,
    depends:        (ids) => `Depende de: ${ids}`,
    mandatory:      "obrigatório",
    optional:       "opcional",
    imported:       (n) => `${n} item(s) importado(s).`,
    cleared:        "Seleção limpa.",
    errReadFile:    "Falha ao ler o arquivo.",
    errImportJson:  "Falha ao importar JSON de seleção.",
    errImportFormat: "Arquivo inválido: importe um arquivo de seleção exportado pelo botão 'Exportar JSON', não o data.json.",
    errUnknownId:   (id) => `ID desconhecido: ${id}`,
    warnUnknown:    (id) => `Item selecionado desconhecido: ${id}`,
    warnMissingDep: (a, b) => `${a} referencia dependência ausente ${b}`,
    warnRequires:   (a, b) => `${a} requer ${b}`,
  },
};

function getLang() {
  const p = new URLSearchParams(location.search).get("lang");
  return p === "pt" ? "pt" : "en";
}

const T = STRINGS[getLang()];

const state = {
  items: [],
  selected: new Set(),
  categories: new Set(),
  docs: [],       // loaded from docs.index.json if available
  docsLoaded: false,
};

function itemMap() {
  return new Map(state.items.map((item) => [item.id, item]));
}

function getSelectedCategories() {
  return [...document.querySelectorAll("[data-filter].active")].map((node) => node.dataset.filter);
}

function filterItems() {
  const term = document.getElementById("search").value.toLowerCase();
  const categories = getSelectedCategories();
  return state.items.filter((item) => {
    const text = `${item.id} ${item.title} ${item.description}`.toLowerCase();
    const matchesText = term === "" || text.includes(term);
    const matchesCategory = categories.length === 0 || categories.includes(item.category);
    return matchesText && matchesCategory;
  });
}

function resolveSelection() {
  const warnings = [];
  const resolved = new Set(state.selected);
  const byId = itemMap();
  const queue = [...state.selected];
  const visiting = new Set();
  while (queue.length > 0) {
    const itemId = queue.shift();
    if (itemId === undefined || visiting.has(itemId)) continue;
    visiting.add(itemId);
    const item = byId.get(itemId);
    if (!item) {
      warnings.push(T.warnUnknown(itemId));
      continue;
    }
    for (const dep of item.depends_on || []) {
      if (!byId.has(dep)) {
        warnings.push(T.warnMissingDep(item.id, dep));
        continue;
      }
      if (!resolved.has(dep)) {
        warnings.push(T.warnRequires(item.id, dep));
        resolved.add(dep);
        queue.push(dep);
      }
    }
  }
  return { warnings, resolved: [...resolved].sort() };
}

function updateWarnings() {
  const node = document.getElementById("warnings");
  const { warnings } = resolveSelection();
  if (warnings.length === 0) {
    node.classList.add("hidden");
    node.textContent = "";
    return;
  }
  node.classList.remove("hidden");
  node.replaceChildren(
    ...warnings.map((warning) => {
      const div = document.createElement("div");
      div.textContent = warning;
      return div;
    })
  );
}

function updateSummary() {
  const { resolved } = resolveSelection();
  document.getElementById("summary").textContent = T.selected(resolved.length);
}

function showStatus(message, type = "info") {
  const node = document.getElementById("status");
  if (message === "") {
    node.classList.add("hidden");
    node.textContent = "";
    node.dataset.kind = "";
    return;
  }
  node.classList.remove("hidden");
  node.dataset.kind = type;
  node.textContent = message;
}

function persistSelection() {
  localStorage.setItem("sdd-selector", JSON.stringify([...state.selected]));
}

function toggleSelection(itemId, checked) {
  if (checked) {
    state.selected.add(itemId);
  } else {
    state.selected.delete(itemId);
  }
  persistSelection();
  updateWarnings();
  updateSummary();
}

function renderFilters() {
  const node = document.getElementById("filters");
  const names = [...state.categories].sort();
  node.replaceChildren(
    ...names.map((name) => {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.filter = name;
      button.textContent = name;
      button.addEventListener("click", () => {
        button.classList.toggle("active");
        renderItems();
      });
      return button;
    })
  );
}

function buildItemCard(item) {
  const itemType = item.item_type || "mandate";

  const article = document.createElement("article");
  article.className = "card";
  article.dataset.itemType = itemType;

  const label = document.createElement("label");
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.dataset.item = item.id;
  checkbox.checked = state.selected.has(item.id);
  checkbox.addEventListener("change", (event) => {
    toggleSelection(event.target.dataset.item, event.target.checked);
  });
  label.append(checkbox, ` ${item.id}`);

  const title = document.createElement("h2");
  title.textContent = item.title;

  const description = document.createElement("p");
  description.textContent = item.description;

  const meta = document.createElement("div");
  meta.className = "meta";

  const typePill = document.createElement("span");
  typePill.className = `pill pill--type pill--${itemType}`;
  typePill.textContent = itemType;

  const categoryPill = document.createElement("span");
  categoryPill.className = "pill";
  categoryPill.textContent = item.category;

  const mandatoryPill = document.createElement("span");
  mandatoryPill.className = "pill";
  mandatoryPill.textContent = item.mandatory ? T.mandatory : T.optional;

  meta.append(typePill, categoryPill, mandatoryPill);

  if (item.depends_on.length > 0) {
    const dependsPill = document.createElement("span");
    dependsPill.className = "pill";
    dependsPill.textContent = T.depends(item.depends_on.join(", "));
    meta.append(dependsPill);
  }

  article.append(label, title, description, meta);
  return article;
}

function renderItems() {
  const node = document.getElementById("items");
  const items = filterItems();
  node.replaceChildren(...items.map(buildItemCard));
}

function downloadSelection() {
  const { resolved } = resolveSelection();
  const payload = {
    version: "1.0",
    selected_ids: [...state.selected].sort(),
    resolved_ids: resolved,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "selector-selection.json";
  link.click();
  URL.revokeObjectURL(url);
}

function restoreSelection() {
  const stored = localStorage.getItem("sdd-selector");
  if (stored === null) return;
  try {
    for (const itemId of JSON.parse(stored)) {
      if (typeof itemId === "string") {
        state.selected.add(itemId);
      }
    }
  } catch {
    localStorage.removeItem("sdd-selector");
  }
}

function loadSelectionPayload(payload) {
  if (!payload || typeof payload !== "object") {
    throw new Error("Selection payload must be an object.");
  }
  if (typeof payload.version !== "string") {
    throw new Error("Selection payload version must be a string.");
  }
  const selectedIds = Array.isArray(payload.selected_ids)
    ? payload.selected_ids
    : payload.resolved_ids;
  if (!Array.isArray(selectedIds)) {
    throw new Error(T.errImportFormat);
  }
  const byId = itemMap();
  state.selected.clear();
  for (const itemId of selectedIds) {
    if (typeof itemId !== "string") {
      throw new Error("Selection ids must be strings.");
    }
    if (!byId.has(itemId)) {
      throw new Error(T.errUnknownId(itemId));
    }
    state.selected.add(itemId);
  }
  persistSelection();
  renderItems();
  updateWarnings();
  updateSummary();
}

function importSelectionFile(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const payload = JSON.parse(String(reader.result));
      loadSelectionPayload(payload);
      showStatus(T.imported(state.selected.size), "success");
    } catch (error) {
      showStatus(error.message || T.errImportJson, "error");
    }
  };
  reader.onerror = () => {
    showStatus(T.errReadFile, "error");
  };
  reader.readAsText(file);
}

function clearSelection() {
  state.selected.clear();
  persistSelection();
  renderItems();
  updateWarnings();
  updateSummary();
  showStatus(T.cleared, "info");
}

async function loadDocsIndex() {
  try {
    const response = await fetch("docs.index.json");
    if (!response.ok) return;          // not available — silent fallback
    const index = await response.json();
    state.docs = (index && Array.isArray(index.documents)) ? index.documents : [];
    state.docsLoaded = true;
  } catch {
    // docs.index.json is optional — fetch failure is non-fatal
  }
}

async function boot() {
  document.title = T.title;
  document.querySelector(".hero h1").textContent = T.title;
  document.querySelector(".hero p").textContent  = T.subtitle;
  document.getElementById("search").placeholder  = T.searchPlaceholder;
  document.getElementById("export").textContent  = T.export;
  document.getElementById("import").textContent  = T.import;
  document.getElementById("clear").textContent   = T.clear;

  let payload;
  try {
    const response = await fetch("data.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    payload = await response.json();
  } catch (err) {
    showStatus(
      `Failed to load data.json: ${err.message}. ` +
        "Serve the selector over HTTP (e.g. python -m http.server) instead of opening it as a file://.",
      "error"
    );
    return;
  }
  state.items = payload.items || [];
  for (const item of state.items) {
    state.categories.add(item.category);
  }

  // Load docs.index.json in parallel — optional, non-blocking
  await loadDocsIndex();

  restoreSelection();
  renderFilters();
  renderItems();
  updateWarnings();
  updateSummary();
  document.getElementById("search").addEventListener("input", renderItems);
  document.getElementById("export").addEventListener("click", downloadSelection);
  document.getElementById("import").addEventListener("click", () => {
    document.getElementById("import-file").click();
  });
  document.getElementById("import-file").addEventListener("change", (event) => {
    const [file] = event.target.files || [];
    if (!file) return;
    importSelectionFile(file);
    event.target.value = "";
  });
  document.getElementById("clear").addEventListener("click", clearSelection);
}

boot();
