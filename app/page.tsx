import React from 'react'
import Header from '@/components/Header'
import Hero from '@/components/Hero'
import About from '@/components/About'
import Strategy from '@/components/Strategy'
import Performance from '@/components/Performance'
import Holdings from '@/components/Holdings'
import Footer from '@/components/Footer'

export default function Home() {
  return (
    <main className="min-h-screen bg-white">
      <Header />
      <Hero />
      <About />
      <Strategy />
      <Performance />
      <Holdings />
      <Footer />
    </main>
  )
} 