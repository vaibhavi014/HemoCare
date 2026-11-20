/**
 * HEMOCARE: Offline Blood Bank Management System
 * Client-Side Application JavaScript (Zero Internet / Zero CDN)
 */

document.addEventListener("DOMContentLoaded", function () {
  initAlertDismissers();
  initDonorAutoFill();
  initUnitAutoFill();
  initSerologyAutoCalculate();
  initDashboardCharts();
});

// ==========================================
// 1. Alert Dismissers
// ==========================================
function initAlertDismissers() {
  document.querySelectorAll(".alert-close").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const alert = btn.closest(".alert");
      if (alert) {
        alert.style.transition = "opacity 0.2s ease";
        alert.style.opacity = "0";
        setTimeout(() => alert.remove(), 200);
      }
    });
  });
}

// ==========================================
// 2. Donation Form: Auto-fill Donor Info
// ==========================================
function initDonorAutoFill() {
  const donorSelect = document.getElementById("select_donor_id");
  if (!donorSelect) return;

  const nameInput = document.getElementById("donor_name_display");
  const bgInput = document.getElementById("blood_group_display");
  const ageInput = document.getElementById("donor_age_display");
  const statusBadge = document.getElementById("donor_status_badge");

  function updateDonor() {
    const donorId = donorSelect.value;
    if (!donorId) {
      if (nameInput) nameInput.value = "";
      if (bgInput) bgInput.value = "";
      if (ageInput) ageInput.value = "";
      if (statusBadge) statusBadge.textContent = "";
      return;
    }

    fetch(`/api/donors/${donorId}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.error) return;
        if (nameInput) nameInput.value = data.name;
        if (bgInput) bgInput.value = data.blood_group;
        if (ageInput) ageInput.value = `${data.age} yrs (${data.gender})`;
        if (statusBadge) {
          statusBadge.textContent = `Status: ${data.status}`;
          statusBadge.className = `badge badge-${data.status.toLowerCase()}`;
        }
      })
      .catch((err) => console.error("Error fetching donor info:", err));
  }

  donorSelect.addEventListener("change", updateDonor);
  if (donorSelect.value) updateDonor();
}

// ==========================================
// 3. Issue / Discard Form: Auto-fill Unit Info & Eligibility
// ==========================================
function initUnitAutoFill() {
  const unitSelect = document.getElementById("select_unit_id");
  if (!unitSelect) return;

  const bgField = document.getElementById("unit_bg_display");
  const compField = document.getElementById("unit_comp_display");
  const expField = document.getElementById("unit_exp_display");
  const serField = document.getElementById("unit_ser_display");
  const banner = document.getElementById("unit_eligibility_box");
  const submitBtn = document.getElementById("btn_submit_issue");

  function updateUnit() {
    const unitId = unitSelect.value;
    if (!unitId) {
      if (bgField) bgField.value = "";
      if (compField) compField.value = "";
      if (expField) expField.value = "";
      if (serField) serField.value = "";
      if (banner) banner.style.display = "none";
      if (submitBtn) submitBtn.disabled = false;
      return;
    }

    fetch(`/api/inventory/unit/${unitId}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.error) return;
        if (bgField) bgField.value = data.blood_group;
        if (compField) compField.value = data.component_type;
        if (expField) expField.value = data.expiry_date;
        if (serField) serField.value = data.serology_status;

        if (banner) {
          banner.style.display = "block";
          if (data.is_eligible) {
            banner.className = "unit-eligibility-banner banner-eligible";
            banner.innerHTML = `<strong>Eligible for Issue:</strong> ${data.unit_code} (${data.blood_group} ${data.component_type}) has Non-Reactive serology and is valid until ${data.expiry_date}.`;
            if (submitBtn) submitBtn.disabled = false;
          } else {
            banner.className = "unit-eligibility-banner banner-ineligible";
            banner.innerHTML = `<strong>Issue Prohibited:</strong> ${data.eligibility_message}`;
            if (submitBtn) submitBtn.disabled = true;
          }
        }
      })
      .catch((err) => console.error("Error fetching unit info:", err));
  }

  unitSelect.addEventListener("change", updateUnit);
  if (unitSelect.value) updateUnit();
}

