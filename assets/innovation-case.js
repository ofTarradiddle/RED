
        // Initialize Lucide icons
        lucide.createIcons();

        // Cinematic scroll reveal functionality
        function handleCinematicReveal() {
            const elements = document.querySelectorAll('.dramatic-reveal, .slide-in-left, .slide-in-right, .zoom-in, .flip-in');
            
            elements.forEach(element => {
                const elementTop = element.getBoundingClientRect().top;
                const elementVisible = 200;
                
                if (elementTop < window.innerHeight - elementVisible) {
                    element.classList.add('visible');
                }
            });
        }

        // Performance Story Chart
        function createPerformanceStoryChart() {
            const ctx = document.getElementById('performanceStoryChart').getContext('2d');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Innovation', 'Value', 'Momentum', 'Quality'],
                    datasets: [{
                        label: 'Annual Return (%)',
                        data: [15.2, 8.7, 12.1, 9.3],
                        backgroundColor: [
                            'rgba(139, 0, 0, 0.9)',
                            'rgba(255, 255, 255, 0.2)',
                            'rgba(255, 255, 255, 0.2)',
                            'rgba(255, 255, 255, 0.2)'
                        ],
                        borderColor: [
                            '#8b0000',
                            'rgba(255, 255, 255, 0.5)',
                            'rgba(255, 255, 255, 0.5)',
                            'rgba(255, 255, 255, 0.5)'
                        ],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: 'white',
                                font: {
                                    size: 14,
                                    weight: 'bold'
                                }
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                color: 'white',
                                font: {
                                    size: 14,
                                    weight: 'bold'
                                }
                            }
                        }
                    }
                }
            });
        }

        // Innovation Story Chart
        function createInnovationStoryChart() {
            const ctx = document.getElementById('innovationStoryChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['2019', '2020', '2021', '2022', '2023', '2024'],
                    datasets: [{
                        label: 'Innovation Factor',
                        data: [100, 115, 135, 158, 182, 210],
                        borderColor: '#8b0000',
                        backgroundColor: 'rgba(139, 0, 0, 0.2)',
                        borderWidth: 4,
                        fill: true,
                        tension: 0.4
                    }, {
                        label: 'Conceptual comparison',
                        data: [100, 112, 128, 142, 156, 170],
                        borderColor: '#6b7280',
                        backgroundColor: 'rgba(107, 114, 128, 0.1)',
                        borderWidth: 3,
                        fill: false,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                color: 'white',
                                font: {
                                    size: 14,
                                    weight: 'bold'
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: 'white',
                                font: {
                                    size: 14,
                                    weight: 'bold'
                                }
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                color: 'white',
                                font: {
                                    size: 14,
                                    weight: 'bold'
                                }
                            }
                        }
                    }
                }
            });
        }

        // Initialize everything when page loads
        document.addEventListener('DOMContentLoaded', function() {
            createInnovationStoryChart();
            createPerformanceStoryChart();
            
            // Initial cinematic reveal check
            handleCinematicReveal();
            
            // Add scroll event listener
            window.addEventListener('scroll', handleCinematicReveal);
        });
    
