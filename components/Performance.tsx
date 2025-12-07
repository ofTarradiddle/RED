import React, { useEffect, useRef } from 'react'
import { TrendingUp, Calendar, DollarSign, BarChart3 } from 'lucide-react'
import { performanceData, calculatePerformanceMetrics, calculateRiskMetrics, formatChartData, formatPremiumDiscountData } from '@/lib/dataLoader'

const Performance = () => {
  const chartRef = useRef<HTMLCanvasElement>(null)
  const premiumChartRef = useRef<HTMLCanvasElement>(null)
  
  // Calculate real performance metrics from data
  const metrics = calculatePerformanceMetrics(performanceData)
  const riskMetrics = calculateRiskMetrics(performanceData)
  
  const performanceDataFormatted = {
    ytd: `${metrics.ytd > 0 ? '+' : ''}${metrics.ytd.toFixed(1)}%`,
    oneMonth: `${metrics.oneMonth > 0 ? '+' : ''}${metrics.oneMonth.toFixed(1)}%`,
    threeMonth: `${metrics.threeMonth > 0 ? '+' : ''}${metrics.threeMonth.toFixed(1)}%`,
    sixMonth: `${metrics.sixMonth > 0 ? '+' : ''}${metrics.sixMonth.toFixed(1)}%`,
    oneYear: `${metrics.oneYear > 0 ? '+' : ''}${metrics.oneYear.toFixed(1)}%`,
    sinceInception: `${metrics.sinceInception > 0 ? '+' : ''}${metrics.sinceInception.toFixed(1)}%`
  }

  const riskMetricsFormatted = [
    { label: 'Beta', value: riskMetrics.beta.toFixed(2), description: 'vs Morningstar US Market Index' },
    { label: 'Sharpe Ratio', value: riskMetrics.sharpeRatio.toFixed(2), description: 'Risk-adjusted return' },
    { label: 'Max Drawdown', value: `${riskMetrics.maxDrawdown.toFixed(1)}%`, description: 'Historical maximum loss' },
    { label: 'Volatility', value: `${riskMetrics.volatility.toFixed(1)}%`, description: 'Annualized standard deviation' }
  ]

  // Initialize charts
  useEffect(() => {
    const initCharts = async () => {
      if (typeof window !== 'undefined' && window.Chart) {
        const Chart = window.Chart
        
        // Performance Chart
        if (chartRef.current) {
          const ctx = chartRef.current.getContext('2d')
          if (ctx) {
            new Chart(ctx, {
              type: 'line',
              data: formatChartData(performanceData),
              options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: 'top',
                  },
                  title: {
                    display: false,
                  }
                },
                scales: {
                  y: {
                    beginAtZero: false,
                    grid: {
                      color: 'rgba(0, 0, 0, 0.1)',
                    }
                  },
                  x: {
                    grid: {
                      color: 'rgba(0, 0, 0, 0.1)',
                    }
                  }
                },
                elements: {
                  point: {
                    radius: 0,
                    hoverRadius: 6
                  }
                }
              }
            })
          }
        }

        // Premium/Discount Chart
        if (premiumChartRef.current) {
          const ctx = premiumChartRef.current.getContext('2d')
          if (ctx) {
            new Chart(ctx, {
              type: 'line',
              data: formatPremiumDiscountData(performanceData),
              options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: 'top',
                  },
                  title: {
                    display: false,
                  }
                },
                scales: {
                  y: {
                    beginAtZero: false,
                    grid: {
                      color: 'rgba(0, 0, 0, 0.1)',
                    }
                  },
                  x: {
                    grid: {
                      color: 'rgba(0, 0, 0, 0.1)',
                    }
                  }
                },
                elements: {
                  point: {
                    radius: 0,
                    hoverRadius: 6
                  }
                }
              }
            })
          }
        }
      }
    }

    initCharts()
  }, [])

  return (
    <section id="performance" className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-secondary-900 mb-6">
            Performance
          </h2>
          <p className="text-xl text-secondary-600 max-w-3xl mx-auto">
            Track record of delivering strong returns through innovative investment strategies 
            and active portfolio management.
          </p>
        </div>

        {/* Performance Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-16">
          <div className="bg-gradient-to-br from-primary-50 to-primary-100 p-4 rounded-xl text-center">
            <div className="text-xl font-bold gradient-text mb-1">{performanceDataFormatted.ytd}</div>
            <div className="text-secondary-600 text-xs">YTD</div>
          </div>
          <div className="bg-gradient-to-br from-accent-50 to-accent-100 p-4 rounded-xl text-center">
            <div className="text-xl font-bold gradient-text mb-1">{performanceDataFormatted.oneMonth}</div>
            <div className="text-secondary-600 text-xs">1 Month</div>
          </div>
          <div className="bg-gradient-to-br from-secondary-50 to-secondary-100 p-4 rounded-xl text-center">
            <div className="text-xl font-bold gradient-text mb-1">{performanceDataFormatted.threeMonth}</div>
            <div className="text-secondary-600 text-xs">3 Month</div>
          </div>
          <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-xl text-center">
            <div className="text-xl font-bold gradient-text mb-1">{performanceDataFormatted.sixMonth}</div>
            <div className="text-secondary-600 text-xs">6 Month</div>
          </div>
          <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-xl text-center">
            <div className="text-xl font-bold gradient-text mb-1">{performanceDataFormatted.oneYear}</div>
            <div className="text-secondary-600 text-xs">1 Year</div>
          </div>
          <div className="bg-gradient-to-br from-primary-50 to-accent-100 p-4 rounded-xl text-center">
            <div className="text-xl font-bold gradient-text mb-1">{performanceDataFormatted.sinceInception}</div>
            <div className="text-secondary-600 text-xs">Since Inception</div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          {/* Performance Chart */}
          <div className="bg-secondary-50 p-8 rounded-xl">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-semibold text-secondary-900">Performance Chart</h3>
              <BarChart3 className="h-6 w-6 text-secondary-400" />
            </div>
            <div className="bg-white p-6 rounded-lg border border-secondary-200">
              <div className="h-64">
                <canvas ref={chartRef}></canvas>
              </div>
            </div>
            <p className="text-sm text-secondary-500 mt-4">
              * Past performance does not guarantee future results. Investment returns and principal value will fluctuate.
            </p>
          </div>

          {/* Premium/Discount Chart */}
          <div className="bg-secondary-50 p-8 rounded-xl">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-semibold text-secondary-900">Premium/Discount</h3>
              <TrendingUp className="h-6 w-6 text-secondary-400" />
            </div>
            <div className="bg-white p-6 rounded-lg border border-secondary-200">
              <div className="h-64">
                <canvas ref={premiumChartRef}></canvas>
              </div>
            </div>
            <p className="text-sm text-secondary-500 mt-4">
              * Premium/Discount shows the difference between ETF market price and NAV.
            </p>
          </div>

        </div>

        {/* Risk Metrics */}
        <div className="mt-12">
          <h3 className="text-2xl font-semibold text-secondary-900 mb-8 text-center">Risk & Volatility Metrics</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {riskMetricsFormatted.map((metric, index) => (
              <div key={index} className="bg-secondary-50 p-6 rounded-xl text-center">
                <div className="text-2xl font-bold gradient-text mb-2">{metric.value}</div>
                <div className="font-medium text-secondary-900 mb-1">{metric.label}</div>
                <div className="text-sm text-secondary-600">{metric.description}</div>
              </div>
            ))}
          </div>

            <div className="mt-8 bg-gradient-to-br from-secondary-50 to-accent-50 p-6 rounded-xl">
              <h4 className="font-semibold text-secondary-900 mb-4">Important Disclosures</h4>
              <ul className="text-sm text-secondary-600 space-y-2">
                <li>• Performance data is historical and does not guarantee future results</li>
                <li>• Investment involves risk, including possible loss of principal</li>
                <li>• ETF shares trade at market price and may trade at a premium or discount to NAV</li>
                <li>• Diversification does not ensure a profit or protect against loss</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Performance Disclaimer */}
        <div className="mt-12 p-6 bg-secondary-50 rounded-xl">
          <div className="flex items-start space-x-4">
            <Calendar className="h-6 w-6 text-secondary-500 mt-1 flex-shrink-0" />
            <div>
              <h4 className="font-semibold text-secondary-900 mb-2">Performance Information</h4>
              <p className="text-sm text-secondary-600">
                Performance data shown represents past performance and is not a guarantee of future results. 
                Current performance may be lower or higher than the performance data quoted. The investment 
                return and principal value of an investment will fluctuate so that an investor's shares, 
                when redeemed, may be worth more or less than their original cost. For performance data 
                current to the most recent month-end, please contact Diamond & Diamond (D&D).
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default Performance 