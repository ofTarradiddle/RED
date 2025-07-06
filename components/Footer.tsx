import React from 'react'
import { Mail, Phone, MapPin, ExternalLink } from 'lucide-react'

const Footer = () => {
  const quickLinks = [
    { name: 'Prospectus', href: '#' },
    { name: 'Fact Sheet', href: '#' },
    { name: 'Holdings', href: '#holdings' },
    { name: 'Performance', href: '#performance' },
  ]

  const resources = [
    { name: 'Investment Strategy', href: '#strategy' },
    { name: 'Risk Factors', href: '#' },
    { name: 'Tax Information', href: '#' },
    { name: 'Frequently Asked Questions', href: '#' },
  ]

  return (
    <footer className="bg-secondary-900 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-8">
          {/* Company Info */}
          <div className="lg:col-span-2">
            <div className="mb-6">
              <h3 className="text-2xl font-bold gradient-text mb-2">RED ETF</h3>
              <p className="text-secondary-300 text-sm">Active Innovation Factor ETF</p>
            </div>
            <p className="text-secondary-300 mb-6 max-w-md">
              A forward-thinking investment strategy focused on companies driving technological 
              advancement and market disruption across global markets.
            </p>
            <div className="flex items-center space-x-4 text-secondary-300">
              <div className="flex items-center space-x-2">
                <Mail className="h-4 w-4" />
                <span className="text-sm">info@diamondbrothers.com</span>
              </div>
              <div className="flex items-center space-x-2">
                <Phone className="h-4 w-4" />
                <span className="text-sm">+1 (555) 123-4567</span>
              </div>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="text-lg font-semibold mb-4">Quick Links</h4>
            <ul className="space-y-2">
              {quickLinks.map((link, index) => (
                <li key={index}>
                  <a
                    href={link.href}
                    className="text-secondary-300 hover:text-white transition-colors text-sm flex items-center"
                  >
                    {link.name}
                    <ExternalLink className="h-3 w-3 ml-1" />
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="text-lg font-semibold mb-4">Resources</h4>
            <ul className="space-y-2">
              {resources.map((link, index) => (
                <li key={index}>
                  <a
                    href={link.href}
                    className="text-secondary-300 hover:text-white transition-colors text-sm"
                  >
                    {link.name}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Legal Disclaimers */}
        <div className="border-t border-secondary-700 pt-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div>
              <h5 className="font-semibold mb-4">Important Disclosures</h5>
              <div className="text-sm text-secondary-300 space-y-2">
                <p>
                  An investment in the RED ETF involves risk, including possible loss of principal. 
                  The Fund's performance may not match or achieve a high degree of correlation with 
                  the performance of the underlying index.
                </p>
                <p>
                  Past performance does not guarantee future results. Investment returns and principal 
                  value will fluctuate so that an investor's shares, when redeemed, may be worth more 
                  or less than their original cost.
                </p>
                <p>
                  ETF shares trade at market price and may trade at a premium or discount to NAV. 
                  Diversification does not ensure a profit or protect against loss.
                </p>
              </div>
            </div>
            
            <div>
              <h5 className="font-semibold mb-4">Regulatory Information</h5>
              <div className="text-sm text-secondary-300 space-y-2">
                <p>
                  <strong>Investment Advisor:</strong> Diamond Brothers LLC<br />
                  <strong>Fund Ticker:</strong> RED<br />
                  <strong>CUSIP:</strong> 123456789
                </p>
                <p>
                  Before investing, you should carefully consider the Fund's investment objectives, 
                  risks, charges and expenses. This and other information is in the prospectus, 
                  a copy of which may be obtained by calling 1-555-123-4567.
                </p>
                <p>
                  Please read the prospectus carefully before you invest.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="border-t border-secondary-700 pt-6 mt-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="text-sm text-secondary-400 mb-4 md:mb-0">
              © 2024 Diamond Brothers LLC. All rights reserved.
            </div>
            <div className="flex space-x-6 text-sm text-secondary-400">
              <a href="#" className="hover:text-white transition-colors">Privacy Policy</a>
              <a href="#" className="hover:text-white transition-colors">Terms of Use</a>
              <a href="#" className="hover:text-white transition-colors">Disclosures</a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}

export default Footer 