import React from 'react'
import { TrendingUp, Calendar, DollarSign, BarChart3 } from 'lucide-react'

const Performance = () => {
  const performanceData = {
    ytd: '+15.2%',
    oneYear: '+28.4%',
    threeYear: '+42.1%',
    sinceInception: '+67.3%'
  }

  const riskMetrics = [
    { label: 'Beta', value: '1.15', description: 'vs S&P 500' },
    { label: 'Sharpe Ratio', value: '1.42', description: 'Risk-adjusted return' },
    { label: 'Max Drawdown', value: '-18.2%', description: 'Historical maximum loss' },
    { label: 'Volatility', value: '24.8%', description: 'Annualized standard deviation' }
  ]

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
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-16">
          <div className="bg-gradient-to-br from-primary-50 to-primary-100 p-6 rounded-xl text-center">
            <div className="text-2xl font-bold gradient-text mb-2">{performanceData.ytd}</div>
            <div className="text-secondary-600 text-sm">YTD Return</div>
          </div>
          <div className="bg-gradient-to-br from-accent-50 to-accent-100 p-6 rounded-xl text-center">
            <div className="text-2xl font-bold gradient-text mb-2">{performanceData.oneYear}</div>
            <div className="text-secondary-600 text-sm">1 Year Return</div>
          </div>
          <div className="bg-gradient-to-br from-secondary-50 to-secondary-100 p-6 rounded-xl text-center">
            <div className="text-2xl font-bold gradient-text mb-2">{performanceData.threeYear}</div>
            <div className="text-secondary-600 text-sm">3 Year Return</div>
          </div>
          <div className="bg-gradient-to-br from-primary-50 to-accent-100 p-6 rounded-xl text-center">
            <div className="text-2xl font-bold gradient-text mb-2">{performanceData.sinceInception}</div>
            <div className="text-secondary-600 text-sm">Since Inception</div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          {/* Performance Chart Placeholder */}
          <div className="bg-secondary-50 p-8 rounded-xl">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-semibold text-secondary-900">Performance Chart</h3>
              <BarChart3 className="h-6 w-6 text-secondary-400" />
            </div>
            <div className="bg-white p-6 rounded-lg border border-secondary-200">
              <div className="h-64 flex items-center justify-center">
                <div className="text-center">
                  <TrendingUp className="h-12 w-12 text-primary-500 mx-auto mb-4" />
                  <p className="text-secondary-600">Interactive performance chart</p>
                  <p className="text-sm text-secondary-500">Coming soon</p>
                </div>
              </div>
            </div>
            <p className="text-sm text-secondary-500 mt-4">
              * Past performance does not guarantee future results. Investment returns and principal value will fluctuate.
            </p>
          </div>

          {/* Risk Metrics */}
          <div>
            <h3 className="text-xl font-semibold text-secondary-900 mb-6">Risk & Volatility Metrics</h3>
            <div className="space-y-4">
              {riskMetrics.map((metric, index) => (
                <div key={index} className="bg-secondary-50 p-4 rounded-lg">
                  <div className="flex justify-between items-center">
                    <div>
                      <div className="font-medium text-secondary-900">{metric.label}</div>
                      <div className="text-sm text-secondary-600">{metric.description}</div>
                    </div>
                    <div className="text-xl font-bold gradient-text">{metric.value}</div>
                  </div>
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
                current to the most recent month-end, please contact Diamond Brothers LLC.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default Performance 