// ====== Clinic Queue System ======
const queueContainer = document.getElementById('queue-container');
const viewControls = document.querySelectorAll('.view-controls span');
const searchInput = document.getElementById('search-input');
const notification = document.getElementById('notification');
const currentTime = document.getElementById('current-time');
const updateTimeEl = document.getElementById('update-time');
const doctorCount = document.getElementById('doctor-count');

// Doctor and patient data
let doctors = [];
let filteredDoctors = [];
let currentDepartment = 'all';

// Medical departments
const departments = {
    'cardiology': 'Cardiology',
    'neurology': 'Neurology',
    'orthopedics': 'Orthopedics',
    'pediatrics': 'Pediatrics',
    'general': 'General Practice'
};

// Medical cases
const medicalCases = {
    'normal': 'Regular Checkup',
    'urgent': 'Urgent Case',
    'followup': 'Follow-up Visit'
};

// Initialize function
function init() {
    loadDoctors();
    setupEventListeners();
    updateClock();
    setInterval(updateClock, 1000);
    setInterval(loadDoctors, 15000); // Refresh every 15 seconds
    
    // Show initial notification
    setTimeout(() => showNotification("System Ready", "Clinic queue system initialized"), 1500);
}

// Load doctor and patient data from API
async function loadDoctors() {
    try {
        const response = await fetch(window.QUEUE_API);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        
        const data = await response.json();
        if (data.queues) {
            doctors = data.queues;
            
            // Update doctor count
            doctorCount.textContent = doctors.length;
            
            // Apply current filters
            filterDoctors();
            
            // Update last updated time
            const now = new Date();
            updateTimeEl.textContent = now.toLocaleTimeString('en-US', { hour: 'numeric', minute: 'numeric' });
        }
    } catch (error) {
        console.error('Error fetching queue data:', error);
        showNotification("System Error", "Failed to load queue data. Using cached data.");
    }
}

// Set up event listeners
function setupEventListeners() {
    // View controls
    viewControls.forEach(control => {
        control.addEventListener('click', () => {
            viewControls.forEach(c => c.classList.remove('active'));
            control.classList.add('active');
            currentDepartment = control.dataset.department;
            filterDoctors();
        });
    });
    
    // Search input
    searchInput.addEventListener('input', filterDoctors);
    
    // Control buttons
    document.getElementById('settings-btn').addEventListener('click', () => 
        showNotification("Settings", "System settings panel opened"));
    
    document.getElementById('reports-btn').addEventListener('click', () => 
        showNotification("Reports", "Generating system performance reports..."));
    
    document.getElementById('admin-btn').addEventListener('click', () => 
        showNotification("Admin Panel", "Accessed system administration controls"));
}

// Filter doctors based on search and department
function filterDoctors() {
    const searchTerm = searchInput.value.toLowerCase();
    
    filteredDoctors = doctors.filter(doctor => {
        const matchesDepartment = currentDepartment === 'all' || 
                                doctor.department === currentDepartment;
        const matchesSearch = !searchTerm || 
                            doctor.doctor_name.toLowerCase().includes(searchTerm) ||
                            doctor.doctor_specialty.toLowerCase().includes(searchTerm);
        return matchesDepartment && matchesSearch;
    });
    
    renderDoctors();
}

// Display doctors in the UI
function renderDoctors() {
    queueContainer.innerHTML = '';
    
    if (filteredDoctors.length === 0) {
        queueContainer.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-user-md"></i>
                <h2>No Doctors Found</h2>
                <p>Please adjust your search or filter criteria</p>
            </div>`;
        return;
    }
    
    filteredDoctors.forEach(doctor => {
        const card = createDoctorCard(doctor);
        queueContainer.appendChild(card);
    });
}

// Create doctor card
function createDoctorCard(doctor) {
    const card = document.createElement('div');
    card.className = 'doctor-card';
    card.dataset.id = doctor.doctor_id;
    card.dataset.department = doctor.department;
    
    // Determine doctor status
    let statusClass = '', statusText = '';
    switch (doctor.status) {
        case 'available': 
            statusClass = 'status-available'; 
            statusText = 'Available'; 
            break;
        case 'in-session': 
            statusClass = 'status-in-session'; 
            statusText = 'In Session'; 
            break;
        case 'on-break': 
            statusClass = 'status-on-break'; 
            statusText = 'On Break'; 
            break;
        default: 
            statusClass = 'status-available'; 
            statusText = 'Available';
    }
    
    // Create card content
    card.innerHTML = `
        <div class="call-to-action" data-id="${doctor.doctor_id}">
            <i class="fas fa-bell"></i>
        </div>
        <div class="doctor-header">
            <div class="doctor-icon">
                <i class="fas fa-user-md"></i>
            </div>
            <div class="doctor-info">
                <div class="doctor-name">${doctor.doctor_name}</div>
                <div class="doctor-specialty">${doctor.doctor_specialty}</div>
            </div>
            <div class="doctor-status ${statusClass}">${statusText}</div>
        </div>
        <div class="queue-content">
            <div class="current-label">Currently Examining</div>
            ${doctor.currentPatient ? `
            <div class="patient-display">
                <div class="patient-number">${doctor.currentPatient.number || ''}</div>
                <div class="patient-info">
                    <div class="patient-name">${doctor.currentPatient.name || ''}</div>
                    <div class="patient-meta">
                        <span>${doctor.currentPatient.case ? medicalCases[doctor.currentPatient.case] : ''}</span>
                        <span><i class="fas fa-clock"></i> ${doctor.currentPatient.time || ''}</span>
                    </div>
                </div>
            </div>
            ` : `
            <div class="empty-state">
                <i class="fas fa-user-injured"></i>
                <p>No current patient</p>
            </div>
            `}
            <div class="waiting-info">
                <div class="waiting-item">
                    <div class="waiting-count">${doctor.waiting ? doctor.waiting.length : 0}</div>
                    <div class="waiting-label">Waiting</div>
                </div>
                <div class="waiting-item">
                    <div class="waiting-count">${doctor.avgTime || 0}</div>
                    <div class="waiting-label">Avg. Wait Time</div>
                </div>
            </div>
        </div>
    `;
    
    // Add event for call button
    if (doctor.currentPatient) {
        card.querySelector('.call-to-action').addEventListener('click', () => callNextPatient(doctor.doctor_id));
    }
    return card;
}

// Call next patient
async function callNextPatient(doctorId) {
    try {
        const url = window.CALL_NEXT_API.replace('0', doctorId);
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.CSRF_TOKEN
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to call next patient');
        }
        
        const data = await response.json();
        if (data.success) {
            showNotification("Patient Called", `Next patient called for doctor ${doctorId}`);
            // Refresh data after successful call
            loadDoctors();
        }
    } catch (error) {
        console.error('Error calling next patient:', error);
        showNotification("System Error", "Failed to call next patient");
    }
}

// Update clock
function updateClock() {
    const now = new Date();
    currentTime.textContent = now.toLocaleTimeString('en-US');
}

// Show notification
function showNotification(title, message) {
    notification.querySelector('h3').textContent = title;
    notification.querySelector('p').textContent = message;
    notification.classList.add('show');
    
    setTimeout(() => notification.classList.remove('show'), 5000);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', init);