// ==========================================
// 4. Serology Form: Auto-calculate Overall Result
// ==========================================
function initSerologyAutoCalculate() {
  const hiv = document.getElementById("hiv_select");
  const hbsag = document.getElementById("hbsag_select");
  const hcv = document.getElementById("hcv_select");
  const syphilis = document.getElementById("syphilis_select");
  const malaria = document.getElementById("malaria_select");
  const overallSelect = document.getElementById("overall_result_select");
  const overallBadge = document.getElementById("overall_result_badge");

  if (!hiv || !hbsag || !hcv || !syphilis || !malaria || !overallSelect) return;

  function calculateResult() {
    const tests = [hiv.value, hbsag.value, hcv.value, syphilis.value, malaria.value];
    let result = "Pending";

    if (tests.some((t) => t === "Reactive")) {
      result = "Reactive";
    } else if (tests.every((t) => t === "Non-Reactive")) {
      result = "Non-Reactive";
    } else {
      result = "Pending";
    }

    overallSelect.value = result;
    if (overallBadge) {
      overallBadge.textContent = result.toUpperCase();
      overallBadge.className = `badge badge-${result.toLowerCase()}`;
    }
  }

  [hiv, hbsag, hcv, syphilis, malaria].forEach((el) => {
    el.addEventListener("change", calculateResult);
  });

  calculateResult();
}

// ==========================================
// 5. Offline Canvas Charts for Dashboard
// ==========================================
function initDashboardCharts() {
  const stockCanvas = document.getElementById("chart_stock");
  const donationsCanvas = document.getElementById("chart_donations");
  const issuesCanvas = document.getElementById("chart_issues");
  const distributionCanvas = document.getElementById("chart_distribution");

  if (!stockCanvas && !donationsCanvas && !issuesCanvas && !distributionCanvas) return;

  // Retrieve embedded data if present on window, else fetch from API
  if (window.HEMOCARE_CHART_DATA) {
    renderAllCharts(window.HEMOCARE_CHART_DATA);
  } else {
    fetch("/api/chart-data")
      .then((res) => res.json())
      .then((data) => renderAllCharts(data))
      .catch((err) => console.error("Error loading chart data:", err));
  }
}

function renderAllCharts(data) {
  // Chart 1: Blood/Component Stock (Horizontal Bar Chart)
  drawHorizontalBarChart("chart_stock", data.component_distribution, [
    "#990000",
    "#c0392b",
    "#2563eb",
    "#16a34a"
  ]);

  // Chart 2: Monthly Donations (Vertical Column Chart)
  drawVerticalBarChart("chart_donations", data.monthly_labels, data.monthly_donations, "#990000");

  // Chart 3: Monthly Issues (Vertical Column Chart)
  drawVerticalBarChart("chart_issues", data.monthly_labels, data.monthly_issues, "#2563eb");

  // Chart 4: Component Distribution (Donut Chart)
  drawDonutChart("chart_distribution", data.component_distribution, [
    "#990000",
    "#c0392b",
    "#2563eb",
    "#16a34a"
  ]);
}

// Canvas Helper: Horizontal Bar Chart
function drawHorizontalBarChart(canvasId, dictData, colorPalette) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);

  const keys = Object.keys(dictData);
  const values = Object.values(dictData);
  const maxVal = Math.max(...values, 5);

  const paddingLeft = 110;
  const paddingRight = 40;
  const paddingTop = 20;
  const paddingBottom = 20;
  const usableWidth = width - paddingLeft - paddingRight;
  const barHeight = 24;
  const gap = (height - paddingTop - paddingBottom - keys.length * barHeight) / (keys.length + 1);

  ctx.font = "12px -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";

  keys.forEach((key, i) => {
    const val = values[i];
    const y = paddingTop + gap * (i + 1) + barHeight * i;
    const barW = (val / maxVal) * usableWidth;

    // Label
    ctx.fillStyle = "#1e293b";
    ctx.textAlign = "right";
    ctx.fillText(key, paddingLeft - 12, y + 16);

    // Background track
    ctx.fillStyle = "#f1f5f9";
    ctx.beginPath();
    ctx.roundRect(paddingLeft, y, usableWidth, barHeight, 4);
    ctx.fill();

    // Value bar
    if (barW > 0) {
      ctx.fillStyle = colorPalette[i % colorPalette.length];
      ctx.beginPath();
      ctx.roundRect(paddingLeft, y, Math.max(barW, 6), barHeight, 4);
      ctx.fill();
    }

    // Value text
    ctx.fillStyle = "#1e293b";
    ctx.textAlign = "left";
    ctx.fillText(`${val} units`, paddingLeft + barW + 8, y + 16);
  });
}

