// Data loading utilities for performance and holdings data

export interface PerformanceDataPoint {
  date: string;
  red_etf: number;
  nav: number;
  sp500: number;
  premium_discount: number;
}

export interface HoldingsData {
  name: string;
  ticker: string;
  weight: number;
  sector: string;
  country?: string;
}

export interface PerformanceMetrics {
  ytd: number;
  oneMonth: number;
  threeMonth: number;
  sixMonth: number;
  oneYear: number;
  sinceInception: number;
}

export interface RiskMetrics {
  beta: number;
  sharpeRatio: number;
  maxDrawdown: number;
  volatility: number;
}

// Import real data from the generated file
import { performanceData, holdingsData } from './realData'

// Re-export the data arrays
export { performanceData, holdingsData }

export function calculatePerformanceMetrics(data: PerformanceDataPoint[]): PerformanceMetrics {
  const latest = data[data.length - 1];
  const inception = data[0];
  
  // Calculate YTD (from January 1st)
  const ytdStart = data.find(d => d.date.startsWith('2024-01-01'));
  const ytdReturn = ytdStart ? ((latest.red_etf / ytdStart.red_etf) - 1) * 100 : 0;
  
  // Calculate 1 Month (30 days ago)
  const oneMonthAgo = data[Math.max(0, data.length - 30)];
  const oneMonthReturn = ((latest.red_etf / oneMonthAgo.red_etf) - 1) * 100;
  
  // Calculate 3 Month (90 days ago)
  const threeMonthAgo = data[Math.max(0, data.length - 90)];
  const threeMonthReturn = ((latest.red_etf / threeMonthAgo.red_etf) - 1) * 100;
  
  // Calculate 6 Month (180 days ago)
  const sixMonthAgo = data[Math.max(0, data.length - 180)];
  const sixMonthReturn = ((latest.red_etf / sixMonthAgo.red_etf) - 1) * 100;
  
  // Calculate 1 Year (365 days ago)
  const oneYearAgo = data[Math.max(0, data.length - 365)];
  const oneYearReturn = ((latest.red_etf / oneYearAgo.red_etf) - 1) * 100;
  
  // Calculate Since Inception
  const sinceInceptionReturn = ((latest.red_etf / inception.red_etf) - 1) * 100;
  
  return {
    ytd: Math.round(ytdReturn * 100) / 100,
    oneMonth: Math.round(oneMonthReturn * 100) / 100,
    threeMonth: Math.round(threeMonthReturn * 100) / 100,
    sixMonth: Math.round(sixMonthReturn * 100) / 100,
    oneYear: Math.round(oneYearReturn * 100) / 100,
    sinceInception: Math.round(sinceInceptionReturn * 100) / 100
  };
}

export function calculateRiskMetrics(data: PerformanceDataPoint[]): RiskMetrics {
  // Calculate daily returns
  const returns = data.slice(1).map((point, index) => {
    const prevPoint = data[index];
    return (point.red_etf / prevPoint.red_etf) - 1;
  });
  
  // Calculate volatility (annualized standard deviation)
  const mean = returns.reduce((sum, ret) => sum + ret, 0) / returns.length;
  const variance = returns.reduce((sum, ret) => sum + Math.pow(ret - mean, 2), 0) / returns.length;
  const volatility = Math.sqrt(variance) * Math.sqrt(252) * 100; // Annualized
  
  // Calculate max drawdown
  let maxDrawdown = 0;
  let peak = data[0].red_etf;
  
  for (const point of data) {
    if (point.red_etf > peak) {
      peak = point.red_etf;
    }
    const drawdown = (point.red_etf / peak) - 1;
    if (drawdown < maxDrawdown) {
      maxDrawdown = drawdown;
    }
  }
  
  // Calculate Sharpe ratio (assuming 2% risk-free rate)
  const riskFreeRate = 0.02;
  const excessReturns = returns.map(ret => ret - riskFreeRate / 252);
  const excessReturnMean = excessReturns.reduce((sum, ret) => sum + ret, 0) / excessReturns.length;
  const sharpeRatio = (excessReturnMean * 252) / (Math.sqrt(variance) * Math.sqrt(252));
  
  // Calculate beta (correlation with S&P 500)
  const sp500Returns = data.slice(1).map((point, index) => {
    const prevPoint = data[index];
    return (point.sp500 / prevPoint.sp500) - 1;
  });
  
  const covariance = returns.reduce((sum, ret, index) => {
    return sum + (ret - mean) * (sp500Returns[index] - sp500Returns.reduce((s, r) => s + r, 0) / sp500Returns.length);
  }, 0) / returns.length;
  
  const sp500Variance = sp500Returns.reduce((sum, ret) => {
    const sp500Mean = sp500Returns.reduce((s, r) => s + r, 0) / sp500Returns.length;
    return sum + Math.pow(ret - sp500Mean, 2);
  }, 0) / sp500Returns.length;
  
  const beta = covariance / sp500Variance;
  
  return {
    beta: Math.round(beta * 100) / 100,
    sharpeRatio: Math.round(sharpeRatio * 100) / 100,
    maxDrawdown: Math.round(maxDrawdown * 10000) / 100, // Convert to percentage
    volatility: Math.round(volatility * 100) / 100
  };
}

export function getSectorAllocation(holdings: HoldingsData[]) {
  const sectorMap = new Map<string, number>();
  
  holdings.forEach(holding => {
    const currentWeight = sectorMap.get(holding.sector) || 0;
    sectorMap.set(holding.sector, currentWeight + holding.weight);
  });
  
  return Array.from(sectorMap.entries())
    .map(([sector, weight]) => ({ sector, weight: Math.round(weight * 100) / 100 }))
    .sort((a, b) => b.weight - a.weight);
}

export function getCountryAllocation(holdings: HoldingsData[]) {
  const countryMap = new Map<string, number>();
  
  holdings.forEach(holding => {
    if (holding.country) {
      const currentWeight = countryMap.get(holding.country) || 0;
      countryMap.set(holding.country, currentWeight + holding.weight);
    }
  });
  
  return Array.from(countryMap.entries())
    .map(([country, weight]) => ({ country, weight: Math.round(weight * 100) / 100 }))
    .sort((a, b) => b.weight - a.weight);
}

export function formatChartData(data: PerformanceDataPoint[]) {
  return {
    labels: data.map(point => point.date),
    datasets: [
      {
        label: 'RED ETF',
        data: data.map(point => point.red_etf),
        borderColor: '#dc2626',
        backgroundColor: 'rgba(220, 38, 38, 0.1)',
        borderWidth: 3,
        fill: false,
        tension: 0.4
      },
      {
        label: 'NAV',
        data: data.map(point => point.nav),
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37, 99, 235, 0.1)',
        borderWidth: 3,
        fill: false,
        tension: 0.4
      },
      {
        label: 'S&P 500',
        data: data.map(point => point.sp500),
        borderColor: '#6b7280',
        backgroundColor: 'rgba(107, 114, 128, 0.1)',
        borderWidth: 3,
        fill: false,
        tension: 0.4
      }
    ]
  };
}

export function formatPremiumDiscountData(data: PerformanceDataPoint[]) {
  return {
    labels: data.map(point => point.date),
    datasets: [
      {
        label: 'Premium/Discount',
        data: data.map(point => point.premium_discount),
        borderColor: '#8b0000',
        backgroundColor: 'rgba(139, 0, 0, 0.05)',
        borderWidth: 2,
        fill: true,
        tension: 0.1
      }
    ]
  };
}
