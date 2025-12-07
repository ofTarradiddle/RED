# Website Structure

This repository follows the industry-standard approach used by firms like Cambria Investments and Sparkline Capital, with separate sites for different business divisions.

## Structure Overview

```
/
├── index.html          # RIA (Registered Investment Advisor) site - Main domain
├── red/                # ETF site - Subdirectory
│   ├── index.html      # RED ETF main page
│   ├── data/           # ETF data files
│   ├── blog/           # ETF blog posts
│   └── why-red.html    # ETF pitch deck
└── serve.py            # Local development server
```

## Site Separation

### RIA Site (`/`)
- **Purpose**: Investment Advisory Services
- **URL**: `yourdomain.com/`
- **Content**: Basic RIA information, services, contact
- **Audience**: Potential advisory clients

### ETF Site (`/red`)
- **Purpose**: Exchange-Traded Fund information
- **URL**: `yourdomain.com/red`
- **Content**: Fund details, performance, holdings, blog, pitch deck
- **Audience**: Investors, financial advisors, institutions

## Industry Examples

### Cambria Investment Management
- **RIA**: `cambriainvestments.com` (advisory services)
- **ETFs**: `cambriafunds.com` (ETF products)

### Sparkline Capital
- **RIA**: `sparklinecapital.com` (advisory services)
- **ETFs**: Separate site for ETF products

## Benefits of This Structure

1. **Regulatory Compliance**: Clear separation between advisory services and product marketing
2. **User Experience**: Tailored content for each audience
3. **Brand Clarity**: Distinct messaging for each business line
4. **SEO**: Better search engine optimization for each division
5. **Maintenance**: Easier to update and maintain separate sites

## Local Development

Run the local server:
```bash
python3 serve.py
```

Then visit:
- **RIA Site**: http://localhost:8080/
- **ETF Site**: http://localhost:8080/red

## Path References

All paths in the ETF site (`/red/`) are relative to the root domain:
- Data files: `/red/data/`
- Blog posts: `/red/blog/`
- Images: `/red/...`

This ensures the site works correctly whether accessed from the subdirectory or if you later move to a subdomain.

