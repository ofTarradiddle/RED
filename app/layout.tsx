import React from 'react'
import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'RED ETF | Active Innovation Factor ETF | Diamond & Diamond (D&D)',
  description: 'RED Active Innovation Factor ETF (RED) - A forward-thinking ETF focused on innovative companies driving the future of technology and business.',
  keywords: 'ETF, RED, Active Innovation, Factor ETF, Diamond & Diamond, Investment, Technology, Innovation',
  authors: [{ name: 'Diamond & Diamond (D&D)' }],
  openGraph: {
    title: 'RED ETF | Active Innovation Factor ETF',
    description: 'A forward-thinking ETF focused on innovative companies driving the future of technology and business.',
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  )
} 