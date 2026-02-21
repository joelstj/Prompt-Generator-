/* global state */
let templates = [];
let activeTemplateId = null;
let activeCategory = "All";

/* ── DOM refs ─────────────────────────────────────────────────── */
const templateSelect    = document.getElementById("template-select");
const mainGoalEl        = document.getElementById("main-goal");
const outputFormatEl    = document.getElementById("output-format");
const rulesEl           = document.getElementById("rules");
const outputGoalEl      = document.getElementById("output-goal");
const correctnessEl     = document.getElementById("correctness");
const howToActEl        = document.getElementById("how-to-act");
const generateBtn       = document.getElementById("generate-btn");
const clearBtn          = document.getElementById("clear-btn");
const copyBtn           = document.getElementById("copy-btn");
const outputPre         = document.getElementById("output-pre");
const emptyState        = document.getElementById("empty-state");
const charCountEl       = document.getElementById("char-count");
const spinnerOverlay    = document.getElementById("spinner-overlay");
const templatesGrid     = document.getElementById("templates-grid");
const categoryFilters   = document.getElementById("category-filters");
const toastContainer    = document.getElementById("toast-container");

/* ── Bootstrap ────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  loadTemplates();
  generateBtn.addEventListener("click", handleGenerate);
  clearBtn.addEventListener("click", handleClear);
  copyBtn.addEventListener("click", handleCopy);
  templateSelect.addEventListener("change", handleTemplateSelectChange);
});

/* ── Template Loading ─────────────────────────────────────────── */
async function loadTemplates() {
  try {
    const res = await fetch("/api/templates");
    if (!res.ok) throw new Error("Failed to load templates");
    templates = await res.json();
    populateTemplateDropdown();
    renderCategoryFilters();
    renderTemplateCards(templates);
  } catch (err) {
    showToast("Could not load templates: " + err.message, "error");
  }
}

function populateTemplateDropdown() {
  templateSelect.innerHTML = '<option value="">— Select a template —</option>';
  templates.forEach(t => {
    const opt = document.createElement("option");
    opt.value = t.id;
    opt.textContent = `${t.name} (${t.category})`;
    templateSelect.appendChild(opt);
  });
}

function renderCategoryFilters() {
  const categories = ["All", ...new Set(templates.map(t => t.category))];
  categoryFilters.innerHTML = "";
  categories.forEach(cat => {
    const btn = document.createElement("button");
    btn.className = "filter-btn" + (cat === activeCategory ? " active" : "");
    btn.textContent = cat;
    btn.addEventListener("click", () => {
      activeCategory = cat;
      document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const filtered = cat === "All" ? templates : templates.filter(t => t.category === cat);
      renderTemplateCards(filtered);
    });
    categoryFilters.appendChild(btn);
  });
}

function renderTemplateCards(list) {
  templatesGrid.innerHTML = "";
  if (list.length === 0) {
    const empty = document.createElement("div");
    empty.style.cssText = "padding:2rem;color:var(--text-muted);font-size:.875rem;grid-column:1/-1;text-align:center;";
    empty.textContent = "No templates found for this category.";
    templatesGrid.appendChild(empty);
    return;
  }
  list.forEach(t => {
    const card = buildTemplateCard(t);
    templatesGrid.appendChild(card);
  });
}

function buildTemplateCard(t) {
  const card = document.createElement("div");
  card.className = "template-card" + (t.id === activeTemplateId ? " active" : "");
  card.dataset.id = t.id;
  card.setAttribute("role", "button");
  card.setAttribute("tabindex", "0");
  card.setAttribute("aria-label", `Use template: ${t.name}`);

  const catClass = categoryClass(t.category);

  card.innerHTML = `
    <div class="template-card-header">
      <div class="template-name">${escHtml(t.name)}</div>
      <span class="template-category-badge ${catClass}">${escHtml(t.category)}</span>
    </div>
    <div class="template-desc">${escHtml(t.description)}</div>
    <div class="template-use-btn">⚡ Use template →</div>
  `;

  const applyTemplate = () => {
    fillForm(t);
    activeTemplateId = t.id;
    templateSelect.value = t.id;
    document.querySelectorAll(".template-card").forEach(c => c.classList.remove("active"));
    card.classList.add("active");
    // Scroll to form on small screens
    if (window.innerWidth <= 900) {
      document.querySelector(".panels").scrollIntoView({ behavior: "smooth" });
    }
    showToast(`Template "${t.name}" applied`, "success");
  };

  card.addEventListener("click", applyTemplate);
  card.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); applyTemplate(); } });
  return card;
}

