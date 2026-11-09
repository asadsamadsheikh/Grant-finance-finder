/**
 * GrantAI Frontend Application
 * IBM Granite powered Grant & Funding Finder for Startups
 * Communicates with FastAPI backend at /api/*
 */

// ─── State ───────────────────────────────────────────────────────────────────
const state = {
  currentProfile: null,
  searchResults: [],
  selectedGrant: null,
  proposalData: null,
  allGrants: [],
};

const API_BASE = window.location.origin;

// ─── Initialization ───────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  checkHealth();
  loadBrowseGrants();
  showSection("finder");
});

// ─── Section Navigation ───────────────────────────────────────────────────────
function showSection(name) {
  const sections = ["finder", "proposals", "browse"];
  sections.forEach((s) => {
    const el = document.getElementById(s);
    if (el) el.style.display = s === name ? "block" : "none";
  });
  document.getElementById("home") && name !== "home"
    ? null
    : null;
  // Always show hero
  document.querySelector(".hero").style.display = "";
  if (name !== "home") {
    const target = document.getElementById(name);
    if (target) setTimeout(() => target.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  }
}

// ─── Health Check ─────────────────────────────────────────────────────────────
async function checkHealth() {
  const badge = document.getElementById("healthBadge");
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    const data = await res.json();
    const allOk = data.ibm_granite.includes("✓") || data.status === "operational";
    badge.innerHTML = `
      <span class="status-dot ${allOk ? "status-ok" : "status-warn"}"></span>
      <span>${allOk ? "All Services Active" : "Limited Mode"}</span>
    `;
  } catch {
    badge.innerHTML = `<span class="status-dot status-error"></span><span>Backend Offline</span>`;
  }
}

