import type {
  Citation, DebateResult, EvalReport, FinancialSnapshot,
  Holding, InvestmentReport,
} from "./types";

export const mockReport: InvestmentReport = {
  ticker: "NVDA",
  company_name: "NVIDIA Corporation",
  horizon: "12 months",
  recommendation: "BUY",
  conviction: 8,
  executive_summary:
    "NVIDIA remains the structural winner of the AI compute buildout, with a durable CUDA software moat and accelerating data-center revenue. Valuation is rich, so position sizing and entry discipline matter, but the risk/reward over a 12-month horizon skews favorable.",
  key_thesis: [
    "Dominant share of AI training/inference accelerators with a wide CUDA moat",
    "Data-center revenue compounding as hyperscaler capex stays elevated",
    "Pricing power and >70% gross margins fund continued R&D leadership",
  ],
  key_risks: [
    "Valuation leaves little margin for execution slips",
    "Customer concentration among a few hyperscalers",
    "Export controls and geopolitical exposure to China demand",
  ],
  research: {
    company_name: "NVIDIA Corporation",
    sector: "Technology",
    business_summary:
      "NVIDIA designs accelerated-computing GPUs and the CUDA software stack powering AI training and inference, gaming, and professional visualization.",
    moat: "CUDA software ecosystem lock-in, full-stack systems (GPU + networking + software), and a multi-year hardware roadmap lead.",
    growth_drivers: ["Generative-AI capex supercycle", "Inference workloads scaling", "Networking (NVLink/InfiniBand) attach", "Sovereign-AI demand"],
    competitive_threats: ["AMD MI-series", "Custom hyperscaler silicon (TPU/Trainium)", "Supply concentration at TSMC"],
    bull_case: "AI compute demand outruns supply for multiple years; NVIDIA captures the majority of accelerator spend while expanding into systems and software.",
    bear_case: "Hyperscaler capex digestion plus custom-silicon substitution compresses growth and the premium multiple de-rates sharply.",
    filing_citations: [
      "NVDA 10-K filed 2025-02-26 (accession 0001045810-25-000023), Item 1A Risk Factors",
      "NVDA 10-Q filed 2025-08-27 (accession 0001045810-25-000119), Item 2 MD&A",
    ],
  },
  financials: {
    valuation_summary: "Premium on forward earnings (~35x), justified only if data-center growth persists at current pace.",
    profitability: "Exceptional: ~75% gross margin, ~60% operating margin, high return on invested capital.",
    balance_sheet: "Net cash, ample liquidity, minimal leverage.",
    growth_trend: "Triple-digit YoY data-center growth decelerating to a still-strong double-digit base.",
    key_metrics: { trailing_pe: 48.2, gross_margin: 0.75, revenue_growth: 1.22, return_on_equity: 1.15 },
    financial_health_score: 9,
  },
  news: {
    overall_sentiment: "BULLISH",
    summary: "Flow remains constructive on sustained data-center demand and new architecture launches; watch export-policy headlines.",
    catalysts: ["Next-gen architecture ramp", "Hyperscaler capex guides", "China export-policy updates"],
    notable_items: [
      { headline: "Cloud providers reiterate elevated AI capex into next year", sentiment: "BULLISH", relevance: "Supports data-center revenue durability" },
      { headline: "New export-control proposals under review", sentiment: "BEARISH", relevance: "Risk to China-region demand" },
    ],
  },
  risk: {
    overall_risk: "ELEVATED",
    market_risk: "High beta; sensitive to rate moves and risk-sentiment rotations out of mega-cap tech.",
    financial_risk: "Low — net cash, high margins, strong cash generation.",
    business_risk: "Customer concentration and supply dependence on TSMC; competitive substitution risk.",
    red_flags: ["Valuation premium", "China revenue exposure"],
    risk_score: 6,
  },
  generated_at: new Date().toISOString(),
  trace: [
    "supervisor: planned analysis for NVIDIA Corporation (NVDA)",
    "research: completed equity research (RAG-grounded)",
    "financial: fundamentals via [sec_edgar,yahoo]",
    "news: analyzed 8 headlines",
    "risk: overall=ELEVATED",
    "supervisor: final call = BUY (conviction 8/10)",
  ],
};

