import React from 'react'
import { PieChart, Building2, Globe, TrendingUp } from 'lucide-react'

const Holdings = () => {
  const topHoldings = [
    { name: 'NVIDIA Corporation', ticker: 'NVDA', weight: '8.5%', sector: 'Technology' },
    { name: 'Microsoft Corporation', ticker: 'MSFT', weight: '7.2%', sector: 'Technology' },
    { name: 'Tesla, Inc.', ticker: 'TSLA', weight: '6.8%', sector: 'Consumer Discretionary' },
    { name: 'Amazon.com, Inc.', ticker: 'AMZN', weight: '6.1%', sector: 'Consumer Discretionary' },
    { name: 'Alphabet Inc.', ticker: 'GOOGL', weight: '5.9%', sector: 'Technology' },
    { name: 'Apple Inc.', ticker: 'AAPL', weight: '5.4%', sector: 'Technology' },
    { name: 'Meta Platforms, Inc.', ticker: 'META', weight: '4.8%', sector: 'Technology' },
    { name: 'Netflix, Inc.', ticker: 'NFLX', weight: '4.2%', sector: 'Communication Services' },
    { name: 'Salesforce, Inc.', ticker: 'CRM', weight: '3.9%', sector: 'Technology' },
    { name: 'Adobe Inc.', ticker: 'ADBE', weight: '3.6%', sector: 'Technology' }
  ]

  const sectorAllocation = [
    { sector: 'Technology', weight: '45.2%', color: 'bg-primary-500' },
    { sector: 'Consumer Discretionary', weight: '18.7%', color: 'bg-accent-500' },
    { sector: 'Healthcare', weight: '12.3%', color: 'bg-secondary-500' },
    { sector: 'Communication Services', weight: '8.9%', color: 'bg-green-500' },
    { sector: 'Financial Services', weight: '6.8%', color: 'bg-purple-500' },
    { sector: 'Other', weight: '8.1%', color: 'bg-gray-500' }
  ]

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
              
              {/* Chart Placeholder */}
              <div className="mt-8 p-6 bg-secondary-50 rounded-lg">
                <div className="flex items-center justify-center h-48">
                  <div className="text-center">
                    <PieChart className="h-12 w-12 text-secondary-400 mx-auto mb-4" />
                    <p className="text-secondary-600">Sector allocation chart</p>
                    <p className="text-sm text-secondary-500">Coming soon</p>
                  </div>
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
            <div className="text-2xl font-bold gradient-text mb-2">42</div>
            <div className="text-secondary-600">Total Holdings</div>
          </div>
          
          <div className="bg-white p-6 rounded-xl border border-secondary-200 text-center card-hover">
            <div className="w-12 h-12 bg-gradient-to-br from-accent-500 to-primary-500 rounded-lg flex items-center justify-center mx-auto mb-4">
              <Globe className="h-6 w-6 text-white" />
            </div>
            <div className="text-2xl font-bold gradient-text mb-2">12</div>
            <div className="text-secondary-600">Countries</div>
          </div>
          
          <div className="bg-white p-6 rounded-xl border border-secondary-200 text-center card-hover">
            <div className="w-12 h-12 bg-gradient-to-br from-secondary-500 to-accent-500 rounded-lg flex items-center justify-center mx-auto mb-4">
              <TrendingUp className="h-6 w-6 text-white" />
            </div>
            <div className="text-2xl font-bold gradient-text mb-2">8.5%</div>
            <div className="text-secondary-600">Largest Position</div>
          </div>
          
          <div className="bg-white p-6 rounded-xl border border-secondary-200 text-center card-hover">
            <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-lg flex items-center justify-center mx-auto mb-4">
              <PieChart className="h-6 w-6 text-white" />
            </div>
            <div className="text-2xl font-bold gradient-text mb-2">6</div>
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
            For the most current holdings information, please contact Diamond Brothers LLC or refer to the most recent 
            fund fact sheet and prospectus.
          </p>
        </div>
      </div>
    </section>
  )
}

export default Holdings 