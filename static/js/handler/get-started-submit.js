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
});
