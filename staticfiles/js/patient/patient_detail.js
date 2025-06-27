document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const predictionBadge = document.getElementById('predictionBadge');
    const modal = document.getElementById('predictionModal');
    const addNoteModal = document.getElementById('addNoteModal');
    const historyModal = document.getElementById('historyModal');
    const closeBtns = document.querySelectorAll('.close');
    const generateReportBtn = document.getElementById('generateReportBtn');
    const addNoteBtn = document.getElementById('addNoteBtn');
    const viewHistoryBtn = document.getElementById('viewHistoryBtn');
    const toast = document.getElementById('reportToast');
    const cancelNoteBtn = document.getElementById('cancelNoteBtn');
    const clinicalNoteForm = document.getElementById('clinicalNoteForm');
    
    // Initialize Health Metrics Chart
    const initHealthChart = () => {
        const ctx = document.getElementById('healthMetricsChart');
        if (!ctx) return;
        
        new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Glucose (mg/dL)',
                    data: [160, 152, 145, 142, 138, 136],
                    borderColor: '#4e73df',
                    backgroundColor: 'rgba(78, 115, 223, 0.1)',
                    tension: 0.3,
                    fill: true
                }, {
                    label: 'HbA1c (%)',
                    data: [8.2, 7.9, 7.7, 7.5, 7.3, 7.1],
                    borderColor: '#17bf7a',
                    backgroundColor: 'rgba(23, 191, 122, 0.1)',
                    tension: 0.3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    };
    
    // Show modal function
    const showModal = (modalElement) => {
        modalElement.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    };
    
    // Hide modal function
    const hideModal = (modalElement) => {
        modalElement.style.display = 'none';
        document.body.style.overflow = 'auto';
    };
    
    // Show toast notification
    const showToast = () => {
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    };
    
    // Event Listeners
    if (predictionBadge) {
        predictionBadge.addEventListener('click', () => showModal(modal));
    }
    
    closeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (modal.style.display === 'flex') hideModal(modal);
            if (addNoteModal.style.display === 'flex') hideModal(addNoteModal);
            if (historyModal.style.display === 'flex') hideModal(historyModal);
        });
    });
    
    window.addEventListener('click', (e) => {
        if (e.target === modal) hideModal(modal);
        if (e.target === addNoteModal) hideModal(addNoteModal);
        if (e.target === historyModal) hideModal(historyModal);
    });
    
    // Card hover animations
    const cards = document.querySelectorAll('.glow-hover');
    cards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-5px)';
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
        });
    });
    
    // Generate Report
    if (generateReportBtn) {
        generateReportBtn.addEventListener('click', () => {
            // Simulate report generation
            const originalHTML = generateReportBtn.innerHTML;
            generateReportBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
            generateReportBtn.disabled = true;
            
            setTimeout(() => {
                generateReportBtn.innerHTML = originalHTML;
                generateReportBtn.disabled = false;
                showToast();
            }, 2000);
        });
    }
    
    // Add Note
    if (addNoteBtn) {
        addNoteBtn.addEventListener('click', () => showModal(addNoteModal));
    }
    
    // View History
    if (viewHistoryBtn) {
        viewHistoryBtn.addEventListener('click', () => showModal(historyModal));
    }
    
    // Cancel Note
    if (cancelNoteBtn) {
        cancelNoteBtn.addEventListener('click', () => hideModal(addNoteModal));
    }
    
    // Form submission
    if (clinicalNoteForm) {
        clinicalNoteForm.addEventListener('submit', (e) => {
            e.preventDefault();
            // Form validation
            const noteContent = document.getElementById('noteContent').value;
            if (!noteContent.trim()) {
                alert('Please enter note content');
                return;
            }
            
            // Here you would handle the form submission to the server
            hideModal(addNoteModal);
            
            // Show success message
            alert('Clinical note added successfully!');
            clinicalNoteForm.reset();
        });
    }
    
    // Initialize components
    initHealthChart();
    
    // Responsive adjustments
    function handleResponsive() {
        if (window.innerWidth < 768) {
            document.querySelector('.pd-actions')?.classList.add('mobile-view');
        } else {
            document.querySelector('.pd-actions')?.classList.remove('mobile-view');
        }
    }
    
    window.addEventListener('resize', handleResponsive);
    handleResponsive();
});