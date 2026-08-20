const form = document.getElementById("analyze-form");
const submitBtn = document.getElementById("submit-btn");
const resultSection = document.getElementById("result");
const errorBox = document.getElementById("error-box");

const GAUGE_CIRCUMFERENCE = 326.7;

function verdictColor(verdict) {
  if (verdict === "likely_credible") return "#3fbf7f";
  if (verdict === "mixed_or_uncertain") return "#e0b83f";
  return "#e0563f";
}

function formatLabel(value) {
  return value
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function renderList(el, items, renderItem) {
  el.innerHTML = "";
  if (!items || items.length === 0) {
    const li = document.createElement("li");
    li.textContent = "None reported.";
    li.classList.add("empty-item");
    el.appendChild(li);
    return;
  }
  items.forEach((item) => el.appendChild(renderItem(item)));
}

function renderResult(data) {
  errorBox.classList.add("hidden");
  resultSection.classList.remove("hidden");

  const score = data.composite_score;
  document.getElementById("score-number").textContent = Math.round(score);

  const gauge = document.getElementById("gauge-circle");
  const offset = GAUGE_CIRCUMFERENCE * (1 - score / 100);
  gauge.style.stroke = verdictColor(data.verdict);
  gauge.style.strokeDashoffset = offset;

  const badge = document.getElementById("verdict-badge");
  badge.textContent = formatLabel(data.verdict);
  badge.className = "badge " + data.verdict;

  const bd = data.breakdown;

  document.getElementById("ai-summary").textContent =
    bd.ai_fact_check.error || bd.ai_fact_check.summary || "";

  document.getElementById("source-score").textContent =
    Math.round(bd.source_reputation.score) + " / 100";
  document.getElementById("source-domain").textContent = bd.source_reputation.domain
    ? `Domain: ${bd.source_reputation.domain} (${formatLabel(bd.source_reputation.category)})`
    : "No URL provided";
  document.getElementById("source-notes").textContent = bd.source_reputation.notes;

  document.getElementById("style-score").textContent =
    Math.round(bd.language_style.score) + " / 100";
  renderList(document.getElementById("style-flags"), bd.language_style.flags, (flag) => {
    const li = document.createElement("li");
    li.textContent = flag;
    return li;
  });

  const aiScore = bd.ai_fact_check.ai_score;
  document.getElementById("ai-score").textContent =
    aiScore === null || aiScore === undefined ? "N/A" : Math.round(aiScore) + " / 100";
  document.getElementById("ai-search-status").textContent = bd.ai_fact_check.used_web_search
    ? "Verified using live web search."
    : "Web search not used for this result.";

  renderList(document.getElementById("red-flags"), bd.ai_fact_check.red_flags, (flag) => {
    const li = document.createElement("li");
    li.textContent = flag;
    return li;
  });

  renderList(document.getElementById("claims-list"), bd.ai_fact_check.key_claims, (claim) => {
    const li = document.createElement("li");
    const span = document.createElement("span");
    span.className = "claim-assessment";
    span.textContent = formatLabel(claim.assessment);
    const text = document.createElement("span");
    text.textContent = claim.claim;
    const explanation = document.createElement("div");
    explanation.className = "claim-explanation";
    explanation.textContent = claim.explanation;
    li.appendChild(span);
    li.appendChild(text);
    li.appendChild(explanation);
    return li;
  });

  renderList(document.getElementById("sources-list"), bd.ai_fact_check.cited_sources, (source) => {
    const li = document.createElement("li");
    if (source.url) {
      const a = document.createElement("a");
      a.href = source.url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = source.name;
      li.appendChild(a);
    } else {
      const span = document.createElement("span");
      span.textContent = source.name;
      li.appendChild(span);
    }
    const stance = document.createElement("span");
    stance.className = "source-stance";
    stance.textContent = formatLabel(source.stance);
    li.appendChild(stance);
    return li;
  });
}

function renderError(message) {
  resultSection.classList.add("hidden");
  errorBox.classList.remove("hidden");
  errorBox.textContent = message;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitBtn.disabled = true;
  submitBtn.textContent = "Analyzing...";

  const payload = {
    text: document.getElementById("text").value,
    url: document.getElementById("url").value || null,
    source_name: document.getElementById("source_name").value || null,
  };

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Request failed (${response.status}): ${errText}`);
    }

    const data = await response.json();
    renderResult(data);
  } catch (err) {
    renderError(err.message || "Something went wrong while analyzing this text.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Analyze";
  }
});
