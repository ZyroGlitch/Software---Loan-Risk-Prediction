// get-started-contribution.js file

import {
  BaseLineFeatures,
  OptimizedFeatures,
} from "../data/get-started-contribution-data.js";

export function renderFeatures(containerId, type = "baseline") {
  const container = document.getElementById(containerId);

  if (!container) return;
  const html = features
    .map((feature, index) => {
      const imp = Number(feature.importance || 0).toFixed(2);
      const con = Number(feature.contribution || 0).toFixed(2);

      return `
        <div class="feature-item">
          <div class="feature-result-box">
            <div class="feature-header">
              <div class="feature-name-container">
                <span class="feature-number">${index + 1}</span>
                <h1 class="feature-name">${feature.name}</h1>
              </div>
            </div>

            <div class="feature-result">
              <div class="feature-result-label">
                <p>Impact</p>
                <span class="feature-importance">${imp}%</span>
              </div>

              <div class="progress-bar-container">
                <div class="progress-bar" style="width: ${imp}%"></div>
              </div>
            </div>

            <div class="feature-result">
              <div class="feature-result-label">
                <p>Contribution</p>
                <span class="feature-importance">${con}%</span>
              </div>

              <div class="progress-bar-container">
                <div class="progress-bar" style="width: ${con}%"></div>
              </div>
            </div>
          </div>
        </div>
      `;
    })
    .join("");
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
