// Ticker-AWARE demo data. Generates deterministic, distinct analysis per company
// so the dashboard changes with the ticker (used only in no-backend demo mode).
// With NEXT_PUBLIC_API_URL set, the live backend response is used instead.

import type {
  Citation, DebateResult, EvalReport, FinancialSnapshot,
  Holding, InvestmentReport, Recommendation, Sentiment,
} from "./types";

// ── Local company registry (mirrors the backend resolver, demo subset) ──
type Co = { name: string; sector: string; industry: string; region: "US" | "IN"; scale: number };
const REGISTRY: Record<string, Co> = {
  AAPL: { name: "Apple Inc.", sector: "Technology", industry: "Consumer Electronics", region: "US", scale: 3500 },
  MSFT: { name: "Microsoft Corporation", sector: "Technology", industry: "Software", region: "US", scale: 3300 },
  TSLA: { name: "Tesla, Inc.", sector: "Consumer Discretionary", industry: "Automobiles", region: "US", scale: 900 },
  NVDA: { name: "NVIDIA Corporation", sector: "Technology", industry: "Semiconductors", region: "US", scale: 3100 },
  GOOGL: { name: "Alphabet Inc.", sector: "Communication Services", industry: "Internet", region: "US", scale: 2200 },
  AMZN: { name: "Amazon.com, Inc.", sector: "Consumer Discretionary", industry: "E-Commerce", region: "US", scale: 2000 },
  META: { name: "Meta Platforms, Inc.", sector: "Communication Services", industry: "Social Media", region: "US", scale: 1300 },
  AMD: { name: "Advanced Micro Devices, Inc.", sector: "Technology", industry: "Semiconductors", region: "US", scale: 250 },
  JPM: { name: "JPMorgan Chase & Co.", sector: "Financials", industry: "Banking", region: "US", scale: 650 },
  KO: { name: "The Coca-Cola Company", sector: "Consumer Staples", industry: "Beverages", region: "US", scale: 280 },
  JNJ: { name: "Johnson & Johnson", sector: "Healthcare", industry: "Pharmaceuticals", region: "US", scale: 380 },
  XOM: { name: "Exxon Mobil Corporation", sector: "Energy", industry: "Oil & Gas", region: "US", scale: 500 },
  "RELIANCE.NS": { name: "Reliance Industries Limited", sector: "Energy", industry: "Conglomerate", region: "IN", scale: 230 },
  "INFY.NS": { name: "Infosys Limited", sector: "Technology", industry: "IT Services", region: "IN", scale: 80 },
  "TCS.NS": { name: "Tata Consultancy Services Limited", sector: "Technology", industry: "IT Services", region: "IN", scale: 170 },
  "HDFCBANK.NS": { name: "HDFC Bank Limited", sector: "Financials", industry: "Banking", region: "IN", scale: 150 },
  "WIPRO.NS": { name: "Wipro Limited", sector: "Technology", industry: "IT Services", region: "IN", scale: 30 },
  "TATAMOTORS.NS": { name: "Tata Motors Limited", sector: "Consumer Discretionary", industry: "Automobiles", region: "IN", scale: 45 },
};

const ALIASES: Record<string, string> = {
  apple: "AAPL", microsoft: "MSFT", tesla: "TSLA", nvidia: "NVDA", google: "GOOGL", alphabet: "GOOGL",
  amazon: "AMZN", meta: "META", facebook: "META", amd: "AMD", jpmorgan: "JPM", coke: "KO", "coca cola": "KO",
  reliance: "RELIANCE.NS", "reliance industries": "RELIANCE.NS", infosys: "INFY.NS",
  tcs: "TCS.NS", "tata consultancy services": "TCS.NS", hdfc: "HDFCBANK.NS", wipro: "WIPRO.NS",
  "tata motors": "TATAMOTORS.NS",
};

/** Resolve a name/symbol to a canonical ticker + profile (demo-side). */
export function resolveLocal(input: string): { ticker: string; co: Co } {
  const raw = (input ?? "").trim();
  const key = raw.toLowerCase();
  let ticker = ALIASES[key] ?? raw.toUpperCase();
  // base-symbol of an Indian alias e.g. "reliance.ns"
  if (!REGISTRY[ticker] && ALIASES[key.split(".")[0]]) ticker = ALIASES[key.split(".")[0]];
  const co = REGISTRY[ticker] ?? {
    name: ticker, sector: "Diversified", industry: "Diversified", region: ticker.endsWith(".NS") ? "IN" : "US", scale: 60,
  };
  return { ticker, co };
}