// ─── Grant Search ─────────────────────────────────────────────────────────────
async function searchGrants(event) {
  event.preventDefault();

  const profile = collectProfile();
  if (!profile) return;
  state.currentProfile = profile;

  // UI: show loading
  document.getElementById("resultsEmpty").style.display = "none";
  document.getElementById("resultsContent").style.display = "none";
  document.getElementById("loadingState").style.display = "flex";
  document.getElementById("searchBtn").disabled = true;

  // Animate loading steps
  animateLoadingSteps(["ls1", "ls2", "ls3", "ls4"], 3000);

  const useGranite = document.getElementById("useGranite").checked;

  try {
    const res = await fetch(`${API_BASE}/api/grants/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        startup_profile: profile,
        max_results: 8,
        use_granite_analysis: useGranite,
      }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    const data = await res.json();
    state.searchResults = data.grants || [];
    renderSearchResults(data);
    updateProposalSection();
  } catch (err) {
    console.error("Search error:", err);
    showError(`Search failed: ${err.message}`);
  } finally {
    document.getElementById("loadingState").style.display = "none";
    document.getElementById("searchBtn").disabled = false;
  }
}

function collectProfile() {
  const name = document.getElementById("startupName").value.trim();
  const industry = document.getElementById("industry").value.trim();
  const description = document.getElementById("description").value.trim();
  const stage = document.getElementById("stage").value;
  const location = document.getElementById("location").value.trim();

  if (!name || !industry || !description || !stage || !location) {
    alert("Please fill in all required fields (marked with *)");
    return null;
  }

  return {
    name,
    industry,
    description,
    stage,
    location,
    team_size: document.getElementById("teamSize").value,
    revenue: document.getElementById("revenue").value,
    problem: document.getElementById("problem").value.trim() || description,
    keywords: document.getElementById("keywords").value.split(",").map((k) => k.trim()).filter(Boolean),
    target_market: "",
    founded_year: "2023",
  };
}

function renderSearchResults(data) {
  const list = document.getElementById("grantsList");
  const header = document.getElementById("resultsHeader");
  list.innerHTML = "";

  const grants = data.grants || [];

  header.innerHTML = `
    <h3>🎯 ${grants.length} Matching Grants Found</h3>
    <p>Ranked by IBM Granite AI eligibility score for <strong>${data.startup_name}</strong></p>
  `;

  if (grants.length === 0) {
    list.innerHTML = '<div style="padding:32px;text-align:center;color:#525252;">No grants matched your profile. Try broadening your industry or location.</div>';
  } else {
    grants.forEach((grant, idx) => {
      list.appendChild(createGrantCard(grant, idx, true));
    });
  }

  document.getElementById("resultsContent").style.display = "flex";
}

function createGrantCard(grant, idx, showProposalBtn) {
  const template = document.getElementById("grantCardTemplate");
  const clone = template.content.cloneNode(true);
  const card = clone.querySelector(".grant-card");
  card.style.animationDelay = `${idx * 0.06}s`;
  card.dataset.id = grant.id;

  // Title & funder
  card.querySelector("h4").textContent = grant.title;
  card.querySelector(".grant-funder").textContent = `by ${grant.funder} · ${(grant.eligible_locations || []).join(", ")}`;

  // Score badge
  const score = grant.match_score || grant._score || 0;
  const badge = card.querySelector(".grant-score-badge");
  badge.innerHTML = `<span>${score}</span><small>match</small>`;
  badge.className = `grant-score-badge ${score >= 75 ? "score-high" : score >= 50 ? "score-med" : "score-low"}`;

  // Meta tags
  const amt = formatAmount(grant.amount_min, grant.amount_max);
  card.querySelector(".meta-tag.amount").textContent = amt;
  card.querySelector(".meta-tag.deadline").textContent = `📅 ${grant.deadline || "Rolling"}`;
  card.querySelector(".meta-tag.type").textContent = capitalizeFirst(grant.grant_type || "grant");

  // Description
  card.querySelector(".grant-description").textContent = grant.description || "";

  // Tags
  const tagContainer = card.querySelector(".grant-tags");
  [...(grant.focus_areas || []).slice(0, 3), ...(grant.eligible_stages || []).slice(0, 2)].forEach((tag) => {
    const t = document.createElement("span");
    t.className = "grant-tag";
    t.textContent = tag;
    tagContainer.appendChild(t);
  });

  // IBM Granite analysis block
  const granitAnalysis = grant.granite_analysis || {};
  if (granitAnalysis.recommendation) {
    const analysisBlock = card.querySelector(".granite-analysis");
    analysisBlock.style.display = "block";
    const body = card.querySelector(".analysis-body");
    body.innerHTML = `
      <p>${granitAnalysis.recommendation}</p>
      <div class="analysis-criteria">
        ${(granitAnalysis.matched_criteria || []).map((c) => `<span class="crit-ok">✓ ${c}</span>`).join("")}
        ${(granitAnalysis.missing_criteria || []).slice(0, 2).map((c) => `<span class="crit-no">✗ ${c}</span>`).join("")}
      </div>
    `;
  }

  // Actions
  const applyLink = card.querySelector(".apply-link");
  applyLink.href = grant.application_url || "#";

  const propBtn = card.querySelector(".gen-proposal-btn");
  if (showProposalBtn) {
    propBtn.addEventListener("click", () => selectGrantForProposal(grant));
  } else {
    propBtn.style.display = "none";
  }

  return clone;
}

function formatAmount(min, max) {
  if (!min && !max) return "💰 Amount TBD";
  const fmt = (n) => n >= 1000000 ? `$${(n / 1000000).toFixed(1)}M` : n >= 1000 ? `$${(n / 1000).toFixed(0)}K` : `$${n}`;
  if (min && max && min !== max) return `💰 ${fmt(min)}–${fmt(max)}`;
  return `💰 Up to ${fmt(max || min)}`;
}

function capitalizeFirst(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }

// ─── Browse All Grants ────────────────────────────────────────────────────────
async function loadBrowseGrants() {
  try {
    const res = await fetch(`${API_BASE}/api/grants/all`);
    const data = await res.json();
    state.allGrants = data.grants || [];
    renderBrowseGrid(state.allGrants);
  } catch (err) {
    console.warn("Could not load browse grants:", err.message);
  }
}

function renderBrowseGrid(grants) {
  const grid = document.getElementById("browseGrid");
  if (!grid) return;
  grid.innerHTML = "";
  grants.forEach((g, i) => grid.appendChild(createGrantCard({ ...g, match_score: null }, i, false)));
}

function filterBrowse() {
  const q = document.getElementById("browseSearch").value.toLowerCase();
  const stage = document.getElementById("browseStage").value.toLowerCase();
  const type = document.getElementById("browseType").value.toLowerCase();

  const filtered = state.allGrants.filter((g) => {
    const text = `${g.title} ${g.funder} ${g.description} ${(g.eligible_locations || []).join(" ")}`.toLowerCase();
    const matchQ = !q || text.includes(q);
    const matchStage = !stage || (g.eligible_stages || []).some((s) => s.toLowerCase().includes(stage));
    const matchType = !type || (g.grant_type || "").toLowerCase() === type;
    return matchQ && matchStage && matchType;
  });
  renderBrowseGrid(filtered);
}

// ─── Proposal Generation ──────────────────────────────────────────────────────
function selectGrantForProposal(grant) {
  state.selectedGrant = grant;
  showSection("proposals");

  // Update proposal form display
  document.getElementById("proposalGrantDisplay").innerHTML = `
    <div class="grant-selector-active">
      <h5>${grant.title}</h5>
      <p>${grant.funder} · ${formatAmount(grant.amount_min, grant.amount_max)}</p>
    </div>
  `;

  if (state.currentProfile) {
    document.getElementById("proposalProfileSummary").textContent =
      `${state.currentProfile.name} · ${state.currentProfile.stage} · ${state.currentProfile.industry}`;
  }

  document.getElementById("generateBtn").disabled = !state.currentProfile;
  document.getElementById("proposalOutput").style.display = "none";
}

function updateProposalSection() {
  if (state.currentProfile) {
    document.getElementById("proposalProfileSummary").textContent =
      `${state.currentProfile.name} · ${state.currentProfile.stage} · ${state.currentProfile.industry}`;
  }
}

async function generateProposal() {
  if (!state.selectedGrant || !state.currentProfile) {
    alert("Please run a grant search first and select a grant.");
    return;
  }

  document.getElementById("proposalOutput").style.display = "none";
  document.getElementById("proposalLoading").style.display = "flex";
  document.getElementById("generateBtn").disabled = true;

  animateLoadingSteps(["pl1", "pl2", "pl3", "pl4"], 5000);

  try {
    const res = await fetch(`${API_BASE}/api/proposals/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        startup_profile: state.currentProfile,
        grant_id: state.selectedGrant.id,
        grant_data: state.selectedGrant,
        include_cover_letter: document.getElementById("includeCoverLetter").checked,
      }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    const data = await res.json();
    state.proposalData = data.proposal;
    renderProposal(data.proposal);
  } catch (err) {
    console.error("Proposal error:", err);
    alert(`Proposal generation failed: ${err.message}\n\nMake sure IBM_WATSONX_API_KEY and IBM_WATSONX_PROJECT_ID are set in your .env file.`);
  } finally {
    document.getElementById("proposalLoading").style.display = "none";
    document.getElementById("generateBtn").disabled = false;
  }
}

