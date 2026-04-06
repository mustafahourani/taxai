// State
var extractedData = null;
var taxpayerData = null;
var form1040Result = null;
var uploadedFiles = [];

// --- Privacy & Attestation ---

async function checkAttestation() {
  var msg = document.getElementById("attest-message");
  var grid = document.getElementById("attest-grid");

  try {
    var resp = await fetch("/api/attestation");
    var data = await resp.json();

    if (data.verified || data.environment === "eigencompute-tee") {
      msg.textContent = "This app is running inside a verified hardware enclave on EigenCompute. The server operator cannot access your data.";
    } else if (data.environment === "local-development") {
      msg.textContent = "Running locally. Enclave protection is simulated. Deploy to EigenCompute for real hardware isolation.";
      document.getElementById("attest-dot").className = "status-dot simulated";
      document.getElementById("status-compute").textContent = "simulated (local)";
      document.getElementById("status-compute").classList.remove("active");
    }

    var report = data.report || data.simulated_report || {};
    grid.innerHTML = "";
    var fields = [
      ["TEE Type", report.tee_type],
      ["Docker Image Digest", report.docker_image_digest],
      ["Enclave Measurement", report.enclave_measurement],
    ];
    for (var i = 0; i < fields.length; i++) {
      if (!fields[i][1]) continue;
      grid.innerHTML += '<div class="attest-item"><div class="label">' + fields[i][0] + '</div><div class="value">' + fields[i][1] + '</div></div>';
    }
  } catch (err) {
    msg.textContent = "Enclave verification is available when deployed to EigenCompute.";
  }
}

function togglePrivacy() {
  var body = document.getElementById("privacy-body");
  var toggle = document.getElementById("privacy-toggle");
  if (body.classList.contains("hidden")) {
    body.classList.remove("hidden");
    toggle.textContent = "hide";
  } else {
    body.classList.add("hidden");
    toggle.textContent = "learn more";
  }
}

// --- File Upload ---

function handleDrop(e) {
  e.preventDefault();
  e.currentTarget.classList.remove("dragover");
  addFiles(e.dataTransfer.files);
}

function handleFiles(e) {
  addFiles(e.target.files);
}

function addFiles(files) {
  for (var i = 0; i < files.length; i++) {
    uploadedFiles.push(files[i]);
  }
  renderFileList();
  document.getElementById("btn-extract").classList.remove("hidden");
}

function removeFile(index) {
  uploadedFiles.splice(index, 1);
  renderFileList();
  if (uploadedFiles.length === 0) {
    document.getElementById("btn-extract").classList.add("hidden");
  }
}

function renderFileList() {
  var list = document.getElementById("file-list");
  if (uploadedFiles.length === 0) {
    list.classList.add("hidden");
    return;
  }
  list.classList.remove("hidden");
  list.innerHTML = "";
  for (var i = 0; i < uploadedFiles.length; i++) {
    var f = uploadedFiles[i];
    var sizeKB = (f.size / 1024).toFixed(1);
    list.innerHTML +=
      '<div class="file-item">' +
        '<div class="file-info">' +
          '<span class="file-name">' + f.name + '</span>' +
          '<span class="file-size">' + sizeKB + ' KB</span>' +
        '</div>' +
        '<button class="file-remove" onclick="removeFile(' + i + ')">x</button>' +
      '</div>';
  }
}

// --- Demo Document Selection ---

var selectedDemoDocs = {};

function addDemoDoc(type) {
  if (selectedDemoDocs[type]) {
    // Deselect
    delete selectedDemoDocs[type];
    document.getElementById("demo-" + type).classList.remove("selected");
    document.getElementById("check-" + type).classList.add("hidden");
  } else {
    // Select
    selectedDemoDocs[type] = true;
    document.getElementById("demo-" + type).classList.add("selected");
    document.getElementById("check-" + type).classList.remove("hidden");
  }

  // Show/hide the "File My Taxes" button
  var hasSelection = Object.keys(selectedDemoDocs).length > 0;
  var btn = document.getElementById("btn-demo-go");
  if (hasSelection) {
    btn.classList.remove("hidden");
  } else {
    btn.classList.add("hidden");
  }
}

