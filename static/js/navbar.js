// Configuration for the navigation bar
const navConfig = {
  website: {
    name: "Loan Risk Prediction",
    url: "/home",
  },
  links: [
    { name: "Home", url: "/home" },
    { name: "Features", url: "/features" },
    { name: "How it works", url: "/function" },
    { name: "Contact", url: "/contact" },
  ],
};

// Function to load Lucide icons
function loadLucideIcons(callback) {
  if (window.lucide) {
    callback();
    return;
  }
  const script = document.createElement("script");
  script.src = "https://unpkg.com/lucide@latest";
  script.onload = callback;
  document.head.appendChild(script);
}

function createNavBar() {
  const currentPage = window.location.pathname.split("/").pop();

  const navHtml = `
    <nav class="nav-container">
        <div>
          <a href="${navConfig.website.url}" class="nav-logo">   
          <i data-lucide="dollar-sign" class = "nav-logo-icon"></i>  
            ${navConfig.website.name}
          </a>
        </div>
        
        <ul class="nav-menu">
          ${navConfig.links
            .map(
              (link) => `
            <li class="nav-item">
              <a 
                href="${link.url}" 
                class="nav-link ${currentPage === link.url ? "active" : ""}"
              >
                ${link.name}
              </a>
            </li>
          `
            )
            .join("")}
          <li class="nav-item">
            <a 
              href="https://github.com/Reignear/loan-risk-prediction-native"
              target="_blank" 
              rel="noopener noreferrer" 
              class="nav-link nav-link-icon"
            >
              <i data-lucide="github"></i>
              Code Repository
            </a>
          </li>
        </ul>
    </nav>
  `;

  document.getElementById("navbar").innerHTML = navHtml;

  // Initialize icons after navbar is created
  if (window.lucide) {
    lucide.createIcons();
  }
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  loadLucideIcons(() => {
    createNavBar();
  });
});
