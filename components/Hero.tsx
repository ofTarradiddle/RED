import React from 'react'
import { ArrowRight, TrendingUp, Zap } from 'lucide-react'

const Hero = () => {
  return (
    <section className="relative pt-16 pb-20 bg-gradient-to-br from-secondary-50 via-white to-accent-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center">
          {/* Main Headline */}
          <h1 className="text-4xl md:text-6xl font-bold text-secondary-900 mb-6">
            The Future of
            <span className="gradient-text block"> Innovation</span>
          </h1>
          
          {/* Subtitle */}
          <p className="text-xl md:text-2xl text-secondary-600 mb-8 max-w-3xl mx-auto">
            RED Active Innovation Factor ETF (RED) - A forward-thinking investment strategy 
            focused on companies driving technological advancement and market disruption.
          </p>

          {/* Key Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12 max-w-4xl mx-auto">
            <div className="text-center">
              <div className="text-3xl font-bold gradient-text mb-2">RED</div>
              <div className="text-secondary-600">Ticker Symbol</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold gradient-text mb-2">Active</div>
              <div className="text-secondary-600">Management Style</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold gradient-text mb-2">Innovation</div>
              <div className="text-secondary-600">Investment Focus</div>
            </div>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <button className="button-primary group">
              Learn More
              <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
            </button>
            <button className="button-secondary">
              Download Prospectus
            </button>
          </div>

          {/* Trust Indicators */}
          <div className="mt-16 pt-8 border-t border-secondary-200">
            <p className="text-sm text-secondary-500 mb-4">Managed by Diamond Brothers LLC</p>
            <div className="flex justify-center items-center space-x-8 text-secondary-400">
              <div className="flex items-center space-x-2">
                <TrendingUp className="h-5 w-5" />
                <span className="text-sm">Active Management</span>
              </div>
              <div className="flex items-center space-x-2">
                <Zap className="h-5 w-5" />
                <span className="text-sm">Innovation Focus</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Background Elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-primary-100 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-pulse"></div>
        <div className="absolute top-40 right-10 w-72 h-72 bg-accent-100 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-pulse animation-delay-2000"></div>
      </div>
    </section>
  )
}

export default Hero 