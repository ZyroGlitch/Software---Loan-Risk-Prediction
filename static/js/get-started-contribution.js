import {
  BaseLineFeatures,
  OptimizedFeatures,
} from "../data/get-started-contribution-data.js";

export function renderFeatures(containerId, type = "baseline") {
  const container = document.getElementById(containerId);

  if (!container) return;
  const features = type === "baseline" ? BaseLineFeatures : OptimizedFeatures;
  const html = features
    .map(
      (feature, index) => `
      <div class="feature-item">
        <div class="feature-header">
          <div class="feature-name-container">
            <span class="feature-number">${index + 1}</span>
            <h1 class="feature-name">${feature.name}</h1>
          </div>
          <span class="feature-importance">${feature.importance}%</span>
        </div>
        <div class="progress-bar-container">
          <div class="progress-bar" style="width: ${feature.importance}%"></div>
        </div>
      </div>
    `
    )
    .join("");

  container.innerHTML = html;
}

export function renderFeatureStats(type = "baseline") {
  const features = type === "baseline" ? BaseLineFeatures : OptimizedFeatures;
  const prefix = type === "baseline" ? "baseline" : "optimized";

  if (!features || features.length === 0) return;

  // Sort features by importance to find top and lowest
  const sortedFeatures = [...features].sort(
    (a, b) => b.importance - a.importance
  );

  const topFeature = sortedFeatures[0];
  const lowestFeature = sortedFeatures[sortedFeatures.length - 1];

  // Update DOM elements with prefixed IDs
  const topFeatureName = document.getElementById(`${prefix}TopFeatureName`);
  const topFeaturePercentage = document.getElementById(
    `${prefix}TopFeaturePercentage`
  );
  const lowestFeatureName = document.getElementById(
    `${prefix}LowestFeatureName`
  );
  const lowestFeaturePercentage = document.getElementById(
    `${prefix}LowestFeaturePercentage`
  );

  if (topFeatureName) topFeatureName.textContent = topFeature.name;
  if (topFeaturePercentage)
    topFeaturePercentage.textContent = `${topFeature.importance}%`;
  if (lowestFeatureName) lowestFeatureName.textContent = lowestFeature.name;
  if (lowestFeaturePercentage)
    lowestFeaturePercentage.textContent = `${lowestFeature.importance}%`;
}