// Canvas Helper: Vertical Column Chart
function drawVerticalBarChart(canvasId, labels, values, color) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);

  const maxVal = Math.max(...values, 5);
  const paddingLeft = 40;
  const paddingRight = 20;
  const paddingTop = 30;
  const paddingBottom = 40;
  const usableWidth = width - paddingLeft - paddingRight;
  const usableHeight = height - paddingTop - paddingBottom;
  const colWidth = usableWidth / labels.length - 16;

  ctx.font = "11px -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";

  // Grid lines
  ctx.strokeStyle = "#e2e8f0";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let step = 0; step <= 4; step++) {
    const y = paddingTop + (usableHeight / 4) * step;
    ctx.moveTo(paddingLeft, y);
    ctx.lineTo(width - paddingRight, y);

    const labelVal = Math.round(maxVal - (maxVal / 4) * step);
    ctx.fillStyle = "#64748b";
    ctx.textAlign = "right";
    ctx.fillText(labelVal, paddingLeft - 8, y + 4);
  }
  ctx.stroke();

  // Draw Bars
  labels.forEach((label, i) => {
    const val = values[i];
    const barH = (val / maxVal) * usableHeight;
    const x = paddingLeft + (usableWidth / labels.length) * i + 8;
    const y = paddingTop + usableHeight - barH;

    // Bar
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.roundRect(x, y, colWidth, barH, [4, 4, 0, 0]);
    ctx.fill();

    // Value on top
    if (val > 0) {
      ctx.fillStyle = "#1e293b";
      ctx.textAlign = "center";
      ctx.fillText(val, x + colWidth / 2, y - 6);
    }

    // X Axis Label
    ctx.fillStyle = "#64748b";
    ctx.textAlign = "center";
    ctx.fillText(label, x + colWidth / 2, height - 12);
  });
}

// Canvas Helper: Donut Chart
function drawDonutChart(canvasId, dictData, colorPalette) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);

  const keys = Object.keys(dictData);
  const values = Object.values(dictData);
  const total = values.reduce((a, b) => a + b, 0);

  const centerX = width / 2 - 50;
  const centerY = height / 2;
  const outerRadius = 80;
  const innerRadius = 45;

  let startAngle = -Math.PI / 2;

  if (total === 0) {
    // Empty state circle
    ctx.strokeStyle = "#e2e8f0";
    ctx.lineWidth = 20;
    ctx.beginPath();
    ctx.arc(centerX, centerY, 60, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillStyle = "#64748b";
    ctx.font = "12px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("No Stock", centerX, centerY + 4);
    return;
  }

  // Draw Segments
  keys.forEach((key, i) => {
    const val = values[i];
    if (val === 0) return;
    const sliceAngle = (val / total) * 2 * Math.PI;
    const endAngle = startAngle + sliceAngle;

    ctx.fillStyle = colorPalette[i % colorPalette.length];
    ctx.beginPath();
    ctx.arc(centerX, centerY, outerRadius, startAngle, endAngle);
    ctx.arc(centerX, centerY, innerRadius, endAngle, startAngle, true);
    ctx.closePath();
    ctx.fill();

    startAngle = endAngle;
  });

  // Center Total
  ctx.fillStyle = "#1e293b";
  ctx.font = "bold 16px sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(total, centerX, centerY);
  ctx.font = "10px sans-serif";
  ctx.fillStyle = "#64748b";
  ctx.fillText("TOTAL", centerX, centerY + 14);

  // Draw Legend on the right side
  const legendX = centerX + outerRadius + 30;
  let legendY = centerY - (keys.length * 22) / 2 + 10;

  ctx.font = "11px -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
  keys.forEach((key, i) => {
    const val = values[i];
    const pct = total > 0 ? Math.round((val / total) * 100) : 0;

    // Color box
    ctx.fillStyle = colorPalette[i % colorPalette.length];
    ctx.beginPath();
    ctx.roundRect(legendX, legendY - 8, 10, 10, 2);
    ctx.fill();

    // Text
    ctx.fillStyle = "#1e293b";
    ctx.textAlign = "left";
    ctx.fillText(`${key}: ${val} (${pct}%)`, legendX + 16, legendY);

    legendY += 22;
  });
}
