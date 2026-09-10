document.addEventListener('DOMContentLoaded', async () => {
    try {
        const res = await fetch('/api/relatorios/resumo');
        const data = await res.json();
        
        // Common chart defaults (Dark glassmorphism theme)
        Chart.defaults.color = '#94a3b8'; // var(--text-secondary)
        
        // 1. Revenue Chart (Bar)
        const ctxFaturamento = document.getElementById('faturamentoChart').getContext('2d');
        new Chart(ctxFaturamento, {
            type: 'bar',
            data: {
                labels: ['Paid', 'Pending (Receivables)'],
                datasets: [{
                    label: 'Amount (£)',
                    data: [
                        data.faturamento.Paid !== undefined ? data.faturamento.Paid : data.faturamento.Pago,
                        data.faturamento.Pending !== undefined ? data.faturamento.Pending : data.faturamento.Pendente
                    ],
                    backgroundColor: [
                        'rgba(16, 185, 129, 0.8)', // Green (Success)
                        'rgba(245, 158, 11, 0.8)'  // Amber (Warning)
                    ],
                    borderColor: [
                        '#10b981',
                        '#f59e0b'
                    ],
                    borderWidth: 1,
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(context.parsed.y);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: {
                            callback: function(value) {
                                return '£' + value;
                            }
                        }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });

        // 2. Fleet Status Chart (Doughnut)
        const ctxFrota = document.getElementById('frotaChart').getContext('2d');
        new Chart(ctxFrota, {
            type: 'doughnut',
            data: {
                labels: ['Available', 'Rented', 'Maintenance'],
                datasets: [{
                    data: [
                        data.frota.Available !== undefined ? data.frota.Available : data.frota.Disponível,
                        data.frota.Rented !== undefined ? data.frota.Rented : data.frota.Alugada,
                        data.frota.Maintenance !== undefined ? data.frota.Maintenance : data.frota.Manutenção
                    ],
                        'rgba(16, 185, 129, 0.85)', // Green - Available
                        'rgba(255, 102, 0, 0.85)',  // FF Motors Orange - Rented
                        'rgba(239, 68, 68, 0.85)'   // Red - Maintenance
                    ],
                    borderColor: 'rgba(12, 14, 20, 1)',
                    borderWidth: 2,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { padding: 20 }
                    }
                },
                cutout: '70%'
            }
        });

    } catch (e) {
        console.error('Error loading reports:', e);
    }
});

