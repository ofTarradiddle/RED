import React, { useEffect, useRef } from 'react'
import { PieChart, Building2, Globe, TrendingUp } from 'lucide-react'
import { holdingsData, getSectorAllocation, getCountryAllocation } from '@/lib/dataLoader'

const Holdings = () => {
  const pieChartRef = useRef<HTMLCanvasElement>(null)
  
  // Get real data from dataLoader
  const topHoldings = holdingsData.slice(0, 10).map(holding => ({
    name: holding.name,
    ticker: holding.ticker,
    weight: `${holding.weight.toFixed(1)}%`,
    sector: holding.sector
  }))
  
  const sectorAllocation = getSectorAllocation(holdingsData).map(sector => ({
    sector: sector.sector,
    weight: `${sector.weight.toFixed(1)}%`,
    color: getSectorColor(sector.sector)
  }))
  
  const countryAllocation = getCountryAllocation(holdingsData)
  
  // Get portfolio statistics
  const totalHoldings = holdingsData.length
  const uniqueCountries = new Set(holdingsData.map(h => h.country).filter(Boolean)).size
  const largestPosition = Math.max(...holdingsData.map(h => h.weight))
  const uniqueSectors = new Set(holdingsData.map(h => h.sector)).size
  
  function getSectorColor(sector: string): string {
    const colors = {
      'Technology': 'bg-primary-500',
      'Consumer Discretionary': 'bg-accent-500',
      'Healthcare': 'bg-secondary-500',
      'Communication Services': 'bg-green-500',
      'Financial Services': 'bg-purple-500',
      'Other': 'bg-gray-500'
    }
    return colors[sector as keyof typeof colors] || 'bg-gray-500'
  }

  // Initialize pie chart
  useEffect(() => {
    const initPieChart = async () => {
      if (typeof window !== 'undefined' && window.Chart && pieChartRef.current) {
        const Chart = window.Chart
        const ctx = pieChartRef.current.getContext('2d')
        
        if (ctx) {
          const sectorData = getSectorAllocation(holdingsData)
          const colors = [
            '#dc2626', // red-600
            '#2563eb', // blue-600
            '#059669', // green-600
            '#7c3aed', // violet-600
            '#ea580c', // orange-600
            '#6b7280'  // gray-500
          ]
          
          new Chart(ctx, {
            type: 'doughnut',
            data: {
              labels: sectorData.map(s => s.sector),
              datasets: [{
                data: sectorData.map(s => s.weight),
                backgroundColor: colors.slice(0, sectorData.length),
                borderWidth: 2,
                borderColor: '#ffffff'
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  position: 'bottom',
                  labels: {
                    padding: 20,
                    usePointStyle: true
                  }
                }
              }
            }
          })
        }
      }
    }

    initPieChart()
  }, [])

  return (
    <section id="holdings" className="py-20 bg-secondary-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-secondary-900 mb-6">
            Portfolio Holdings
          </h2>
          <p className="text-xl text-secondary-600 max-w-3xl mx-auto">
            A concentrated portfolio of innovative companies across technology, healthcare, 
            and other transformative sectors.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 mb-16">
          {/* Top Holdings */}
          <div>
            <h3 className="text-2xl font-bold text-secondary-900 mb-6">Top Holdings</h3>
            <div className="bg-white rounded-xl border border-secondary-200 overflow-hidden">
              <div className="p-6 border-b border-secondary-200">
                <div className="grid grid-cols-4 gap-4 text-sm font-medium text-secondary-600">
                  <div>Company</div>
                  <div>Ticker</div>
                  <div>Weight</div>
                  <div>Sector</div>
                </div>
              </div>
              <div className="divide-y divide-secondary-100">
                {topHoldings.map((holding, index) => (
                  <div key={index} className="p-6 hover:bg-secondary-50 transition-colors">
                    <div className="grid grid-cols-4 gap-4 items-center">
                      <div>
                        <div className="font-medium text-secondary-900">{holding.name}</div>
                      </div>
                      <div className="font-mono text-secondary-600">{holding.ticker}</div>
                      <div className="font-semibold gradient-text">{holding.weight}</div>
                      <div className="text-sm text-secondary-600">{holding.sector}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <p className="text-sm text-secondary-500 mt-4">
              Holdings are subject to change and may not be representative of current or future investments.
            </p>
          </div>

          {/* Sector Allocation */}
          <div>
            <h3 className="text-2xl font-bold text-secondary-900 mb-6">Sector Allocation</h3>
            <div className="bg-white p-6 rounded-xl border border-secondary-200">
              <div className="space-y-4">
                {sectorAllocation.map((sector, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className={`w-4 h-4 rounded-full ${sector.color}`}></div>
                      <span className="font-medium text-secondary-900">{sector.sector}</span>
                    </div>
                    <span className="font-semibold gradient-text">{sector.weight}</span>
                  </div>
                ))}
              </div>
              
              {/* Sector Allocation Chart */}
              <div className="mt-8 p-6 bg-secondary-50 rounded-lg">
                <div className="h-64">
                  <canvas ref={pieChartRef}></canvas>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Portfolio Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-white p-6 rounded-xl border border-secondary-200 text-center card-hover">
            <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center mx-auto mb-4">
              <Building2 className="h-6 w-6 text-white" />
            </div>
            <div className="text-2xl font-bold gradient-text mb-2">{totalHoldings}</div>
            <div className="text-secondary-600">Total Holdings</div>
          </div>
          
          <div className="bg-white p-6 rounded-xl border border-secondary-200 text-center card-hover">
            <div className="w-12 h-12 bg-gradient-to-br from-accent-500 to-primary-500 rounded-lg flex items-center justify-center mx-auto mb-4">
              <Globe className="h-6 w-6 text-white" />
            </div>
            <div className="text-2xl font-bold gradient-text mb-2">{uniqueCountries}</div>
            <div className="text-secondary-600">Countries</div>
          </div>
          
          <div className="bg-white p-6 rounded-xl border border-secondary-200 text-center card-hover">
            <div className="w-12 h-12 bg-gradient-to-br from-secondary-500 to-accent-500 rounded-lg flex items-center justify-center mx-auto mb-4">
              <TrendingUp className="h-6 w-6 text-white" />
            </div>
            <div className="text-2xl font-bold gradient-text mb-2">{largestPosition.toFixed(1)}%</div>
            <div className="text-secondary-600">Largest Position</div>
          </div>
          
          <div className="bg-white p-6 rounded-xl border border-secondary-200 text-center card-hover">
            <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-lg flex items-center justify-center mx-auto mb-4">
              <PieChart className="h-6 w-6 text-white" />
            </div>
            <div className="text-2xl font-bold gradient-text mb-2">{uniqueSectors}</div>
            <div className="text-secondary-600">Sectors</div>
          </div>
        </div>

        {/* Important Notice */}
        <div className="mt-12 p-6 bg-gradient-to-br from-secondary-50 to-accent-50 rounded-xl">
          <h4 className="font-semibold text-secondary-900 mb-4">Important Information</h4>
          <p className="text-sm text-secondary-600 mb-4">
            Holdings and allocations are subject to change and may not be representative of current or future investments. 
            The information provided is for informational purposes only and should not be considered as investment advice.
          </p>
          <p className="text-sm text-secondary-600">
            For the most current holdings information, please contact Diamond & Diamond (D&D) or refer to the most recent 
            fund fact sheet and prospectus.
          </p>
        </div>
      </div>
    </section>
  )
}

export default Holdings 