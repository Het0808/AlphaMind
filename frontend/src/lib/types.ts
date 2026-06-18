// TypeScript mirrors of the AlphaMind backend Pydantic schemas.

export type Recommendation = "STRONG_BUY" | "BUY" | "HOLD" | "SELL" | "STRONG_SELL";
export type RiskLevel = "LOW" | "MODERATE" | "ELEVATED" | "HIGH";
export type Sentiment = "VERY_BULLISH" | "BULLISH" | "NEUTRAL" | "BEARISH" | "VERY_BEARISH";

export interface ResearchReport {
  company_name: string;
  sector: string;
  business_summary: string;
  moat: string;
  growth_drivers: string[];
  competitive_threats: string[];
  bull_case: string;
  bear_case: string;
  filing_citations: string[];
}

export interface FinancialReport {
  valuation_summary: string;
  profitability: string;
  balance_sheet: string;
  growth_trend: string;
  key_metrics: Record<string, number | string>;
  financial_health_score: number;
}

export interface NewsItem { headline: string; sentiment: Sentiment; relevance: string; }
export interface NewsReport {
  overall_sentiment: Sentiment;
  summary: string;
  catalysts: string[];
  notable_items: NewsItem[];
}

export interface RiskReport {
  overall_risk: RiskLevel;
  market_risk: string;
  financial_risk: string;
  business_risk: string;
  red_flags: string[];
  risk_score: number;
}

export interface InvestmentReport {
  ticker: string;
  company_name: string;
  horizon: string;
  recommendation: Recommendation;
  conviction: number;
  executive_summary: string;
  key_thesis: string[];
  key_risks: string[];
  research: ResearchReport;
  financials: FinancialReport;
  news: NewsReport;
  risk: RiskReport;
  generated_at: string;
  trace: string[];
}

// ── Financial data layer ──
export interface CompanyOverview {
  ticker: string; name: string; sector?: string; industry?: string;
  description?: string; exchange?: string; currency?: string; country?: string;
  website?: string; employees?: number;
}
export interface FinancialMetrics {
  ticker: string; price?: number | null; revenue?: number | null; net_income?: number | null;
  eps?: number | null; market_cap?: number | null; pe_ratio?: number | null;
  ebitda?: number | null; operating_cash_flow?: number | null; free_cash_flow?: number | null;
  enterprise_value?: number | null; roe?: number | null; roce?: number | null;
  fiscal_period?: string; currency?: string;
}
export interface FieldQuality {
  field: string; value: number | null; unit: string; currency?: string | null;
  sources: Record<string, number>; chosen_source?: string | null;
  agreement?: number | null; confidence: number; status: string; issues: string[];
}
export interface QualityReport {
  overall_confidence: number; providers: string[];
  field_quality: Record<string, FieldQuality>; validations: string[]; last_updated: string;
}
export interface FinancialSnapshot {
  ticker: string; overview: CompanyOverview; metrics: FinancialMetrics;
  providers_used: string[]; field_sources: Record<string, string>; warnings: string[];
  quality?: QualityReport | null;
}

// ── Debate ──
export interface DebateArgument {
  round: number; stance: "bull" | "bear"; claims: string[];
  rebuttals: string[]; evidence: string[]; confidence: number; summary: string;
}
export interface SideThesis {
  stance: "bull" | "bear"; thesis: string; key_points: string[];
  strongest_point: string; acknowledged_weaknesses: string[]; confidence: number;
}
export interface JudgeDecision {
  winner: "bull" | "bear" | "tie"; recommendation: Recommendation; confidence: number;
  bull_score: number; bear_score: number; reasoning: string;
  decisive_argument: string; key_factors: string[];
}
export interface DebateResult {
  ticker: string; company_name: string; rounds: number;
  bull_thesis: SideThesis; bear_thesis: SideThesis; judge: JudgeDecision;
  confidence: number; transcript: DebateArgument[];
}

// ── Citations (RAG) ──
export interface Citation {
  ticker: string; company?: string; form: string; section: string;
  accession: string; filing_date: string; url: string; snippet?: string; score?: number;
}

// ── Evaluation ──
export interface MetricScore {
  metric: string; score: number; passed: boolean; higher_is_better: boolean;
  skipped: boolean; detail: string;
}
export interface FailureCase {
  sample_id: string; agent?: string; metric: string; score: number; question: string; reason: string;
}
export interface EvalReport {
  run_id: string; created_at: string; n_samples: number; overall_quality: number;
  metric_averages: Record<string, number>; pass_rates: Record<string, number>;
  agent_breakdown: Record<string, Record<string, number>>;
  failures: FailureCase[];
}

// ── Portfolio (frontend-side model) ──
export interface Holding {
  ticker: string; name: string; weight: number; recommendation: Recommendation;
  conviction: number; riskScore: number; sector: string;
}