// ── Deterministic PRNG seeded by ticker (so a company always looks the same) ──
function seedFrom(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}
function rng(seed: number) { return () => ((seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 2 ** 32); }
const pick = <T,>(r: () => number, arr: T[]): T => arr[Math.floor(r() * arr.length)];
const round = (n: number, d = 2) => Number(n.toFixed(d));

const RECS: Recommendation[] = ["STRONG_BUY", "BUY", "BUY", "HOLD", "HOLD", "SELL", "STRONG_SELL"];
const SENTI: Sentiment[] = ["VERY_BULLISH", "BULLISH", "NEUTRAL", "BEARISH"];

function profile(input: string) {
  const { ticker, co } = resolveLocal(input);
  const r = rng(seedFrom(ticker));
  const cur = co.region === "IN" ? "INR" : "USD";
  const fx = co.region === "IN" ? 83 : 1;                       // crude USD→INR for magnitude
  const marketCap = co.scale * 1e9 * fx * (0.85 + r() * 0.3);
  const price = round(40 + r() * 460);
  const revenue = marketCap * (0.12 + r() * 0.4);
  const margin = 0.05 + r() * 0.32;
  const netIncome = revenue * margin;
  const shares = marketCap / price;
  const eps = round(netIncome / shares, 2);
  const pe = round(price / Math.max(eps, 0.1), 1);
  const ocf = netIncome * (1.1 + r() * 0.4);
  const fcf = ocf * (0.7 + r() * 0.25);
  const rec = pick(r, RECS);
  const conviction = 4 + Math.floor(r() * 6);
  const riskScore = 3 + Math.floor(r() * 6);
  const health = 4 + Math.floor(r() * 6);
  return { ticker, co, cur, marketCap, price, revenue, netIncome, eps, pe, ocf, fcf, rec, conviction, riskScore, health, r };
}

// ── Public generators ──
export function mockReportFor(input: string): InvestmentReport {
  const p = profile(input);
  const { co, ticker } = p;
  const riskLevel = p.riskScore >= 7 ? "HIGH" : p.riskScore >= 5 ? "ELEVATED" : p.riskScore >= 4 ? "MODERATE" : "LOW";
  const senti = p.rec.includes("BUY") ? "BULLISH" : p.rec.includes("SELL") ? "BEARISH" : "NEUTRAL";
  return {
    ticker, company_name: co.name, horizon: "12 months",
    recommendation: p.rec, conviction: p.conviction,
    executive_summary:
      `${co.name} operates in ${co.sector} (${co.industry}). On a 12-month view the setup is `
      + `${p.rec.includes("BUY") ? "constructive" : p.rec.includes("SELL") ? "challenged" : "balanced"}: `
      + `fundamentals score ${p.health}/10 while risk sits at ${p.riskScore}/10. Position sizing and entry discipline apply.`,
    key_thesis: [
      `Durable position in ${co.industry} with a defensible competitive setup`,
      `Cash generation (${p.cur} FCF) funds reinvestment and capital returns`,
      `${co.sector} demand trends support the medium-term growth path`,
    ],
    key_risks: [
      `Valuation re-rating risk at ${p.pe}x earnings`,
      `${co.sector} cyclicality and competitive intensity`,
      co.region === "IN" ? "Currency (INR) and regulatory exposure" : "Macro / rate sensitivity",
    ],
    research: {
      company_name: co.name, sector: co.sector,
      business_summary: `${co.name} is a ${co.industry} company in the ${co.sector} sector.`,
      moat: `Scale, brand and switching costs typical of leading ${co.industry} franchises.`,
      growth_drivers: [`${co.industry} expansion`, "Operating leverage", "Capital allocation"],
      competitive_threats: ["New entrants", "Pricing pressure", "Substitution risk"],
      bull_case: `If execution holds, ${co.name} compounds earnings and the multiple is sustained.`,
      bear_case: `If ${co.sector} demand softens, growth and margins compress and the multiple de-rates.`,
      filing_citations: mockCitationsFor(ticker).map(c => c.snippet ? `${ticker} ${c.form} (${c.section})` : `${ticker} ${c.form}`),
    },
    financials: {
      valuation_summary: `Trades around ${p.pe}x earnings — ${p.pe > 30 ? "premium" : p.pe > 18 ? "fair" : "undemanding"}.`,
      profitability: `Net margin ~${Math.round((p.netIncome / p.revenue) * 100)}%; quality of earnings is solid.`,
      balance_sheet: "Adequate liquidity; leverage within sector norms.",
      growth_trend: "Mid-to-high single digit revenue growth with operating leverage.",
      key_metrics: { pe_ratio: p.pe, eps: p.eps },
      financial_health_score: p.health,
    },
    news: {
      overall_sentiment: senti as Sentiment,
      summary: `Recent ${co.name} news flow is ${senti.toLowerCase()}; watch ${co.sector} catalysts.`,
      catalysts: ["Earnings", "Product / strategy updates", `${co.sector} policy`],
      notable_items: [
        { headline: `${co.name} reports quarterly results`, sentiment: senti as Sentiment, relevance: "Sets the near-term tone" },
      ],
    },
    risk: {
      overall_risk: riskLevel as InvestmentReport["risk"]["overall_risk"],
      market_risk: `Beta-driven sensitivity; ${co.sector} factor exposure.`,
      financial_risk: p.health >= 7 ? "Low — strong cash generation." : "Moderate — watch leverage/margins.",
      business_risk: "Competitive and execution risk inherent to the industry.",
      red_flags: p.rec.includes("SELL") ? ["Deteriorating momentum", "Valuation premium"] : ["Valuation premium"],
      risk_score: p.riskScore,
    },
    generated_at: new Date().toISOString(),
    trace: [
      `supervisor: planned analysis for ${co.name} (${ticker})`,
      `research: completed equity research`,
      `financial: fundamentals via [sec_edgar,yahoo]`,
      `news: analyzed headlines (sentiment ${senti})`,
      `risk: overall=${riskLevel}`,
      `supervisor: final call = ${p.rec} (conviction ${p.conviction}/10)`,
    ],
  };
}

export function mockSnapshotFor(input: string): FinancialSnapshot {
  const p = profile(input);
  return {
    ticker: p.ticker,
    overview: {
      ticker: p.ticker, name: p.co.name, sector: p.co.sector, industry: p.co.industry,
      exchange: p.co.region === "IN" ? "NSE" : "NasdaqGS", currency: p.cur,
      country: p.co.region === "IN" ? "India" : "United States",
      employees: Math.round(5000 + p.r() * 200000),
      description: `${p.co.name} — ${p.co.industry} (${p.co.sector}).`,
    },
    metrics: {
      ticker: p.ticker, revenue: round(p.revenue, 0), net_income: round(p.netIncome, 0), eps: p.eps,
      market_cap: round(p.marketCap, 0), pe_ratio: p.pe,
      operating_cash_flow: round(p.ocf, 0), free_cash_flow: round(p.fcf, 0),
      fiscal_period: "FY ending 2025", currency: p.cur,
    },
    providers_used: ["sec_edgar", "yahoo", "fmp"],
    field_sources: { revenue: "sec_edgar", market_cap: "fmp", pe_ratio: "yahoo", eps: "sec_edgar" },
    warnings: [],
  };
}

export function mockDebateFor(input: string): DebateResult {
  const p = profile(input);
  const winner = p.rec.includes("SELL") ? "bear" : p.rec.includes("BUY") ? "bull" : (p.r() > 0.5 ? "bull" : "bear");
  return {
    ticker: p.ticker, company_name: p.co.name, rounds: 2, confidence: p.conviction,
    bull_thesis: {
      stance: "bull", thesis: `${p.co.name} is a quality ${p.co.industry} compounder worth owning through the cycle.`,
      key_points: ["Competitive moat", "Cash generation", `${p.co.sector} tailwinds`],
      strongest_point: "Durable franchise economics", acknowledged_weaknesses: ["Valuation", "Cyclicality"], confidence: Math.min(9, p.conviction + 1),
    },
    bear_thesis: {
      stance: "bear", thesis: `The ${p.pe}x multiple discounts a lot; ${p.co.sector} risks are underpriced.`,
      key_points: ["Valuation premium", "Competitive pressure", "Macro sensitivity"],
      strongest_point: "Asymmetric downside if growth slows", acknowledged_weaknesses: ["Near-term momentum"], confidence: Math.max(4, 11 - p.conviction),
    },
    judge: {
      winner, recommendation: p.rec, confidence: p.conviction,
      bull_score: winner === "bull" ? 8 : 6, bear_score: winner === "bear" ? 8 : 6,
      reasoning: `Weighing both sides for ${p.co.name}, the ${winner} case is better supported on current evidence.`,
      decisive_argument: winner === "bull" ? "Franchise durability sustains returns" : "Risk/reward skews unfavorable at this multiple",
      key_factors: ["Valuation", "Growth durability", "Risk profile"],
    },
    transcript: [
      { round: 1, stance: "bull", confidence: p.conviction, summary: `${p.co.name} is mispriced to the upside.`, claims: ["Moat intact", "FCF compounding"], rebuttals: [], evidence: [`${p.pe}x P/E`] },
      { round: 1, stance: "bear", confidence: Math.max(4, 11 - p.conviction), summary: "Premium leaves no margin for error.", claims: ["Valuation stretched"], rebuttals: ["Growth can disappoint"], evidence: [`${p.co.sector} cyclicality`] },
    ],
  };
}

export function mockCitationsFor(input: string): Citation[] {
  const { ticker, co } = resolveLocal(input);
  if (co.region === "IN") {
    return [
      { ticker, company: co.name, form: "Annual Report", section: "Risk Factors", accession: `${ticker}-AR-2025`, filing_date: "2025-05-30", url: "https://www.nseindia.com/", snippet: `Risks relating to ${co.industry} and regulatory environment...`, score: 0.81 },
      { ticker, company: co.name, form: "Quarterly", section: "MD&A", accession: `${ticker}-Q-2025`, filing_date: "2025-07-20", url: "https://www.nseindia.com/", snippet: `Revenue growth driven by ${co.sector} demand...`, score: 0.77 },
    ];
  }
  return [
    { ticker, company: co.name, form: "10-K", section: "Item 1A Risk Factors", accession: `${ticker}-10K-2025`, filing_date: "2025-02-26", url: "https://www.sec.gov/edgar", snippet: `Our ${co.industry} business faces competition and regulatory risk...`, score: 0.83 },
    { ticker, company: co.name, form: "10-Q", section: "Item 2 MD&A", accession: `${ticker}-10Q-2025`, filing_date: "2025-08-27", url: "https://www.sec.gov/edgar", snippet: `Revenue increased on ${co.sector} demand...`, score: 0.79 },
  ];
}

export function mockPriceSeriesFor(input: string) {
  const p = profile(input);
  const r = rng(seedFrom(p.ticker + "px"));
  const base = p.price;
  return Array.from({ length: 60 }, (_, i) => {
    const drift = (p.rec.includes("BUY") ? 1 : p.rec.includes("SELL") ? -1 : 0) * i * 0.25;
    const noise = Math.sin(i / 3 + r() * 6) * (base * 0.04) + Math.cos(i / 7) * (base * 0.02);
    return { t: `D${i + 1}`, price: round(base + drift + noise, 2), volume: Math.round(40 + Math.abs(noise) * 4) };
  });
}

// ── Static, multi-company fixtures (not tied to one ticker) ──
export const mockPortfolio: Holding[] = [
  { ticker: "NVDA", name: "NVIDIA", weight: 0.22, recommendation: "BUY", conviction: 8, riskScore: 6, sector: "Technology" },
  { ticker: "AAPL", name: "Apple", weight: 0.18, recommendation: "HOLD", conviction: 6, riskScore: 4, sector: "Technology" },
  { ticker: "MSFT", name: "Microsoft", weight: 0.20, recommendation: "BUY", conviction: 7, riskScore: 3, sector: "Technology" },
  { ticker: "JNJ", name: "Johnson & Johnson", weight: 0.12, recommendation: "HOLD", conviction: 5, riskScore: 3, sector: "Healthcare" },
  { ticker: "XOM", name: "Exxon Mobil", weight: 0.10, recommendation: "SELL", conviction: 6, riskScore: 7, sector: "Energy" },
  { ticker: "JPM", name: "JPMorgan", weight: 0.18, recommendation: "BUY", conviction: 7, riskScore: 5, sector: "Financials" },
];

export const mockEval: EvalReport = {
  run_id: "eval-demo01", created_at: new Date().toISOString(), n_samples: 24, overall_quality: 0.82,
  metric_averages: { faithfulness: 0.88, hallucination_rate: 0.11, retrieval_quality: 0.79, tool_usage_accuracy: 0.91, response_completeness: 0.84 },
  pass_rates: { faithfulness: 0.83, hallucination_rate: 0.88, retrieval_quality: 0.71, tool_usage_accuracy: 0.92, response_completeness: 0.79 },
  agent_breakdown: {
    research: { faithfulness: 0.9, retrieval_quality: 0.82, response_completeness: 0.86 },
    financial: { faithfulness: 0.86, tool_usage_accuracy: 0.94, response_completeness: 0.83 },
    risk: { faithfulness: 0.88, response_completeness: 0.81 },
  },
  failures: [
    { sample_id: "amd-fin-3", agent: "financial", metric: "retrieval_quality", score: 0.42, question: "Summarize AMD's cash flow.", reason: "precision=0.40, recall=0.50" },
    { sample_id: "tsla-risk-2", agent: "risk", metric: "faithfulness", score: 0.55, question: "Tesla key risks?", reason: "2/4 claims supported" },
  ],
};
