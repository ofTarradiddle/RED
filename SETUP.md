# Setup Guide

## Environment Variables

This project requires API keys to be set as environment variables. Never commit API keys to the repository.

### Required Environment Variables

- `FMP_API_KEY`: Financial Modeling Prep API key
  - Get your API key from: https://financialmodelingprep.com/developer/docs/

### Setting Up Environment Variables

#### Option 1: Using a `.env` file (Recommended)

1. Copy the example environment file:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` and add your API key:
   ```
   FMP_API_KEY=your_actual_api_key_here
   ```

3. The `.env` file is already in `.gitignore` and will not be committed.

#### Option 2: Export in your shell

```bash
export FMP_API_KEY=your_actual_api_key_here
```

Add this to your `~/.bashrc`, `~/.zshrc`, or shell profile to make it persistent.

#### Option 3: Using GitLab CI/CD Variables (for CI/CD)

1. Go to your GitLab project → Settings → CI/CD → Variables
2. Add a new variable:
   - Key: `FMP_API_KEY`
   - Value: Your API key
   - Check "Mask variable" to hide it in logs
   - Check "Protect variable" if you want it only in protected branches

### Verifying Setup

Run any script that uses the API to verify your setup:

```bash
python lib/etf/functions/research/scripts/fetch_sp500_returns_fmp.py --help
```

If the API key is not set, you'll get a clear error message.

