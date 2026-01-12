document.getElementById("form").addEventListener("submit", async (e) => {
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

  const response = await fetch("/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const result = await response.json();

  // Feature Indicators Function Call
  runPrediction(payload);

  /* ================= BASELINE MODEL ================= */
  if (result.baseline_model) {
    document.getElementById("baseline-status").textContent =
      result.baseline_model.loan_status;

    document.getElementById("baseline-risk").textContent =
      result.baseline_model.risk_percentage + "%";

    document.getElementById("baseline-accuracy").textContent =
      result.baseline_model.rf_probability + "%";

    document.getElementById("baseline-confidence").textContent =
      result.baseline_model.confidence_score + "%";
  }

  /* ================= ENHANCED MODEL ================= */
  if (result.enhanced_model) {
    document.getElementById("enhanced-status").textContent =
      result.enhanced_model.loan_status;

    document.getElementById("enhanced-risk").textContent =
      result.enhanced_model.risk_percentage + "%";

    document.getElementById("enhanced-accuracy").textContent =
      result.enhanced_model.xgb_probability + "%";

    document.getElementById("enhanced-confidence").textContent =
      result.enhanced_model.confidence_score + "%";
  }

  /* ================= Feature Indicators (Helper functions) ================= */

  function renderIndicators(containerId, items) {
    const container = document.getElementById(containerId);
    container.innerHTML = "";

    items.forEach(item => {
      const pct = Number(item.impact_percent).toFixed(2);

      const indicator = document.createElement("div");
      indicator.className = "indicator";

      indicator.innerHTML = `
        <div class="indicator-chart"
            data-percentage="${pct}"
            style="--percentage: ${pct}">
          <span class="indicator-value">${pct}%</span>
        </div>
        <p class="indicator-label">${formatLabel(item.feature)}</p>
      `;

      container.appendChild(indicator);
    });
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
      poutcome: "Previous Outcome"
    };
    return map[feature] || feature;
  }


  /* ================= Feature Indicators (FETCH + INJECT) ================= */
  async function runPrediction(payload) {
  const res = await fetch("/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  const data = await res.json();

  // BASELINE SHAP (16 features)
  if (data.baseline_explainability) {
    renderIndicators(
      "baseline-indicators",
      data.baseline_explainability.items
    );
  }

  // OPTIMIZED SHAP (16 features, final blend)
  if (data.enhanced_explainability_16) {
    renderIndicators(
      "optimized-indicators",
      data.enhanced_explainability_16.items
    );
  }
}


  
});
