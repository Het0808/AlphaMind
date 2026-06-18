# AlphaMind — Frontend

A professional research terminal for AlphaMind, styled after a **Bloomberg
Terminal × OpenAI** aesthetic: dark, dense, data-forward, with a faint terminal
grid and tabular-numeric data.

**Stack:** Next.js 14 (App Router) · TypeScript · Tailwind CSS · shadcn-style
components · Recharts · lucide-react.

## Pages

| Route | Page | Highlights |
|-------|------|-----------|
| `/research` | **Research Workspace** | Run the pipeline; thesis, conviction, risk, agent thoughts, citations |
| `/company` | **Company Analysis** | Fundamentals, business/moat, Bull/Bear/Judge debate, citations |
| `/reasoning` | **Agent Reasoning Viewer** | Reasoning timeline, live agent trace, debate history |
| `/financials` | **Financial Dashboard** | Price/area chart, income & cash-flow bars, risk radar, provenance |
| `/portfolio` | **Portfolio Advisor** | Holdings table, weighted conviction/risk, sector allocation |
| `/evaluation` | **Evaluation Dashboard** | Metric scores, agent performance, failure analysis |

## Displays
Agent thoughts (terminal trace) · debate history (round-by-round) · SEC citations
(with accession + filing date + link) · financial charts · risk scores (radial
gauge + radar) · confidence metrics (segmented meters).

## Run

```bash
cd frontend
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL, or leave unset for demo data
npm run dev                        # http://localhost:3000
```

The UI ships with realistic **mock data** and a graceful API client: with no
`NEXT_PUBLIC_API_URL` (or if the backend is unreachable) every page renders on
mock data and the top bar shows a **Demo data** badge. Point it at the FastAPI
backend (`http://localhost:8000`) to go live.

## Backend wiring
`src/lib/api.ts` calls the FastAPI endpoints (`/analyze`, `/debate`,
`/filings/search`, …) and falls back to `src/lib/mock.ts`. Types in
`src/lib/types.ts` mirror the backend Pydantic schemas.
