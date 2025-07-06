import React from 'react'
import { Target, Users, Shield, Globe } from 'lucide-react'

const About = () => {
  const features = [
    {
      icon: Target,
      title: 'Focused Strategy',
      description: 'Concentrated portfolio of innovative companies with high growth potential and disruptive technologies.'
    },
    {
      icon: Users,
      title: 'Active Management',
      description: 'Expert portfolio management by Diamond Brothers LLC with deep expertise in technology and innovation.'
    },
    {
      icon: Shield,
      title: 'Risk Management',
      description: 'Sophisticated risk controls and diversification strategies to manage volatility while capturing growth.'
    },
    {
      icon: Globe,
      title: 'Global Reach',
      description: 'Access to innovative companies across global markets, not limited by geographic boundaries.'
    }
  ]

  return (
    <section id="about" className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-secondary-900 mb-6">
            About RED ETF
          </h2>
          <p className="text-xl text-secondary-600 max-w-3xl mx-auto">
            The RED Active Innovation Factor ETF seeks to provide long-term capital appreciation 
            by investing in companies that are driving innovation across technology, healthcare, 
            and other transformative industries.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center mb-16">
          <div>
            <h3 className="text-2xl font-bold text-secondary-900 mb-6">
              Investment Philosophy
            </h3>
            <p className="text-secondary-600 mb-6">
              We believe that innovation is the primary driver of long-term value creation in today's 
              rapidly evolving economy. Our strategy focuses on identifying and investing in companies 
              that are at the forefront of technological advancement and market disruption.
            </p>
            <p className="text-secondary-600 mb-6">
              Through active management and rigorous fundamental analysis, we seek to construct a 
              concentrated portfolio of high-quality, innovative companies with strong growth potential 
              and sustainable competitive advantages.
            </p>
            <div className="flex items-center space-x-4">
              <div className="text-2xl font-bold gradient-text">Diamond Brothers LLC</div>
              <div className="text-sm text-secondary-500">Investment Advisor</div>
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-secondary-50 to-accent-50 p-8 rounded-2xl">
            <h4 className="text-xl font-semibold text-secondary-900 mb-4">Key Investment Themes</h4>
            <ul className="space-y-3 text-secondary-700">
              <li className="flex items-start">
                <div className="w-2 h-2 bg-primary-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                <span>Artificial Intelligence & Machine Learning</span>
              </li>
              <li className="flex items-start">
                <div className="w-2 h-2 bg-primary-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                <span>Biotechnology & Healthcare Innovation</span>
              </li>
              <li className="flex items-start">
                <div className="w-2 h-2 bg-primary-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                <span>Clean Energy & Sustainability</span>
              </li>
              <li className="flex items-start">
                <div className="w-2 h-2 bg-primary-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                <span>Digital Transformation</span>
              </li>
              <li className="flex items-start">
                <div className="w-2 h-2 bg-primary-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                <span>Emerging Technologies</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {features.map((feature, index) => (
            <div key={index} className="text-center card-hover p-6 rounded-xl bg-white border border-secondary-100">
              <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center mx-auto mb-4">
                <feature.icon className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-secondary-900 mb-3">
                {feature.title}
              </h3>
              <p className="text-secondary-600 text-sm">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default About 