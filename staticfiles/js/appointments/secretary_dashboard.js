// File: static/js/appointments/secretary_dashboard.js

document.addEventListener("DOMContentLoaded", () => {
  // ==========================
  // Cache DOM Elements
  // ==========================
  const clockElem       = document.getElementById("digital-clock");
  const dateElem        = document.getElementById("digital-date");
  const chartDataScript = document.getElementById("chart-data");
  const chartCanvas     = document.getElementById("patientsWeekChart");

  const bell     = document.getElementById("notificationBell");
  const dropdown = document.getElementById("notificationDropdown");
  const list     = document.getElementById("notificationList");
  const countEl  = document.getElementById("notificationCount");

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
      const opts = {
        weekday: "short",
        year:    "numeric",
        month:   "short",
        day:     "2-digit"
      };
      dateElem.textContent = now.toLocaleDateString("en-GB", opts);
    }
  }

  updateClock();
  setInterval(updateClock, 1000);

  // ==========================
  // Chart.js – Weekly Overview
  // ==========================
  if (chartDataScript && chartCanvas) {
    try {
      const chartData = JSON.parse(chartDataScript.textContent);
      const ctx = chartCanvas.getContext("2d");

      new Chart(ctx, {
        type: "bar",
        data: {
          labels: chartData.labels,
          datasets: [{
            label: "Patients",
            data: chartData.data,
            backgroundColor: [
              "rgba(56,182,255,0.7)",
              "rgba(73,211,173,0.7)",
              "rgba(145,124,246,0.7)",
              "rgba(255,214,224,0.7)",
              "rgba(255,245,186,0.7)",
              "rgba(226,240,203,0.7)",
              "rgba(255,188,188,0.7)"
            ],
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
            tooltip: {
              callbacks: {
                label: ctx => ` ${ctx.parsed.y} patients`
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
      console.error("Error initializing weekly chart:", err);
    }
  }

  // ==========================
  // Notification System (FIXED TIMEZONE)
  // ==========================
  if (bell && dropdown && list && countEl) {
    // Toggle dropdown
    bell.addEventListener("click", () => {
      dropdown.classList.toggle("open");
    });

    // Format date to local time
    function formatToLocalTime(utcString) {
      const date = new Date(utcString);
      
      // Format time (HH:MM AM/PM)
      const hours = date.getHours();
      const minutes = date.getMinutes().toString().padStart(2, '0');
      const ampm = hours >= 12 ? 'PM' : 'AM';
      const formattedHours = hours % 12 || 12;
      
      // Format date (Day, DD Month YYYY)
      const dateOptions = { 
        weekday: 'short', 
        day: '2-digit', 
        month: 'short', 
        year: 'numeric' 
      };
      const formattedDate = date.toLocaleDateString('en-GB', dateOptions);
      
      return {
        time: `${formattedHours}:${minutes} ${ampm}`,
        date: formattedDate
      };
    }

    // Fetch and render notifications
    async function fetchNotifications() {
      try {
        // Get API URL and CSRF token from data attributes
        const apiUrl = bell.dataset.notificationUrl;
        const csrfToken = bell.dataset.csrfToken;
        
        if (!apiUrl || !csrfToken) {
          console.error("Notification API URL or CSRF token missing");
          return;
        }

        const resp = await fetch(apiUrl, {
          headers: { "X-CSRFToken": csrfToken }
        });
        
        if (!resp.ok) throw new Error("Failed to fetch notifications");
        
        const data = await resp.json();
        list.innerHTML = "";

        const requests = data.booking_requests || [];
        
        if (requests.length === 0) {
          list.innerHTML = '<div class="no-notifications">No new booking requests.</div>';
          countEl.textContent = "0";
          return;
        }

        countEl.textContent = requests.length.toString();
        
        requests.forEach(req => {
          const item = document.createElement("div");
          item.className = "notification-list-item";
          
          // Convert UTC time to local time
          const localTime = formatToLocalTime(req.requested_time);
          
          item.innerHTML = `
            <div class="notification-header">
              <strong>New Booking Request</strong>
              <small>${localTime.date} at ${localTime.time}</small>
            </div>
            <div class="notification-details">
              <span>Patient:</span> ${req.full_name}<br>
              <span>Doctor:</span> Dr. ${req.requested_doctor}
            </div>
          `;
          
          list.appendChild(item);
        });
      } catch (error) {
        console.error("Error fetching notifications:", error);
        list.innerHTML = '<div class="no-notifications">Error loading notifications</div>';
      }
    }

    // Initial fetch
    fetchNotifications();
    
    // Faster polling (every 3 seconds)
    setInterval(fetchNotifications, 3000);
  }

  // ==========================
  // Call Next Patient
  // ==========================
  document.querySelectorAll(".call-next-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const url = btn.dataset.url;
      const csrfToken = btn.dataset.csrfToken;
      
      if (!csrfToken) {
        console.error("CSRF token missing for call next patient");
        alert("Security token missing. Please refresh the page.");
        return;
      }

      try {
        const resp = await fetch(url, {
          method: "POST",
          headers: {
            "X-CSRFToken": csrfToken,
            "Content-Type": "application/json"
          }
        });
        if (!resp.ok) throw new Error("Failed to call next patient");
        location.reload();
      } catch (err) {
        console.error("Error calling next patient:", err);
        alert("Failed to call next patient. Please try again.");
      }
    });
  });
});