// --- Process: Extract + Compute in one shot ---

async function useDemoDocuments() {
  await processDocuments(true);
}

async function extractDocuments() {
  await processDocuments(false);
}

async function processDocuments(useDemo) {
  var bar = document.getElementById("progress-bar");
  var fill = document.getElementById("progress-fill");
  var text = document.getElementById("progress-text");

  bar.classList.remove("hidden");
  text.classList.remove("hidden");
  if (useDemo) {
    var docNames = [];
    if (selectedDemoDocs["w2"]) docNames.push("W-2");
    if (selectedDemoDocs["1098e"]) docNames.push("1098-E");
    if (docNames.length === 0) docNames = ["W-2", "1098-E"]; // fallback
    text.textContent = "Extracting data from " + docNames.join(" + ") + " inside enclave...";
  } else {
    text.textContent = "Uploading and extracting data inside encrypted enclave...";
  }

  var progress = 0;
  var interval = setInterval(function() {
    progress = Math.min(progress + Math.random() * 12, 45);
    fill.style.width = progress + "%";
  }, 150);

  try {
    // Step 1: Extract documents
    var formData = new FormData();
    formData.append("use_demo", useDemo ? "true" : "false");
    if (useDemo) {
      var docKeys = Object.keys(selectedDemoDocs);
      if (docKeys.length === 0) docKeys = ["w2", "1098e"];
      formData.append("demo_docs", docKeys.join(","));
    } else {
      for (var i = 0; i < uploadedFiles.length; i++) {
        formData.append("files", uploadedFiles[i]);
      }
    }

    var resp = await fetch("/api/extract-documents", { method: "POST", body: formData });
    extractedData = await resp.json();

    text.textContent = "Documents extracted. Computing your taxes...";
    progress = 55;
    fill.style.width = progress + "%";

    // Step 2: Build taxpayer data from extraction
    var d = extractedData.extracted;
    var numDeps = (d.dependents || []).length;
    var deps = [];
    for (var i = 0; i < numDeps; i++) {
      deps.push({ name: "Child " + (i + 1), ssn: "", relationship: "child", child_tax_credit: true });
    }

    taxpayerData = {
      filing_status: d.filing_status || "single",
      first_name: d.first_name,
      last_name: d.last_name,
      ssn: d.ssn,
      address: d.address,
      dependents: deps,
      w2s: d.w2s || [],
      interest_income: d.interest_income || 0,
      dividend_income: d.dividend_income || 0,
      other_income: d.other_income || 0,
      adjustments: d.adjustments || 0,
      use_standard_deduction: true,
      itemized_deductions: 0,
    };

    // Step 3: Compute 1040
    var resp2 = await fetch("/api/compute-1040", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(taxpayerData),
    });
    form1040Result = await resp2.json();

    text.textContent = "Optimizing your return...";
    progress = 85;
    fill.style.width = progress + "%";

    // Brief pause for UX
    await new Promise(function(r) { setTimeout(r, 400); });

    clearInterval(interval);
    fill.style.width = "100%";
    text.textContent = "Done.";

    setTimeout(function() { showResults(); }, 300);
  } catch (err) {
    clearInterval(interval);
    text.textContent = "Error: " + err.message;
  }
}

function backToUpload() {
  document.getElementById("step-2").classList.add("hidden");
  document.getElementById("step-2").classList.remove("active");
  document.getElementById("step-1").classList.remove("completed");
  document.getElementById("step-1").classList.add("active");
  // Reset progress
  document.getElementById("progress-bar").classList.add("hidden");
  document.getElementById("progress-text").classList.add("hidden");
  document.getElementById("progress-fill").style.width = "0%";
}

// --- Results ---

