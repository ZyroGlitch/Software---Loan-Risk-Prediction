// csv-reader-submit.js file

const fileInput = document.getElementById("csvFile");
const table = document.getElementById("table");
const errorEl = document.getElementById("error");
const metaEl = document.getElementById("meta");
const predictBtn = document.getElementById("predict-btn");

let loadedRows = null;

// Data Loader Functions
const loader = document.getElementById("loader");
const progressFill = document.getElementById("progressFill");
const progressLeft = document.getElementById("progressLeft");
const progressRight = document.getElementById("progressRight");
const loaderTitle = document.getElementById("loaderTitle");
const loaderSub = document.getElementById("loaderSub");

const fileNameEl = document.getElementById("fileName");
predictBtn.disabled = true;

const HIDDEN_COLUMNS = ["deposit"];

function showLoader(title = "Loading your CSV…", sub = "Reading file and preparing preview") {
  loaderTitle.textContent = title;
  loaderSub.textContent = sub;
  progressFill.style.width = "0%";
  progressLeft.textContent = "Please wait…";
  progressRight.textContent = "0%";
  loader.classList.remove("fade-out");
  loader.style.display = "flex";
}

function setLoaderProgress(percent, leftText = "") {
  const p = Math.max(0, Math.min(100, percent));
  progressFill.style.width = p + "%";
  progressRight.textContent = p + "%";
  if (leftText) progressLeft.textContent = leftText;
}

function hideLoader() {
  loader.classList.add("fade-out");
  setTimeout(() => {
    loader.style.display = "none";
    loader.classList.remove("fade-out");
  }, 220);
}

// -------------------------------------------------

fileInput.addEventListener("change", async (e) => {
  errorEl.textContent = "";
  metaEl.textContent = "";
  table.innerHTML = "";
  loadedRows = null;

  const file = e.target.files?.[0];

  fileNameEl.textContent = file ? file.name : "No file selected";
  predictBtn.disabled = true;

  if (!file) return;

  try {
    showLoader("Loading your CSV…", `Reading: ${file.name}`);
    setLoaderProgress(10, "Reading file…");

    const text = await file.text();
    setLoaderProgress(45, "Parsing CSV…");

    await new Promise((r) => setTimeout(r, 120)); // small UI smoothness
    const rows = parseCSV(text);

    if (!rows.length) {
      hideLoader();
      errorEl.textContent = "CSV is empty.";
      return;
    }

    setLoaderProgress(80, "Rendering table…");
    await new Promise((r) => setTimeout(r, 120));

    loadedRows = rows;
    renderTable(rows);

    setLoaderProgress(100, "Done!");
    metaEl.innerHTML = `Loaded <code>${file.name}</code> — Rows: <code>${
      rows.length - 1
    }</code>, Columns: <code>${rows[0].length}</code>`;

    predictBtn.disabled = false;
    setTimeout(hideLoader, 200);
  } catch (err) {
    hideLoader();
    errorEl.textContent = "Failed to read CSV: " + (err?.message || err);
  }
});

predictBtn.addEventListener("click", async () => {
  errorEl.textContent = "";

  if (!loadedRows || loadedRows.length < 2) {
    errorEl.textContent = "Upload a CSV first.";
    return;
  }

  try {
    predictBtn.disabled = true;

    showLoader("Running prediction…", "Preparing results and generating reports");
    setLoaderProgress(15, "Validating data…");
    await new Promise((r) => setTimeout(r, 150));

    setLoaderProgress(45, "Predicting records…");
    await new Promise((r) => setTimeout(r, 200));

    setLoaderProgress(75, "Updating table…");
    await renderPredictedTable(loadedRows);

    setLoaderProgress(100, "Done!");

    predictBtn.disabled = false;
    setTimeout(hideLoader, 200);
  } catch (err) {
    hideLoader();
    errorEl.textContent = "Prediction failed: " + (err?.message || err);

    predictBtn.disabled = false;
  }
});


