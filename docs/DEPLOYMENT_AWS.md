# AlphaMind — AWS Deployment Architecture

Production reference architecture for deploying AlphaMind on AWS using containers
(ECS Fargate) behind an Application Load Balancer, with managed data stores.

## Architecture

```
                                   ┌────────────────┐
                Users ───────────► │   Route 53     │  DNS
                                   └───────┬────────┘
                                           ▼
                                   ┌────────────────┐
                                   │   AWS WAF      │  OWASP rules, IP allow/deny
                                   └───────┬────────┘
                                           ▼
                              ┌────────────────────────┐
                              │  Application Load        │  TLS (ACM cert)
                              │  Balancer (HTTPS :443)   │  health checks → /health
                              └───────┬───────────┬──────┘
                       /api/*, /v1/* │           │ /  (static)
                                     ▼           ▼
                    ┌──────────────────────┐  ┌──────────────────────┐
                    │ ECS Fargate Service  │  │ ECS Fargate Service  │
                    │  alphamind-api       │  │  alphamind-frontend  │
                    │  (gunicorn+uvicorn)  │  │  (Next.js)           │
                    │  autoscale 2..N      │  │  autoscale 2..N      │
                    └───┬───────┬──────┬───┘  └──────────────────────┘
            ┌───────────┘       │      └──────────────┐
            ▼                   ▼                     ▼
   ┌─────────────────┐  ┌──────────────┐    ┌──────────────────┐
   │ RDS PostgreSQL  │  │ ElastiCache  │    │ Qdrant on ECS    │
   │ (Multi-AZ)      │  │ Redis        │    │ Fargate + EFS     │
   │ memory store    │  │ rate limits  │    │ (or Qdrant Cloud) │
   └─────────────────┘  │ + cache      │    └──────────────────┘
                        └──────────────┘
   ┌──────────────────────────────────────────────────────────────┐
   │ Cross-cutting AWS services                                     │
   │  • ECR              container images (api, frontend)           │
   │  • Secrets Manager  OPENAI_API_KEY, API_KEYS, DB creds, FMP    │
   │  • CloudWatch       logs (JSON), metrics, alarms, dashboards   │
   │  • S3               eval reports, filing cache, artifacts      │
   │  • CloudWatch + ADOT / Prometheus  scrape /metrics             │
   └──────────────────────────────────────────────────────────────┘
```

## Components

| Concern | AWS service | Notes |
|--------|-------------|-------|
| DNS | Route 53 | `app.alphamind.io`, `api.alphamind.io` |
| Edge security | AWS WAF | Managed OWASP rule set; tied to the ALB |
| TLS | ACM | Auto-renewing cert on the ALB |
| Load balancing | ALB | Path routing; `/health` health checks; access logs → S3 |
| Compute | ECS Fargate | `alphamind-api` (gunicorn + 3 uvicorn workers) and `alphamind-frontend`; serverless containers, no EC2 to manage |
| Images | ECR | Pushed by GitHub Actions (`docker-publish.yml`) |
| Relational | RDS PostgreSQL (Multi-AZ) | Persistent memory (users/companies/research/conversations) |
| Cache / limits | ElastiCache Redis | Distributed rate limiting + response/tool caching |
| Vector DB | Qdrant on Fargate + EFS, or Qdrant Cloud | RAG filing embeddings |
| Secrets | Secrets Manager | Injected as task env; never baked into images |
| Logs | CloudWatch Logs | `LOG_JSON=true` → structured JSON, queryable in Logs Insights |
| Metrics | CloudWatch + Prometheus/ADOT | Scrape `/metrics`; alarms on p95 latency, 5xx rate, 429 rate |
| Object storage | S3 | Eval reports, filing cache, ALB/WAF logs |

## Scaling & resilience
- **Horizontal autoscaling** on ECS by CPU/memory and ALB requests-per-target.
- **Multi-AZ** for RDS and across ≥2 AZs for ECS tasks.
- **Stateless API** — all state in RDS/Redis/Qdrant, so any task can serve any request.
- **Rate limiting** moves from in-process (single task) to **Redis-backed** (shared) in production — set `REDIS_URL`.
- **Health/readiness**: ALB → `/health`; deployment gates on `/ready`.

## Security
- TLS everywhere (ACM); HTTP→HTTPS redirect at the ALB.
- **Auth**: `AUTH_ENABLED=true` + `API_KEYS` from Secrets Manager (rotate regularly). Front with API Gateway/Cognito for end-user JWTs if needed.
- Private subnets for ECS/RDS/Redis/Qdrant; only the ALB is internet-facing. Security groups least-privilege.
- WAF rate-based rules as a second layer beyond app rate limiting.
- Secrets only via Secrets Manager; images run as a **non-root** user (see `Dockerfile`).

## CI/CD flow
```
GitHub push/tag
   └─► Actions: ci.yml         (ruff + pytest + frontend build)
   └─► Actions: docker-publish (build → push images to GHCR/ECR)
   └─► Actions: codeql.yml     (SAST)
        └─► (CD) deploy: aws ecs update-service --force-new-deployment
                         rolling update with ALB health checks + circuit breaker
```
Promote images by tag (`v1.2.3`) across `staging` → `production` accounts/clusters.
`GIT_SHA` is baked in as a build-arg and surfaced at `GET /version`.

## Observability runbook
- **Dashboards**: request rate, p50/p95/p99 latency, 5xx & 429 rates, per-endpoint volume (from `alphamind_http_*` metrics).
- **Alarms**: p95 > 2s (5m), 5xx > 2%, 429 > 10%, RDS CPU > 80%, ECS task restarts.
- **Tracing**: enable LangSmith (`LANGCHAIN_TRACING_V2=true`) for agent-level traces; correlate with `X-Request-ID` in CloudWatch.
