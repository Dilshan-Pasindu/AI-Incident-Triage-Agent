# Runbook: payments-api

## Service Overview
`payments-api` processes transactions, checkout flows, and payment gateway webhooks. It is a Tier-0 mission-critical service.

## Operational Dependencies
- Primary PostgreSQL transactional DB (`payments_db`)
- External gateways: Stripe, Adyen
- Kafka event bus (`payment-events` topic)

## Common Failure Modes & Diagnostics

### 1. Database Connection Pool Exhaustion (`DB connection timeout after 5000ms`)
- **Symptoms**:
  - Spike in HTTP 500 responses on `/v1/charges` and `/v1/refunds`.
  - Log entries containing `DB connection timeout after 5000ms` and `connection pool exhausted`.
- **Immediate Mitigation**:
  1. Inspect recent deployment history (`get_deployment_history`).
  2. If a recent deployment adjusted DB pool configurations (e.g., commit `db-pool-reduction`), rollback immediately.
  3. Increase pool configuration in `service-config.yaml` from degraded value back to at least 25 connections per replica.
  4. Restart pods gradually to purge hung transactions.

### 2. Upstream Gateway Degradation
- **Symptoms**: Timeouts communicating with Stripe/Adyen API endpoints.
- **Action**: Check public gateway status pages and route to secondary provider if outage exceeds 5 minutes.

## Escalation Path
- Primary On-Call: `#payments-oncall`
- Escalation Lead: Lead Financial Systems Engineer (`@sarah.k`)
- Incident Severity:
  - Database pool exhaustion / inability to accept charges $\rightarrow$ `CRITICAL` (SEV-1).
  - Open incident ticket immediately with detailed timeline, affected commits, and rollback recommendations.
