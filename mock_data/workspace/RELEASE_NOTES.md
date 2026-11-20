# Release Notes

## Version 2.14.0 (Current Release Candidate)
- **payments-api** (`c4a9f12`):
  - Performance optimization: Reduce default PostgreSQL database connection pool size per replica from 30 to 5 to conserve RDS connection limits during off-peak scaling.
  - Added tracing headers to outgoing webhook events.
- **notification-worker** (`a1b8c3d`):
  - Updated SendGrid batch sending SDK to v7.2.
  - Implemented jittered exponential backoff on dispatch failures.
- **auth-service** (`f9e8d7c`):
  - Minor maintenance: rotated internal HMAC signing token keys.

---

## Version 2.13.0 (Previous Release)
- **auth-service** (`8c2d1e0`):
  - Implemented PKCE support for public OAuth clients.
- **payments-api** (`5b4a3c2`):
  - Added support for 3D Secure 2.0 biometric challenge flows.
- **notification-worker** (`7e6d5c4`):
  - Added SMS template validation utility.