export const mockSnapshot: FinancialSnapshot = {
  ticker: "NVDA",
  overview: {
    ticker: "NVDA", name: "NVIDIA Corporation", sector: "Technology",
    industry: "Semiconductors", exchange: "NasdaqGS", currency: "USD",
    country: "United States", employees: 29600,
    description: "Accelerated computing and AI platform company.",
  },
  metrics: {
    ticker: "NVDA", revenue: 130_500_000_000, net_income: 72_880_000_000, eps: 2.94,
    market_cap: 3_180_000_000_000, pe_ratio: 48.2,
    operating_cash_flow: 64_100_000_000, free_cash_flow: 60_700_000_000,
    fiscal_period: "FY ending 2025-01-26", currency: "USD",
  },
  providers_used: ["sec_edgar", "yahoo", "fmp"],
  field_sources: { revenue: "sec_edgar", market_cap: "fmp", pe_ratio: "yahoo", eps: "sec_edgar" },
  warnings: [],
};

export const mockDebate: DebateResult = {
  ticker: "NVDA",
  company_name: "NVIDIA Corporation",
  rounds: 2,
  confidence: 7,
  bull_thesis: {
    stance: "bull",
    thesis: "NVIDIA is the indispensable platform of the AI era; demand visibility and the CUDA moat justify ownership despite the premium.",
    key_points: ["CUDA lock-in", "Multi-year roadmap lead", "Margin-funded R&D flywheel"],
    strongest_point: "Software ecosystem makes switching costs prohibitive for AI developers.",
    acknowledged_weaknesses: ["Valuation premium", "Cyclical capex exposure"],
    confidence: 8,
  },
  bear_thesis: {
    stance: "bear",
    thesis: "The multiple discounts perfection; capex digestion and custom silicon erode both growth and margins.",
    key_points: ["Hyperscaler in-housing", "Capex cyclicality", "Geopolitical demand risk"],
    strongest_point: "Top customers are actively building substitutes (TPU, Trainium).",
    acknowledged_weaknesses: ["Near-term demand still robust", "No credible CUDA alternative yet"],
    confidence: 6,
  },
  judge: {
    winner: "bull",
    recommendation: "BUY",
    confidence: 7,
    bull_score: 8,
    bear_score: 6,
    reasoning: "The bull case is better supported by current demand signals and the durability of the software moat; the bear's substitution thesis is real but multi-year, not imminent.",
    decisive_argument: "CUDA switching costs sustain pricing power through the next cycle.",
    key_factors: ["Demand visibility", "Moat durability", "Valuation risk acknowledged"],
  },
  transcript: [
    { round: 1, stance: "bull", confidence: 8, summary: "Demand vastly exceeds supply.",
      claims: ["Backlog visibility multiple quarters out", "Gross margins fund R&D lead"],
      rebuttals: [], evidence: ["~75% gross margin", "Data-center YoY +120%"] },
    { round: 1, stance: "bear", confidence: 6, summary: "Premium prices in perfection.",
      claims: ["~48x trailing P/E leaves no room for slips", "Custom silicon ramps"],
      rebuttals: ["Backlog can be cancelled in a digestion phase"], evidence: ["Hyperscaler TPU/Trainium roadmaps"] },
    { round: 2, stance: "bull", confidence: 8, summary: "Moat blunts substitution.",
      claims: ["CUDA migration costs are prohibitive"], rebuttals: ["Custom chips lack the software ecosystem"], evidence: ["Developer lock-in"] },
    { round: 2, stance: "bear", confidence: 6, summary: "Concentration is fragile.",
      claims: ["Few customers drive most revenue"], rebuttals: ["Margins compress if one hyperscaler in-sources"], evidence: ["Customer concentration disclosure"] },
  ],
};