function renderTable(rows) {
  table.innerHTML = "";

  const headers = rows[0];
  const visibleIndexes = headers
    .map((h, i) => (HIDDEN_COLUMNS.includes(h.toLowerCase()) ? -1 : i))
    .filter(i => i !== -1);

  const thead = document.createElement("thead");
  const tbody = document.createElement("tbody");

  const headerTr = document.createElement("tr");
  visibleIndexes.forEach(i => {
    const th = document.createElement("th");
    th.textContent = headers[i];
    headerTr.appendChild(th);
  });
  thead.appendChild(headerTr);

  for (let r = 1; r < rows.length; r++) {
    const tr = document.createElement("tr");
    visibleIndexes.forEach(i => {
      const td = document.createElement("td");
      td.textContent = rows[r][i];
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  }

  table.appendChild(thead);
  table.appendChild(tbody);
}

async function renderPredictedTable(rows) {
  table.innerHTML = "";

  const headers = rows[0];
  const visibleIndexes = headers
    .map((h, i) => (HIDDEN_COLUMNS.includes(h.toLowerCase()) ? -1 : i))
    .filter(i => i !== -1);

  const dataRows = rows.slice(1);

  const thead = document.createElement("thead");
  const tbody = document.createElement("tbody");

  const headerTr = document.createElement("tr");

  const thReport = document.createElement("th");
  thReport.textContent = "Report";
  headerTr.appendChild(thReport);

  visibleIndexes.forEach(i => {
    const th = document.createElement("th");
    th.textContent = headers[i];
    headerTr.appendChild(th);
  });

  thead.appendChild(headerTr);

  dataRows.forEach((rowArr) => {
    const tr = document.createElement("tr");

    const recordObj = rowToObject(headers, rowArr);

    const tdReport = document.createElement("td");
    tdReport.className = "report-link";

    const a = document.createElement("a");
    a.href = "#";
    a.textContent = "View PDF";
    a.addEventListener("click", (ev) => {
      ev.preventDefault();
      openRecordTabAsPDF(recordObj);
    });

    tdReport.appendChild(a);
    tr.appendChild(tdReport);

    visibleIndexes.forEach(i => {
      const td = document.createElement("td");
      td.textContent = rowArr[i];
      tr.appendChild(td);
    });

    tbody.appendChild(tr);
  });

  table.appendChild(thead);
  table.appendChild(tbody);
}


function rowToObject(headers, rowArr) {
  const obj = {};
  for (let i = 0; i < headers.length; i++) obj[headers[i]] = rowArr[i] ?? "";
  return obj;
}

// Open new tab with full record details + "Download PDF" (Print -> Save as PDF)
async function openRecordTabAsPDF(recordObj) {
  const payload = csvRowToPayload(recordObj);

  const requiredKeys = [
    "age","job","marital","education","contact","balance","housing","default","loan",
    "day","month","duration","campaign","pdays","previous","poutcome"
  ];

  const missing = requiredKeys.filter(k => payload[k] === null || payload[k] === "" || Number.isNaN(payload[k]));
  if (missing.length) {
    alert("Cannot generate PDF. Missing/invalid fields: " + missing.join(", "));
    return;
  }

  const res = await fetch("/report-row", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const t = await res.text();
    alert("Report failed: " + t);
    return;
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);

  window.open(url, "_blank");

  setTimeout(() => URL.revokeObjectURL(url), 15000);
}



function escapeHtml(s) {
  return s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// Your CSV parser (unchanged)
function parseCSV(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    const next = text[i + 1];

    if (c === '"') {
      if (inQuotes && next === '"') {
        field += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (c === "," && !inQuotes) {
      row.push(field);
      field = "";
    } else if ((c === "\n" || c === "\r") && !inQuotes) {
      if (c === "\r" && next === "\n") i++;
      row.push(field);
      field = "";
      if (!(row.length === 1 && row[0] === "")) rows.push(row);
      row = [];
    } else {
      field += c;
    }
  }

  row.push(field);
  if (!(row.length === 1 && row[0] === "")) rows.push(row);

  const cols = rows[0]?.length || 0;
  for (let r = 1; r < rows.length; r++) {
    while (rows[r].length < cols) rows[r].push("");
    if (rows[r].length > cols) rows[r] = rows[r].slice(0, cols);
  }

  return rows;
}

// CSV Report Payload Mapping
const CSV_VALUE_MAP = {
  job: {
    admin: 0,
    "blue-collar": 1,
    entrepreneur: 2,
    housemaid: 3,
    management: 4,
    retired: 5,
    "self-employed": 6,
    services: 7,
    student: 8,
    technician: 9,
    unemployed: 10,
    unknown: 11,
  },
  marital: {
    divorced: 0, 
    married: 1, 
    single: 2 
  },
  education: { 
    primary: 0, 
    secondary: 1, 
    tertiary: 2, 
    unknown: 3 
  },
  contact: { 
    cellular: 0, 
    telephone: 1, 
    unknown: 2 
  },
  housing: { 
    no: 0, 
    yes: 1 
  },
  default: { 
    no: 0, 
    yes: 1 
  },
  loan: { 
    no: 0, 
    yes: 1 
  },
  month: {
    jan: 4, january: 4,
    feb: 3, february: 3,
    mar: 7, march: 7,
    apr: 0, april: 0,
    may: 8,
    jun: 6, june: 6,
    jul: 5, july: 5,
    aug: 1, august: 1,
    sep: 11, sept: 11, september: 11,
    oct: 10, october: 10,
    nov: 9, november: 9,
    dec: 2, december: 2,
  },
  poutcome: { 
    failure: 0, 
    other: 1, 
    success: 2, 
    unknown: 3 
  },
};

function norm(s) {
  return String(s ?? "").trim().toLowerCase();
}

function toNumOrMap(key, value) {
  const v = String(value ?? "").trim();
  if (v === "") return null;
  if (!Number.isNaN(Number(v))) return Number(v);

  const map = CSV_VALUE_MAP[key];
  if (!map) return null;

  const k = norm(v);
  return Object.prototype.hasOwnProperty.call(map, k) ? map[k] : null;
}

function csvRowToPayload(recordObj) {
  return {
    age: toNumOrMap("age", recordObj.age),
    job: toNumOrMap("job", recordObj.job),
    marital: toNumOrMap("marital", recordObj.marital),
    education: toNumOrMap("education", recordObj.education),
    default: toNumOrMap("default", recordObj.default),
    balance: toNumOrMap("balance", recordObj.balance),
    housing: toNumOrMap("housing", recordObj.housing),
    loan: toNumOrMap("loan", recordObj.loan),
    contact: toNumOrMap("contact", recordObj.contact),
    day: toNumOrMap("day", recordObj.day),
    month: toNumOrMap("month", recordObj.month),
    duration: toNumOrMap("duration", recordObj.duration),
    campaign: toNumOrMap("campaign", recordObj.campaign),
    pdays: toNumOrMap("pdays", recordObj.pdays),
    previous: toNumOrMap("previous", recordObj.previous),
    poutcome: toNumOrMap("poutcome", recordObj.poutcome),
  };
}
