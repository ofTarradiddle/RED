# RED ETF Website

A modern, minimalist website for the RED Active Innovation Factor ETF, managed by Diamond Brothers LLC. This website showcases the ETF's investment strategy, performance, holdings, and provides essential information for potential investors.

## Features

- **Modern Design**: Clean, professional design inspired by leading investment firms
- **Responsive Layout**: Optimized for desktop, tablet, and mobile devices
- **Interactive Components**: Smooth animations and hover effects
- **Performance Focused**: Built with Next.js for optimal performance
- **Accessibility**: WCAG compliant design and navigation

## Technology Stack

- **Framework**: Next.js 14 with App Router
- **Styling**: Tailwind CSS with custom design system
- **Icons**: Lucide React
- **Animations**: Framer Motion
- **Language**: TypeScript
- **Deployment**: Vercel-ready

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd red-etf-website
```

2. Install dependencies:
```bash
npm install
# or
yarn install
```

3. Run the development server:
```bash
npm run dev
# or
yarn dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
red-etf-website/
├── app/                    # Next.js app directory
│   ├── globals.css        # Global styles and Tailwind imports
│   ├── layout.tsx         # Root layout component
│   └── page.tsx           # Homepage component
├── components/            # React components
│   ├── Header.tsx         # Navigation header
│   ├── Hero.tsx           # Hero section
│   ├── About.tsx          # About section
│   ├── Strategy.tsx       # Investment strategy
│   ├── Performance.tsx    # Performance metrics
│   ├── Holdings.tsx       # Portfolio holdings
│   └── Footer.tsx         # Footer with legal info
├── public/                # Static assets
├── package.json           # Dependencies and scripts
├── tailwind.config.js     # Tailwind configuration
├── tsconfig.json          # TypeScript configuration
└── README.md              # Project documentation
```

## Design System

### Colors
- **Primary**: Red gradient (#ef4444 to #dc2626)
- **Secondary**: Slate grays (#64748b to #0f172a)
- **Accent**: Blue gradient (#0ea5e9 to #0284c7)

### Typography
- **Font Family**: Inter (Google Fonts)
- **Weights**: 300, 400, 500, 600, 700, 800

### Components
- **Buttons**: Primary and secondary button styles
- **Cards**: Hover effects and glass morphism
- **Navigation**: Fixed header with mobile menu
- **Sections**: Consistent spacing and layout

## Content Sections

1. **Hero**: Compelling introduction with key metrics
2. **About**: Investment philosophy and key themes
3. **Strategy**: Investment methodology and process
4. **Performance**: Historical returns and risk metrics
5. **Holdings**: Top holdings and sector allocation
6. **Footer**: Legal disclaimers and contact information

## Legal Compliance

The website includes standard investment disclaimers and regulatory information required for ETF marketing materials:

- Performance disclaimers
- Risk factor disclosures
- Regulatory information
- Contact details for Diamond Brothers LLC

## Deployment

### Vercel (Recommended)

1. Push your code to GitHub
2. Connect your repository to Vercel
3. Deploy automatically on push

### Other Platforms

The project can be deployed to any platform that supports Next.js:
- Netlify
- AWS Amplify
- DigitalOcean App Platform

## Customization

### Updating Content

- Edit component files in the `components/` directory
- Update metadata in `app/layout.tsx`
- Modify styling in `app/globals.css` and `tailwind.config.js`

### Adding New Sections

1. Create a new component in `components/`
2. Import and add to `app/page.tsx`
3. Update navigation in `components/Header.tsx`

## Performance Optimization

- Images optimized with Next.js Image component
- CSS purged with Tailwind
- Code splitting with Next.js
- SEO optimized with metadata

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

© 2024 Diamond Brothers LLC. All rights reserved.

## Contact

For questions about the RED ETF or this website:
- Email: info@diamondbrothers.com
- Phone: +1 (555) 123-4567

---

**Important**: This website is for informational purposes only and does not constitute investment advice. Please read the prospectus carefully before investing. 