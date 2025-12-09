document.addEventListener('DOMContentLoaded', function() {
    console.log("SerendivWatcher Premium Dashboard Loaded");
    
    // Initialize all components
    if (typeof dashboardData !== 'undefined') {
        initSectorChart(dashboardData.national_indicators?.top_sectors || []);
        initThemeToggle();
        initAutoRefresh();
    }
});

let currentChart = null;
let currentChartType = 'bar';

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
                    borderRadius: 8,
                    barThickness: 24,
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
                    backgroundColor: 'rgba(99, 102, 241, 0.2)',
                    borderColor: 'rgb(99, 102, 241)',
                    borderWidth: 2,
                    pointBackgroundColor: 'rgb(99, 102, 241)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgb(99, 102, 241)'
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
    gradient.addColorStop(0, 'rgba(99, 102, 241, 0.8)');
    gradient.addColorStop(1, 'rgba(139, 92, 246, 0.4)');
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
                    padding: 15,
                    font: { size: 11, family: "'Inter', sans-serif" },
                    usePointStyle: true
                }
            },
            tooltip: {
                backgroundColor: '#1e293b',
                padding: 16,
                titleFont: { size: 14, weight: '600' },
                bodyFont: { size: 13 },
                cornerRadius: 10,
                displayColors: false,
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
            }
        }
    };
    
    if (type === 'bar') {
        baseOptions.scales = {
            y: {
                beginAtZero: true,
                grid: { color: '#f1f5f9', drawBorder: false },
                ticks: {
                    font: { size: 11, family: "'Inter', sans-serif" },
                    color: '#64748b'
                }
            },
            x: {
                grid: { display: false },
                ticks: {
                    font: { size: 11, family: "'Inter', sans-serif" },
                    color: '#64748b'
                }
            }
        };
    }
    
    if (type === 'radar') {
        baseOptions.scales = {
            r: {
                angleLines: { color: '#e2e8f0' },
                grid: { color: '#f1f5f9' },
                pointLabels: {
                    font: { size: 11, family: "'Inter', sans-serif" },
                    color: '#64748b'
                },
                ticks: { display: false }
            }
        };
    }
    
    return baseOptions;
}

// Theme Toggle
function initThemeToggle() {
    const toggle = document.getElementById('themeToggle');
    if (!toggle) return;
    
    toggle.addEventListener('click', function() {
        document.body.classList.toggle('dark-mode');
        const icon = this.querySelector('i');
        icon.classList.toggle('fa-moon');
        icon.classList.toggle('fa-sun');
    });
}

// Auto-refresh timestamp
function initAutoRefresh() {
    const updateElement = document.getElementById('lastUpdated');
    if (!updateElement) return;
    
    setInterval(() => {
        const now = new Date().toLocaleString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
        updateElement.textContent = now;
    }, 60000); // Update every minute
}

