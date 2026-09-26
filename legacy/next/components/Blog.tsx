import React, { useState } from 'react'
import { Calendar, Clock, ArrowRight, ExternalLink } from 'lucide-react'

interface BlogPost {
  id: string
  title: string
  excerpt: string
  date: string
  readTime: string
  category: string
  image: string
  featured?: boolean
}

const Blog = () => {
  const [selectedCategory, setSelectedCategory] = useState('All')

  const blogPosts: BlogPost[] = [
    {
      id: 'sample-post-1',
      title: 'The Future of Innovation in ETF Investing',
      excerpt: 'Exploring how technological disruption is reshaping the investment landscape and what it means for factor-based ETF strategies.',
      date: '2024-01-15',
      readTime: '5 min read',
      category: 'Strategy',
      image: '/api/placeholder/400/250',
      featured: true
    },
    {
      id: 'sample-post-2',
      title: 'Understanding Innovation Factors in Market Analysis',
      excerpt: 'A deep dive into the quantitative metrics we use to identify companies with superior innovation characteristics.',
      date: '2024-01-10',
      readTime: '7 min read',
      category: 'Analysis',
      image: '/api/placeholder/400/250'
    },
    {
      id: 'sample-post-3',
      title: 'Market Volatility and Innovation-Led Recovery',
      excerpt: 'How innovative companies have historically performed during market downturns and their role in economic recovery.',
      date: '2024-01-05',
      readTime: '6 min read',
      category: 'Market Insights',
      image: '/api/placeholder/400/250'
    },
    {
      id: 'sample-post-4',
      title: 'ESG Integration in Innovation-Focused Investing',
      excerpt: 'The intersection of environmental, social, and governance factors with innovation metrics in our investment process.',
      date: '2024-01-01',
      readTime: '8 min read',
      category: 'ESG',
      image: '/api/placeholder/400/250'
    }
  ]

  const categories = ['All', 'Strategy', 'Analysis', 'Market Insights', 'ESG']

  const filteredPosts = selectedCategory === 'All' 
    ? blogPosts 
    : blogPosts.filter(post => post.category === selectedCategory)

  const featuredPost = blogPosts.find(post => post.featured)
  const regularPosts = filteredPosts.filter(post => !post.featured)

  return (
    <section id="blog" className="py-20 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            Insights & Analysis
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Stay informed with our latest research, market insights, and strategic perspectives on innovation-driven investing.
          </p>
        </div>

        {/* Category Filter */}
        <div className="flex flex-wrap justify-center gap-4 mb-12">
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => setSelectedCategory(category)}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
                selectedCategory === category
                  ? 'bg-primary-600 text-white shadow-lg'
                  : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200'
              }`}
            >
              {category}
            </button>
          ))}
        </div>

        {/* Featured Post */}
        {featuredPost && selectedCategory === 'All' && (
          <div className="mb-16">
            <h3 className="text-2xl font-semibold text-gray-900 mb-8">Featured Article</h3>
            <div className="bg-white rounded-2xl shadow-xl overflow-hidden hover:shadow-2xl transition-shadow duration-300">
              <div className="md:flex">
                <div className="md:w-1/2">
                  <div className="h-64 md:h-full bg-gradient-to-br from-primary-50 to-primary-100 flex items-center justify-center">
                    <div className="text-center">
                      <div className="w-16 h-16 bg-primary-600 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span className="text-white text-2xl font-bold">📊</span>
                      </div>
                      <p className="text-primary-600 font-medium">Featured Content</p>
                    </div>
                  </div>
                </div>
                <div className="md:w-1/2 p-8">
                  <div className="flex items-center gap-4 mb-4">
                    <span className="px-3 py-1 bg-primary-100 text-primary-800 text-sm font-medium rounded-full">
                      {featuredPost.category}
                    </span>
                    <span className="text-sm text-gray-500">Featured</span>
                  </div>
                  <h4 className="text-2xl font-bold text-gray-900 mb-4">
                    {featuredPost.title}
                  </h4>
                  <p className="text-gray-600 mb-6 leading-relaxed">
                    {featuredPost.excerpt}
                  </p>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 text-sm text-gray-500">
                      <div className="flex items-center gap-1">
                        <Calendar size={16} />
                        {new Date(featuredPost.date).toLocaleDateString('en-US', { 
                          year: 'numeric', 
                          month: 'long', 
                          day: 'numeric' 
                        })}
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock size={16} />
                        {featuredPost.readTime}
                      </div>
                    </div>
                    <a 
                      href="/blog/sample-post-1.html"
                      className="button-primary flex items-center gap-2"
                    >
                      Read More
                      <ArrowRight size={16} />
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Blog Posts Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {regularPosts.map((post) => (
            <article
              key={post.id}
              className="bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-all duration-300 group"
            >
              <div className="h-48 bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center">
                <div className="text-center">
                  <div className="w-12 h-12 bg-primary-600 rounded-full flex items-center justify-center mx-auto mb-3">
                    <span className="text-white text-lg font-bold">📈</span>
                  </div>
                  <p className="text-gray-500 text-sm">Article Preview</p>
                </div>
              </div>
              <div className="p-6">
                <div className="flex items-center gap-3 mb-3">
                  <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs font-medium rounded">
                    {post.category}
                  </span>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-3 group-hover:text-primary-600 transition-colors">
                  {post.title}
                </h3>
                <p className="text-gray-600 mb-4 text-sm leading-relaxed">
                  {post.excerpt}
                </p>
                <div className="flex items-center justify-between text-sm text-gray-500 mb-4">
                  <div className="flex items-center gap-1">
                    <Calendar size={14} />
                    {new Date(post.date).toLocaleDateString('en-US', { 
                      month: 'short', 
                      day: 'numeric',
                      year: 'numeric'
                    })}
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock size={14} />
                    {post.readTime}
                  </div>
                </div>
                <a 
                  href={`/blog/${post.id}.html`}
                  className="w-full button-secondary flex items-center justify-center gap-2 group-hover:bg-primary-50 group-hover:text-primary-700 transition-colors"
                >
                  Read Article
                  <ExternalLink size={14} />
                </a>
              </div>
            </article>
          ))}
        </div>

        {/* Load More Button */}
        <div className="text-center mt-12">
          <a 
            href="/blog/index.html"
            className="button-primary px-8 py-3 inline-block"
          >
            View All Articles
          </a>
        </div>

        {/* Newsletter Signup */}
        <div className="mt-20 bg-primary-600 rounded-2xl p-8 text-center text-white">
          <h3 className="text-2xl font-bold mb-4">Stay Updated</h3>
          <p className="text-primary-100 mb-6 max-w-2xl mx-auto">
            Get the latest insights on innovation-driven investing delivered to your inbox.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 max-w-md mx-auto">
            <input
              type="email"
              placeholder="Enter your email"
              className="flex-1 px-4 py-3 rounded-lg text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-white/20"
            />
            <button className="bg-white text-primary-600 px-6 py-3 rounded-lg font-medium hover:bg-gray-100 transition-colors">
              Subscribe
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}

export default Blog