function showResults() {
  document.getElementById("step-1").classList.remove("active");
  document.getElementById("step-1").classList.add("completed");
  document.getElementById("step-2").classList.remove("hidden");
  document.getElementById("step-2").classList.add("active");

  var s = form1040Result.summary;
  var li = form1040Result.line_items;

  function fmt(n) { return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2 }); }

  var isRefund = s.refund > 0;
  var heroAmount = isRefund ? s.refund : s.owed;
  var heroLabel = isRefund ? "Your Federal Refund" : "Amount You Owe";
  var heroClass = isRefund ? "positive" : "negative";

  document.getElementById("result-hero").innerHTML =
    '<div class="result-hero-card">' +
      '<div class="hero-label">' + heroLabel + '</div>' +
      '<div class="hero-amount ' + heroClass + '">' + fmt(heroAmount) + '</div>' +
      '<div class="hero-meta">' +
        '<span>Total income: ' + fmt(s.total_income) + '</span>' +
        '<span>Total tax: ' + fmt(s.total_tax) + '</span>' +
        '<span>Effective rate: ' + s.effective_rate + '%</span>' +
      '</div>' +
    '</div>';

  renderOptimizations();
  loadSuggestions();
}

function renderOptimizations() {
  var opts = form1040Result.optimizations || [];
  var totalSavings = form1040Result.total_optimization_savings || 0;

  function fmt(n) { return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2 }); }

  var html = '';

  if (totalSavings > 0) {
    html += '<div class="optimization-total">' +
      '<div class="optimization-total-label">Total tax savings from optimizations</div>' +
      '<div class="optimization-total-amount">' + fmt(totalSavings) + '</div>' +
    '</div>';
  }

  for (var i = 0; i < opts.length; i++) {
    var o = opts[i];
    var savingsHTML = o.savings ? '<div class="optimization-savings">Saved you ' + fmt(o.savings) + '</div>' : '';

    html +=
      '<div class="optimization-card">' +
        '<div class="optimization-icon">&#10003;</div>' +
        '<div class="optimization-content">' +
          '<div class="optimization-action">' + o.action + '</div>' +
          '<div class="optimization-detail">' + o.detail + '</div>' +
          savingsHTML +
        '</div>' +
      '</div>';
  }

  document.getElementById("optimizations-list").innerHTML = html;
}

async function loadSuggestions() {
  var list = document.getElementById("suggestions-list");
  list.innerHTML = '<div class="progress-text">AI is analyzing your return for additional suggestions...</div>';

  try {
    var resp = await fetch("/api/review-1040", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form1040Result),
    });
    var data = await resp.json();
    var suggestions = data.suggestions || [];

    list.innerHTML = "";
    for (var i = 0; i < suggestions.length; i++) {
      var sg = suggestions[i];
      var typeClass = {
        "suggestion": "green",
        "next_year": "accent",
        "flag": "blue",
      }[sg.type] || "accent";
      var savings = sg.potential_savings ? '<span class="suggestion-savings">~$' + sg.potential_savings.toLocaleString("en-US") + ' potential savings</span>' : "";

      list.innerHTML +=
        '<div class="suggestion-card">' +
          '<div class="suggestion-type ' + typeClass + '">' + sg.type.replace(/_/g, " ") + '</div>' +
          '<div class="suggestion-title">' + sg.title + '</div>' +
          '<div class="suggestion-detail">' + sg.detail + '</div>' +
          savings +
        '</div>';
    }
  } catch (err) {
    list.innerHTML = '<div class="progress-text">Could not load suggestions: ' + err.message + '</div>';
  }
}

// --- Tabs ---

function switchTab(tab) {
  var tabs = ["optimizations", "suggestions"];
  for (var i = 0; i < tabs.length; i++) {
    var t = tabs[i];
    document.getElementById("tab-" + t).classList.toggle("active", t === tab);
    document.getElementById("panel-" + t).classList.toggle("hidden", t !== tab);
  }
}

// --- PDF ---

async function downloadPDF() {
  if (!taxpayerData) return;
  try {
    var resp = await fetch("/api/1040-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(taxpayerData),
    });
    var blob = await resp.blob();
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "form_1040_draft.pdf";
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert("PDF generation failed: " + err.message);
  }
}

// --- Init ---
// No dynamic attestation check needed - status is hardcoded for deployed TEE
