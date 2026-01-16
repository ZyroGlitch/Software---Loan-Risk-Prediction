const form = document.getElementById("form");

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const payload = {
    age: Number(document.getElementById("age").value),
    job: Number(document.getElementById("job").value),
    marital: Number(document.getElementById("marital").value),
    education: Number(document.getElementById("education").value),
    default: Number(document.getElementById("default").value),
    balance: Number(document.getElementById("balance").value),
    housing: Number(document.getElementById("housing").value),
    loan: Number(document.getElementById("loan").value),
    contact: Number(document.getElementById("phone").value),
    day: Number(document.getElementById("day").value),
    month: Number(document.getElementById("month").value),
    duration: Number(document.getElementById("duration").value),
    campaign: Number(document.getElementById("campaign").value),
    pdays: Number(document.getElementById("pdays").value),
    previous: Number(document.getElementById("previous").value),
    poutcome: Number(document.getElementById("previous-outcome").value),
  };

  let data;
  try {
    const res = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const t = await res.text();
      throw new Error(t || "Predict failed");
    }

    data = await res.json();
  } catch (err) {
    console.error(err);
    return;
  }

  if (data.baseline_model) {
    document.getElementById("baseline-status").textContent =
      data.baseline_model.loan_status;

    document.getElementById("baseline-risk").textContent =
      Number(data.baseline_model.risk_percentage).toFixed(2) + "%";

    document.getElementById("baseline-confidence").textContent =
      Number(data.baseline_model.confidence_score).toFixed(2) + "%";
  }

  if (data.enhanced_model) {
    document.getElementById("enhanced-status").textContent =
      data.enhanced_model.loan_status;

    document.getElementById("enhanced-risk").textContent =
      Number(data.enhanced_model.risk_percentage).toFixed(2) + "%";

    document.getElementById("enhanced-confidence").textContent =
      Number(data.enhanced_model.confidence_score).toFixed(2) + "%";
  }

  if (data.baseline_explainability?.items) {
    renderFeatureBars("baseline-features-container", data.baseline_explainability.items);
    renderTopBottomFromImpact(
      data.baseline_explainability.items,
      "baselineTopFeatureName",
      "baselineTopFeaturePercentage",
      "baselineLowestFeatureName",
      "baselineLowestFeaturePercentage"
    );
  }

  if (data.enhanced_explainability_16?.items) {
    renderFeatureBars("optimized-features-container", data.enhanced_explainability_16.items);
    renderTopBottomFromImpact(
      data.enhanced_explainability_16.items,
      "optimizedTopFeatureName",
      "optimizedTopFeaturePercentage",
      "optimizedLowestFeatureName",
      "optimizedLowestFeaturePercentage"
    );
  }
});

function renderFeatureBars(containerId, items) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const rows = (items || []).map((x) => ({
    feature: x.feature,
    impact: Number(x.impact_percent ?? 0),
    contribution: Number(x.contribution ?? 0),
  }));

  const maxAbs = rows.reduce((m, x) => Math.max(m, Math.abs(x.contribution)), 0) || 1;

  rows.forEach((x) => {
    x.contributionPercent = (Math.abs(x.contribution) / maxAbs) * 100; // 0..100
    x.sign = x.contribution >= 0 ? "+" : "−";
  });

  container.innerHTML = "";

  rows.forEach((x, idx) => {
    const impactPct = x.impact.toFixed(2);
    const contribPct = x.contributionPercent.toFixed(2);

    const row = document.createElement("div");
    row.className = "feature-row";

    row.innerHTML = `
      <div class="feature-row-title">
        <span class="feature-row-index">${idx + 1}</span>
        <span class="feature-row-name">${formatLabel(x.feature)}</span>
      </div>

      <div class="feature-bar-group">
        <div class="feature-bar-label">
          <span>Impact</span>
          <span>${impactPct}%</span>
        </div>
        <div class="feature-bar">
          <div class="feature-bar-fill" style="width:${impactPct}%;"></div>
        </div>
      </div>

      <div class="feature-bar-group">
        <div class="feature-bar-label">
          <span>Contribution</span>
          <span class="contrib ${x.sign === "−" ? "neg" : "pos"}">${x.sign}${contribPct}%</span>
        </div>
        <div class="feature-bar">
          <div class="feature-bar-fill" style="width:${contribPct}%;"></div>
        </div>
      </div>
    `;

    container.appendChild(row);
  });
}

function renderTopBottomFromImpact(items, topNameId, topPctId, lowNameId, lowPctId) {
  const arr = (items || [])
    .map((x) => ({ feature: x.feature, v: Number(x.impact_percent ?? 0) }))
    .sort((a, b) => b.v - a.v);

  if (!arr.length) return;

  const top = arr[0];
  const low = arr[arr.length - 1];

  const topName = document.getElementById(topNameId);
  const topPct = document.getElementById(topPctId);
  const lowName = document.getElementById(lowNameId);
  const lowPct = document.getElementById(lowPctId);

  if (topName) topName.textContent = formatLabel(top.feature);
  if (topPct) topPct.textContent = top.v.toFixed(2) + "%";
  if (lowName) lowName.textContent = formatLabel(low.feature);
  if (lowPct) lowPct.textContent = low.v.toFixed(2) + "%";
}

function formatLabel(feature) {
  const map = {
    age: "Age",
    marital: "Marital Status",
    education: "Highest Educational Attainment",
    job: "Job",
    contact: "Phone Type",
    balance: "Balance",
    housing: "Housing",
    default: "Default",
    loan: "Loan",
    day: "Day",
    duration: "Duration",
    month: "Month",
    campaign: "Campaign",
    pdays: "Days Since Contact",
    previous: "Previous Contacts",
    poutcome: "Previous Outcome",
  };

  return map[feature] || feature;
}
