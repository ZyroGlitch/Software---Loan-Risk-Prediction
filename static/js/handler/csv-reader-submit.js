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

  // New header: 2 columns FIRST, then original headers
  const headerTr = document.createElement("tr");

  const thReport = document.createElement("th");
  thReport.textContent = "Report";
  headerTr.appendChild(thReport);

  const thDecision = document.createElement("th");
  thDecision.textContent = "Decision";
  headerTr.appendChild(thDecision);

  visibleIndexes.forEach(i => {
    const th = document.createElement("th");
    th.textContent = headers[i];
    headerTr.appendChild(th);
  });

  thead.appendChild(headerTr);

  // Each row: [ReportLink, Decision, ...original columns]
  dataRows.forEach((rowArr, idx) => {
    const tr = document.createElement("tr");

    const recordObj = rowToObject(headers, rowArr);
    const recordId = idx + 1;

    // 1) Report link column
    const tdReport = document.createElement("td");
    tdReport.className = "report-link";

    const a = document.createElement("a");
    a.href = "#";
    a.textContent = "View PDF";
    a.addEventListener("click", (ev) => {
      ev.preventDefault();
      openRecordTabAsPDF(recordObj, recordId);
    });

    tdReport.appendChild(a);
    tr.appendChild(tdReport);

    // 2) Decision column (Accepted green / Rejected red)
    const decision = fakePredict(recordObj); // Replace this later with real backend call if you want
    const tdDecision = document.createElement("td");
    tdDecision.textContent = decision;
    tdDecision.className = decision === "Accepted" ? "accepted" : "rejected";
    tr.appendChild(tdDecision);

    // Original columns
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

// SIMPLE demo prediction logic
// Replace with fetch() to your Flask endpoint when ready.
function fakePredict(recordObj) {
  const values = Object.values(recordObj).join(" ").toLowerCase();
  const accepted = values.includes("yes") || values.includes("approved");
  return accepted ? "Accepted" : "Rejected";
}

// Open new tab with full record details + "Download PDF" (Print -> Save as PDF)
function openRecordTabAsPDF(recordObj, recordId) {
  const w = window.open("", "_blank");
  if (!w) return;

  // const rowsHtml = Object.entries(recordObj)
  //   .map(
  //     ([k, v]) =>
  //       `<tr>
  //         <th>${escapeHtml(k)}</th>
  //         <td>${escapeHtml(String(v))}</td>
  //       </tr>`
  //   )
  //   .join("");

  const rowsHtml = Object.entries(recordObj)
  .filter(([k]) => !HIDDEN_COLUMNS.includes(k.toLowerCase()))


  w.document.write(`
    <!doctype html>
    <html>
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Record ${recordId} Report</title>

        <style>
          body {
            font-family: Arial, sans-serif;
            margin: 24px;
          }

          .container {
            max-width: 900px;
            margin: 0 auto;
          }

          table {
            width: 100%;
            border-collapse: collapse;
          }

          th, td {
            padding: 8px;
            border-bottom: 1px solid #eee;
            text-align: left;
          }

          th {
            background: #fafafa;
          }

          .actions {
            display: flex;
            gap: 10px;
            margin-bottom: 14px;
          }

          button {
            padding: 10px 14px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
          }

          .download {
            background: #000;
            color: #fff;
            border: none;
          }

          .close {
            background: #fff;
            border: 1px solid #ddd;
          }

          /* 🔥 THIS IS THE FIX */
          @media print {
            .no-print {
              display: none !important;
            }

            body {
              margin: 0;
            }

            @page {
              margin: 20mm;
            }
          }
        </style>
      </head>

      <body>
        <div class="container">

          <!-- Visible on screen ONLY -->
          <div class="no-print">
            <h2>Record ${recordId} - Full Details</h2>
            <p style="color:#555;">
              Click <b>Download PDF</b> then choose <b>Save as PDF</b> in the print dialog.
            </p>

            <div class="actions">
              <button class="download" id="downloadPdf">Download PDF</button>
              <button class="close" id="closeTab">Close</button>
            </div>
          </div>

          <!-- ALWAYS INCLUDED IN PDF -->
          <table>
            ${rowsHtml}
          </table>

        </div>

        <script>
          document.getElementById("downloadPdf")
            .addEventListener("click", () => window.print());

          document.getElementById("closeTab")
            .addEventListener("click", () => window.close());
        </script>
      </body>
    </html>
  `);

  w.document.close();
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
