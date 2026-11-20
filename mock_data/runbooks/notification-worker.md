# Runbook: notification-worker

## Service Overview
`notification-worker` consumes transactional events from Kafka and dispatches customer emails, push notifications, and SMS messages.

## Operational Dependencies
- Kafka broker cluster (`notifications-queue`)
- Third-party email provider (SendGrid)
- SMS Provider (Twilio)

## Common Failure Modes & Diagnostics
1. **Kafka Consumer Lag Spike**
   - *Check*: Consumer offset lag in Grafana.
   - *Action*: Increase worker pod replica count if lag exceeds 10,000 messages.

2. **SendGrid Rate Limiting (HTTP 429)**
   - *Check*: Outbound dispatch logs for `rate_limit_exceeded`.
   - *Action*: Enable backoff buffer in worker configuration; batch email delivery.

3. **Dead Letter Queue (DLQ) Accumulation**
   - *Check*: Bad recipient address or malformed payload rejections.
   - *Action*: Inspect payload schema compatibility with producer services.

## Escalation Path
- Primary On-Call: `#customer-comms-oncall`
- Incident Severity: Delays in delivery are typically `MEDIUM` unless critical transactional OTP codes are delayed.