/* ── Form Helpers ─────────────────────────────────────────────── */
function fillForm(t) {
  mainGoalEl.value     = t.main_goal     || "";
  outputFormatEl.value = t.output_format || "";
  rulesEl.value        = t.rules         || "";
  outputGoalEl.value   = t.output_goal   || "";
  correctnessEl.value  = t.correctness   || "";
  howToActEl.value     = t.how_to_act    || "";
}

function handleTemplateSelectChange() {
  const id = templateSelect.value;
  if (!id) return;
  const t = templates.find(t => t.id === id);
  if (!t) return;
  fillForm(t);
  activeTemplateId = id;
  document.querySelectorAll(".template-card").forEach(c => {
    c.classList.toggle("active", c.dataset.id === id);
  });
  showToast(`Template "${t.name}" applied`, "success");
}

function handleClear() {
  mainGoalEl.value = outputFormatEl.value = rulesEl.value =
    outputGoalEl.value = correctnessEl.value = howToActEl.value = "";
  templateSelect.value = "";
  activeTemplateId = null;
  document.querySelectorAll(".template-card").forEach(c => c.classList.remove("active"));
  outputPre.textContent = "";
  outputPre.classList.add("empty");
  emptyState.classList.remove("hidden");
  outputPre.classList.add("hidden");
  copyBtn.disabled = true;
  charCountEl.innerHTML = "";
  showToast("All fields cleared", "info");
}

/* ── Generate ─────────────────────────────────────────────────── */
async function handleGenerate() {
  const body = {
    main_goal:     mainGoalEl.value.trim(),
    output_format: outputFormatEl.value.trim(),
    rules:         rulesEl.value.trim(),
    output_goal:   outputGoalEl.value.trim(),
    correctness:   correctnessEl.value.trim(),
    how_to_act:    howToActEl.value.trim(),
  };

  if (!Object.values(body).some(v => v)) {
    showToast("Please fill in at least one field", "error");
    return;
  }

  setLoading(true);
  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Generation failed", "error");
      return;
    }
    displayOutput(data.prompt, data.char_count);
    showToast("Prompt generated successfully!", "success");
  } catch (err) {
    showToast("Network error: " + err.message, "error");
  } finally {
    setLoading(false);
  }
}

function displayOutput(text, charCount) {
  emptyState.classList.add("hidden");
  outputPre.classList.remove("hidden", "empty");
  outputPre.textContent = text;
  copyBtn.disabled = false;
  charCountEl.innerHTML = `<span>${(charCount || text.length).toLocaleString()}</span> characters`;
}

function setLoading(on) {
  generateBtn.disabled = on;
  spinnerOverlay.classList.toggle("active", on);
}

/* ── Copy ─────────────────────────────────────────────────────── */
async function handleCopy() {
  const text = outputPre.textContent;
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    showToast("Copied to clipboard!", "success");
    copyBtn.textContent = "✓ Copied!";
    setTimeout(() => { copyBtn.innerHTML = "📋 Copy to Clipboard"; }, 2000);
  } catch {
    showToast("Copy failed — please select and copy the text manually.", "error");
  }
}

/* ── Toast ────────────────────────────────────────────────────── */
function showToast(message, type = "info") {
  const icons = { success: "✅", error: "❌", info: "ℹ️" };
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span class="toast-icon">${icons[type] || "ℹ️"}</span><span>${escHtml(message)}</span>`;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.classList.add("hide");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

/* ── Utilities ────────────────────────────────────────────────── */
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function categoryClass(cat) {
  const map = {
    "Smart Contract":          "cat-smart-contract",
    "DeFi Bot":                "cat-defi-bot",
    "Trading Bot":             "cat-trading-bot",
    "Blockchain Integration":  "cat-blockchain-integration",
    "Security Audit":          "cat-security-audit",
    "MEV Bot":                 "cat-mev-bot",
    "NFT":                     "cat-nft",
    "Cross-Chain":             "cat-cross-chain",
  };
  return map[cat] || "cat-default";
}
