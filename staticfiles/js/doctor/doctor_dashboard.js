// static/js/doctor/doctor_dashboard.js

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
  // Flatpickr Calendar (رزنامة عصرية)
  // ==========================
  // في حال لم يتم تضمين عنصر التقويم في واجهة الطبيب، 
  // فلن يُنفذ هذا القسم لأن calendarElem سيكون null.
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
  // Digital Clock & Date (ساعة وتاريخ عصري)
  // ==========================
  function updateClock() {
    const now = new Date();
    // ساعات ودقائق وثوانٍ منسقة
    let h = now.getHours(), m = now.getMinutes(), s = now.getSeconds();
    h = h < 10 ? "0" + h : h;
    m = m < 10 ? "0" + m : m;
    s = s < 10 ? "0" + s : s;
    if (clockElem) clockElem.textContent = `${h}:${m}:${s}`;

    // تاريخ بصيغة مختصرة
    if (dateElem) {
      const opts = { weekday: 'short', year: 'numeric', month: 'short', day: '2-digit' };
      dateElem.textContent = now.toLocaleDateString('en-GB', opts);
    }
  }
  updateClock();
  setInterval(updateClock, 1000);

  // ==========================
  // Chart.js – إحصائية الأسبوع
  // ==========================
  if (chartDataElement && chartCanvas) {
    try {
      const chartData = JSON.parse(chartDataElement.textContent);

      // توليد ألوان باستيل بناءً على عدد الأيام
      const pastelColors = ['#A3C8F7','#B8E0D2','#FFD6E0','#FFF5BA','#E2F0CB','#FFBCBC','#C1BFFF'];
      const barColors = chartData.labels.map((_, i) => pastelColors[i % pastelColors.length]);

      const ctx = chartCanvas.getContext("2d");
      new Chart(ctx, {
        type: "bar",
        data: {
          labels: chartData.labels,
          datasets: [{
            label: "Appointments",
            data: chartData.data,
            backgroundColor: barColors,
            borderRadius: 14,
            borderSkipped: false,
            maxBarThickness: 56,
            minBarLength: 4  // يعرض بار صغير حتى لو القيمة صفر
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: ctx => ` ${ctx.parsed.y} appointments`
              }
            }
          },
          scales: {
            x: { grid: { display: false } },
            y: {
              beginAtZero: true,
              grid: { color: "#e6f2fa" },
              ticks: { stepSize: 1 }
            }
          },
          animation: {
            duration: 1200,
            easing: "easeOutQuart"
          }
        }
      });
    } catch (err) {
      console.error("Error initializing Weekly Chart:", err, chartDataElement.textContent);
    }
  }
});
