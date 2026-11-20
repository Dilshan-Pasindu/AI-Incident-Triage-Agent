# Runbook: auth-service

## Service Overview
`auth-service` handles user authentication, session validation, OAuth2 integrations, and JWT issuance.

## Operational Dependencies
- PostgreSQL (User credentials & tokens)
- Redis cluster (Session caches and rate-limiting counters)

## Common Failure Modes & Diagnostics
1. **Elevated Token Verification Latency (>200ms)**
   - *Check*: Redis connection count and cache eviction metrics.
   - *Action*: Scale Redis replicas if memory pressure exceeds 85%.

2. **JWT Signature Failures**
   - *Check*: KMS key rotation logs.
   - *Action*: Verify public key distribution sync across consumer microservices.

3. **Database Connection Saturation**
   - *Check*: Connection pool exhaustion in auth pod logs.
   - *Action*: Inspect slow queries on the `user_sessions` table.

## Escalation Path
- Primary On-Call: `#auth-team-oncall`
- Escalation Lead: Senior Security Architect (`@alex.m`)
- Incident Severity: If token issuance fails globally, escalate immediately to `SEV-1`.