export const mockCitations: Citation[] = [
  { ticker: "NVDA", company: "NVIDIA Corporation", form: "10-K", section: "Item 1A Risk Factors",
    accession: "0001045810-25-000023", filing_date: "2025-02-26",
    url: "https://www.sec.gov/Archives/edgar/data/1045810/000104581025000023/nvda-20250126.htm",
    snippet: "We are dependent on third-party foundries... export controls could materially affect demand...", score: 0.83 },
  { ticker: "NVDA", company: "NVIDIA Corporation", form: "10-Q", section: "Item 2 MD&A",
    accession: "0001045810-25-000119", filing_date: "2025-08-27",
    url: "https://www.sec.gov/Archives/edgar/data/1045810/000104581025000119/nvda-20250727.htm",
    snippet: "Data center revenue increased driven by demand for accelerated computing...", score: 0.79 },
];

export const mockEval: EvalReport = {
  run_id: "eval-demo01",
  created_at: new Date().toISOString(),
  n_samples: 24,
  overall_quality: 0.82,
  metric_averages: {
    faithfulness: 0.88, hallucination_rate: 0.11, retrieval_quality: 0.79,
    tool_usage_accuracy: 0.91, response_completeness: 0.84,
  },
  pass_rates: {
    faithfulness: 0.83, hallucination_rate: 0.88, retrieval_quality: 0.71,
    tool_usage_accuracy: 0.92, response_completeness: 0.79,
  },
  agent_breakdown: {
    research: { faithfulness: 0.9, retrieval_quality: 0.82, response_completeness: 0.86 },
    financial: { faithfulness: 0.86, tool_usage_accuracy: 0.94, response_completeness: 0.83 },
    risk: { faithfulness: 0.88, response_completeness: 0.81 },
  },
  failures: [
    { sample_id: "amd-fin-3", agent: "financial", metric: "retrieval_quality", score: 0.42, question: "Summarize AMD's cash flow.", reason: "precision=0.40, recall=0.50" },
    { sample_id: "tsla-risk-2", agent: "risk", metric: "faithfulness", score: 0.55, question: "Tesla key risks?", reason: "2/4 claims supported" },
    { sample_id: "msft-news-1", agent: "research", metric: "response_completeness", score: 0.50, question: "Microsoft growth drivers?", reason: "2/4 required points covered" },
  ],
};

export const mockPortfolio: Holding[] = [
  { ticker: "NVDA", name: "NVIDIA", weight: 0.22, recommendation: "BUY", conviction: 8, riskScore: 6, sector: "Technology" },
  { ticker: "AAPL", name: "Apple", weight: 0.18, recommendation: "HOLD", conviction: 6, riskScore: 4, sector: "Technology" },
  { ticker: "MSFT", name: "Microsoft", weight: 0.20, recommendation: "BUY", conviction: 7, riskScore: 3, sector: "Technology" },
  { ticker: "JNJ", name: "Johnson & Johnson", weight: 0.12, recommendation: "HOLD", conviction: 5, riskScore: 3, sector: "Healthcare" },
  { ticker: "XOM", name: "Exxon Mobil", weight: 0.10, recommendation: "SELL", conviction: 6, riskScore: 7, sector: "Energy" },
  { ticker: "JPM", name: "JPMorgan", weight: 0.18, recommendation: "BUY", conviction: 7, riskScore: 5, sector: "Financials" },
];

// A synthetic price series for the financial dashboard chart.
export const mockPriceSeries = Array.from({ length: 60 }, (_, i) => {
  const base = 120 + i * 1.6;
  const noise = Math.sin(i / 3) * 6 + Math.cos(i / 7) * 4;
  return { t: `D${i + 1}`, price: Number((base + noise).toFixed(2)), volume: Math.round(40 + Math.abs(noise) * 6) };
});
