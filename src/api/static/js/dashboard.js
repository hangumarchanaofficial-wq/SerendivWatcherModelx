document.addEventListener('DOMContentLoaded', function() {
    console.log("SerendivWatcher Premium Dark Dashboard Loaded");
    
    // Initialize components
    if (typeof dashboardData !== 'undefined') {
        initSectorChart(dashboardData.national_indicators?.top_sectors || []);
        initAutoRefresh();
        initAnimations();
    }
});

let currentChart = null;
let currentChartType = 'bar';

// ==========================================
// SECTOR CHART WITH DARK THEME
// ==========================================
function initSectorChart(sectors) {
    const ctx = document.getElementById('sectorChart')?.getContext('2d');
    if (!ctx) return;
    
    const topSectors = sectors.slice(0, 8);
    const labels = topSectors.map(s => s.sector.charAt(0).toUpperCase() + s.sector.slice(1));
    const dataPoints = topSectors.map(s => s.count);
    
    const chartConfig = {
        bar: {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Article Volume',
                    data: dataPoints,
                    backgroundColor: createGradient(ctx),
                    borderRadius: 10,
                    barThickness: 30,
                }]
            },
            options: getChartOptions('bar')
        },
        radar: {
            type: 'radar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Sector Activity',
                    data: dataPoints,
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    borderColor: 'rgb(102, 126, 234)',
                    borderWidth: 3,
                    pointBackgroundColor: 'rgb(102, 126, 234)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgb(102, 126, 234)',
                    pointRadius: 5,
                    pointHoverRadius: 7
                }]
            },
            options: getChartOptions('radar')
        },
        doughnut: {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dataPoints,
                    backgroundColor: [
                        '#6366f1', '#8b5cf6', '#ec4899', '#f43f5e',
                        '#f97316', '#f59e0b', '#10b981', '#14b8a6'
                    ],
                    borderWidth: 0,
                    hoverOffset: 10
                }]
            },
            options: getChartOptions('doughnut')
        }
    };
    
    currentChart = new Chart(ctx, chartConfig[currentChartType]);
    
    // Chart type switcher
    document.querySelectorAll('[data-chart]').forEach(btn => {
        btn.addEventListener('click', function() {
            const type = this.dataset.chart;
            document.querySelectorAll('[data-chart]').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            currentChart.destroy();
            currentChartType = type;
            currentChart = new Chart(ctx, chartConfig[type]);
        });
    });
}

function createGradient(ctx) {
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(102, 126, 234, 0.9)');
    gradient.addColorStop(1, 'rgba(118, 75, 162, 0.6)');
    return gradient;
}

function getChartOptions(type) {
    const baseOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 1500,
            easing: 'easeInOutQuart'
        },
        plugins: {
            legend: {
                display: type === 'doughnut',
                position: 'bottom',
                labels: {
                    padding: 20,
                    font: { size: 12, family: "'Inter', sans-serif" },
                    color: '#94a3b8',
                    usePointStyle: true
                }
            },
            tooltip: {
                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                padding: 16,
                titleFont: { size: 14, weight: '700' },
                bodyFont: { size: 13 },
                cornerRadius: 12,
                displayColors: type !== 'bar',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                borderWidth: 1
            }
        }
    };
    
    if (type === 'bar') {
        baseOptions.scales = {
            y: {
                beginAtZero: true,
                grid: { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false },
                ticks: {
                    font: { size: 12, family: "'Inter', sans-serif" },
                    color: '#64748b'
                }
            },
            x: {
                grid: { display: false },
                ticks: {
                    font: { size: 12, family: "'Inter', sans-serif" },
                    color: '#64748b'
                }
            }
        };
    }
    
    if (type === 'radar') {
        baseOptions.scales = {
            r: {
                angleLines: { color: 'rgba(255, 255, 255, 0.1)' },
                grid: { color: 'rgba(255, 255, 255, 0.08)' },
                pointLabels: {
                    font: { size: 11, family: "'Inter', sans-serif" },
                    color: '#94a3b8'
                },
                ticks: { 
                    display: false,
                    backdropColor: 'transparent'
                }
            }
        };
    }
    
    return baseOptions;
}

// ==========================================
// AUTO-REFRESH TIMESTAMP
// ==========================================
function initAutoRefresh() {
    const updateElement = document.getElementById('lastUpdated');
    if (!updateElement) return;
    
    function updateTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit'
        });
        updateElement.textContent = `Updated at ${timeString}`;
    }
    
    updateTime();
    setInterval(updateTime, 60000); // Update every minute
}

// ==========================================
// ANIMATIONS ON SCROLL
// ==========================================
function initAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.animation = 'fadeInUp 0.6s ease forwards';
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.card-glass-dark').forEach(card => {
        observer.observe(card);
    });
}

// ==========================================
// REFRESH BUTTON
// ==========================================
document.querySelector('.btn-glass-primary')?.addEventListener('click', function() {
    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
    
    setTimeout(() => {
        location.reload();
    }, 1000);
});
