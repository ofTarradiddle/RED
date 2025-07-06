import React from 'react'
import { BarChart3, Search, Filter, TrendingUp } from 'lucide-react'

const Strategy = () => {
  const processSteps = [
    {
      icon: Search,
      title: 'Research & Discovery',
      description: 'Comprehensive analysis of innovative companies across global markets using proprietary screening criteria.'
    },
    {
      icon: Filter,
      title: 'Factor Analysis',
      description: 'Evaluation of innovation factors including R&D intensity, patent activity, and market disruption potential.'
    },
    {
      icon: BarChart3,
      title: 'Portfolio Construction',
      description: 'Strategic allocation based on risk-adjusted return potential and correlation analysis.'
    },
    {
      icon: TrendingUp,
      title: 'Active Management',
      description: 'Continuous monitoring and rebalancing to maintain optimal exposure to innovation themes.'
    }
  ]

  return (
    <section id="strategy" className="py-20 bg-secondary-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-secondary-900 mb-6">
            Investment Strategy
          </h2>
          <p className="text-xl text-secondary-600 max-w-3xl mx-auto">
            Our systematic approach combines quantitative screening with fundamental analysis 
            to identify the most promising innovative companies across global markets.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center mb-16">
          <div>
            <h3 className="text-2xl font-bold text-secondary-900 mb-6">
              Innovation Factor Methodology
            </h3>
            <p className="text-secondary-600 mb-6">
              The RED ETF employs a proprietary innovation factor model that evaluates companies 
              based on multiple dimensions of innovation, including research and development 
              intensity, intellectual property strength, and market disruption potential.
            </p>
            <p className="text-secondary-600 mb-6">
              Our quantitative screening process identifies companies with above-average 
              innovation metrics, which are then subject to rigorous fundamental analysis 
              by our investment team.
            </p>
            
            <div className="bg-white p-6 rounded-xl border border-secondary-200">
              <h4 className="font-semibold text-secondary-900 mb-4">Key Innovation Factors</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="font-medium text-secondary-900">R&D Intensity</div>
                  <div className="text-secondary-600">Research spending as % of revenue</div>
                </div>
                <div>
                  <div className="font-medium text-secondary-900">Patent Activity</div>
                  <div className="text-secondary-600">Patent filings and citations</div>
                </div>
                <div>
                  <div className="font-medium text-secondary-900">Market Disruption</div>
                  <div className="text-secondary-600">Potential to disrupt existing markets</div>
                </div>
                <div>
                  <div className="font-medium text-secondary-900">Growth Metrics</div>
                  <div className="text-secondary-600">Revenue and earnings growth rates</div>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            {processSteps.map((step, index) => (
              <div key={index} className="flex items-start space-x-4">
                <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center flex-shrink-0">
                  <step.icon className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h4 className="text-lg font-semibold text-secondary-900 mb-2">
                    {step.title}
                  </h4>
                  <p className="text-secondary-600">
                    {step.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Strategy Highlights */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-white p-8 rounded-xl border border-secondary-200 text-center card-hover">
            <div className="text-3xl font-bold gradient-text mb-2">30-50</div>
            <div className="text-secondary-600 mb-4">Target Holdings</div>
            <p className="text-sm text-secondary-600">
              Concentrated portfolio of high-conviction positions in innovative companies
            </p>
          </div>
          
          <div className="bg-white p-8 rounded-xl border border-secondary-200 text-center card-hover">
            <div className="text-3xl font-bold gradient-text mb-2">Global</div>
            <div className="text-secondary-600 mb-4">Market Coverage</div>
            <p className="text-sm text-secondary-600">
              Access to innovative companies across developed and emerging markets worldwide
            </p>
          </div>
          
          <div className="bg-white p-8 rounded-xl border border-secondary-200 text-center card-hover">
            <div className="text-3xl font-bold gradient-text mb-2">Active</div>
            <div className="text-secondary-600 mb-4">Management Style</div>
            <p className="text-sm text-secondary-600">
              Dynamic portfolio management with regular rebalancing and position adjustments
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}

export default Strategy 