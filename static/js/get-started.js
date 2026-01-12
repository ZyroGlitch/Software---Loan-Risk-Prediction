// Populate select options in the Get Started form
// Import data for select options. If modules aren't supported in the
// current page, we will also try to read from a global fallback.
import {
  jobData,
  educationData,
  maritalStatusData,
  phoneData,
  loanData,
  housingData,
  defaultData,
  dayData,
  monthData,
  previousOutcomeData,
} from "../data/get-started-data.js";
import {
  renderFeatures,
  renderFeatureStats,
} from "./get-started-contribution.js";

function populateSelectOptions(
  selectId,
  data,
  placeholder = "Select an option"
) {
  const selectElement = document.getElementById(selectId);

  if (!selectElement) return;

  if (!Array.isArray(data) || data.length === 0) {
    // Ensure we at least show the placeholder if no data provided
    selectElement.innerHTML = "";
    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = placeholder;
    defaultOption.disabled = true;
    defaultOption.selected = true;
    selectElement.appendChild(defaultOption);
    return;
  }

  selectElement.innerHTML = "";

  const defaultOption = document.createElement("option");
  defaultOption.value = "";
  defaultOption.textContent = placeholder;
  defaultOption.disabled = true;
  defaultOption.selected = true;
  selectElement.appendChild(defaultOption);

  data.forEach((item) => {
    const option = document.createElement("option");
    const value = item && (item.value ?? item.val ?? item.id ?? "");
    const label = item && (item.label ?? item.text ?? String(value));
    option.value = String(value);
    option.textContent = label;
    selectElement.appendChild(option);
  });
}

function initGetStartedOptions() {
  // Prefer imported module values; fallback to globals if present
  const globals = window.getStartedData || {};

  populateSelectOptions("job", jobData ?? globals.jobData ?? []);
  populateSelectOptions(
    "education",
    educationData ?? globals.educationData ?? []
  );
  populateSelectOptions(
    "marital",
    maritalStatusData ?? globals.maritalStatusData ?? []
  );
  populateSelectOptions("phone", phoneData ?? globals.phoneData ?? []);
  populateSelectOptions("loan", loanData ?? globals.loanData ?? []);
  populateSelectOptions("housing", housingData ?? globals.housingData ?? []);
  populateSelectOptions("default", defaultData ?? globals.defaultData ?? []);
  populateSelectOptions("day", dayData ?? globals.dayData ?? []);
  populateSelectOptions("month", monthData ?? globals.monthData ?? []);
  populateSelectOptions(
    "previous-outcome",
    previousOutcomeData ?? globals.previousOutcomeData ?? []
  );

  // For feature contribution indicators
  renderFeatures("baseline-indicators", "baseline");
  renderFeatures("optimized-indicators", "optimized");
  renderFeatureStats("baseline");
  renderFeatureStats("optimized");
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initGetStartedOptions);
} else {
  initGetStartedOptions();
}

// Export initializer if this file is used as a module
export { initGetStartedOptions, populateSelectOptions };