function renderProposal(proposal) {
  const doc = document.getElementById("proposalDoc");
  const sectionLabels = {
    executive_summary:    "Executive Summary",
    problem_statement:    "Problem Statement",
    proposed_solution:    "Proposed Solution",
    innovation_uniqueness:"Innovation & Uniqueness",
    team_qualifications:  "Team Qualifications",
    implementation_plan:  "Implementation Plan",
    expected_outcomes:    "Expected Outcomes & Impact",
    budget_outline:       "Budget Outline",
  };

  doc.innerHTML = `
    <div class="proposal-disclaimer">
      ${proposal.disclaimer}
    </div>
    <div style="margin-bottom:20px;">
      <h3 style="font-size:20px;font-weight:700;">${proposal.startup_name} — Grant Application</h3>
      <p style="color:#525252;font-size:13px;margin-top:4px;">
        For: ${proposal.grant_title} | ${proposal.grant_funder}
        ${proposal.grant_amount_max ? ` | Up to $${Number(proposal.grant_amount_max).toLocaleString()}` : ""}
        | ~${proposal.word_count} words | Generated ${new Date(proposal.generated_at).toLocaleDateString()}
      </p>
    </div>
    ${Object.entries(proposal.sections)
      .filter(([key]) => sectionLabels[key])
      .map(([key, content]) => `
        <div class="proposal-section">
          <h4>${sectionLabels[key] || key}</h4>
          <p>${content}</p>
        </div>
      `).join("")}
    ${proposal.cover_letter ? `
      <div class="proposal-section">
        <h4>Cover Letter</h4>
        <p>${proposal.cover_letter}</p>
      </div>
    ` : ""}
    <p style="font-size:11px;color:#8d8d8d;margin-top:24px;">
      Proposal ID: ${proposal.proposal_id} · Stored in IBM Cloud Object Storage
    </p>
  `;

  document.getElementById("proposalOutput").style.display = "block";
  document.getElementById("proposalOutput").scrollIntoView({ behavior: "smooth" });
}

function downloadProposal() {
  if (!state.proposalData) return;
  const p = state.proposalData;
  let text = `GRANT APPLICATION PROPOSAL\n${"=".repeat(60)}\n`;
  text += `Startup: ${p.startup_name}\nGrant: ${p.grant_title}\nFunder: ${p.grant_funder}\nGenerated: ${p.generated_at}\n\n`;
  text += `⚠️ DISCLAIMER: ${p.disclaimer}\n\n${"=".repeat(60)}\n\n`;
  Object.entries(p.sections).forEach(([key, val]) => {
    text += `${key.replace(/_/g, " ").toUpperCase()}\n${"-".repeat(40)}\n${val}\n\n`;
  });
  if (p.cover_letter) text += `COVER LETTER\n${"-".repeat(40)}\n${p.cover_letter}\n`;
  const blob = new Blob([text], { type: "text/plain" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
  a.download = `${p.startup_name.replace(/\s+/g, "_")}_${p.proposal_id}_proposal.txt`;
  a.click();
}

function copyProposal() {
  if (!state.proposalData) return;
  const doc = document.getElementById("proposalDoc");
  navigator.clipboard.writeText(doc.innerText).then(() => alert("Proposal copied to clipboard!"));
}

// ─── Utility ──────────────────────────────────────────────────────────────────
function animateLoadingSteps(stepIds, totalMs) {
  const delay = totalMs / stepIds.length;
  stepIds.forEach((id, i) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.className = "lstep";
    setTimeout(() => {
      if (el) el.className = "lstep done";
    }, delay * (i + 1));
  });
}

function showError(msg) {
  document.getElementById("resultsEmpty").style.display = "flex";
  document.getElementById("resultsEmpty").querySelector("h4").textContent = "Search Error";
  document.getElementById("resultsEmpty").querySelector("p").textContent = msg;
  document.getElementById("resultsContent").style.display = "none";
  document.getElementById("loadingState").style.display = "none";
}
