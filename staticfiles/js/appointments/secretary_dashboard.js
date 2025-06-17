document.addEventListener("DOMContentLoaded", function() {
  // ==========================
  // Cache DOM Elements
  // ==========================
  const calendarElem       = document.getElementById("calendar-inline");
  const clockElem          = document.getElementById("digital-clock");
  const dateElem           = document.getElementById("digital-date");
  const chartDataElement   = document.getElementById("chart-data");
  const chartCanvas        = document.getElementById("patientsWeekChart");

  // ==========================
  // Flatpickr Calendar
  // ==========================
  if (calendarElem) {
    flatpickr(calendarElem, {
      inline: true,
      defaultDate: new Date().toISOString().split("T")[0],
      locale: "en",
      dateFormat: "Y-m-d",
      minDate: "today",
      disableMobile: true
    });
  }

  // ==========================
  // Digital Clock & Date
  // ==========================
  function updateClock() {
    const now = new Date();
    let h = now.getHours(), m = now.getMinutes(), s = now.getSeconds();
    h = h < 10 ? "0" + h : h;
    m = m < 10 ? "0" + m : m;
    s = s < 10 ? "0" + s : s;
    if (clockElem) clockElem.textContent = `${h}:${m}:${s}`;

    if (dateElem) {
      const opts = { weekday: 'short', year: 'numeric', month: 'short', day: '2-digit' };
      dateElem.textContent = now.toLocaleDateString('en-GB', opts);
    }
  }
  updateClock();
  setInterval(updateClock, 1000);

  // ==========================
  // Chart.js – Weekly Overview
  // ==========================
  if (chartDataElement && chartCanvas) {
    try {
      const chartData = JSON.parse(chartDataElement.textContent);
      const pastelColors = ['#A3C8F7','#B8E0D2','#FFD6E0','#FFF5BA','#E2F0CB','#FFBCBC','#C1BFFF'];
      const barColors = chartData.labels.map((_, i) => pastelColors[i % pastelColors.length]);
      const ctx = chartCanvas.getContext("2d");
      new Chart(ctx, {
        type: "bar",
        data: {
          labels: chartData.labels,
          datasets: [{
            label: "Patients",
            data: chartData.data,
            backgroundColor: barColors,
            borderRadius: 14,
            borderSkipped: false,
            maxBarThickness: 56,
            minBarLength: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: ctx => ` ${ctx.parsed.y} patients` } }
          },
          scales: {
            x: { grid: { display: false } },
            y: { beginAtZero: true, grid: { color: "#e6f2fa" }, ticks: { stepSize: 1 } }
          },
          animation: { duration: 1200, easing: "easeOutQuart" }
        }
      });
    } catch (err) {
      console.error("Error initializing Weekly Chart:", err);
    }
  }

  // ==========================
  // CSRF Helper
  // ==========================
  function getCookie(name) {
    let cookieValue = null;
    document.cookie.split(';').forEach(c => {
      c = c.trim();
      if (c.startsWith(name + '=')) {
        cookieValue = decodeURIComponent(c.slice(name.length + 1));
      }
    });
    return cookieValue;
  }

  // ==========================
  // Call Next Patient
  // ==========================
  document.querySelectorAll('.call-next-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const doctorId = btn.dataset.doctor;
      try {
        const urlBase = window.QUEUE_API.replace('api/queue-number/', '');
        const res = await fetch(`${urlBase}call-next/${doctorId}/`, {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        if (!res.ok) throw new Error();
        // Refresh the page or section
        location.reload();
      } catch {
        console.error('Failed to call next patient');
      }
    });
  });
});