# Mandatory Pre-Release Verification Checklist

All release candidates must satisfy the following four criteria before production deployment.

## Criteria

1. **Telemetry Stability (No Error Spikes)**
   - The service must exhibit zero `ERROR` or `FATAL` severity spikes within the last 24 hours.
   - Error rates must not exceed 0.05% of total request volume.

2. **Documentation & Release Notes**
   - A valid entry must exist in `RELEASE_NOTES.md` corresponding to the release candidate version/commit.
   - Breaking API changes and dependency updates must be explicitly documented.

3. **Configuration & Resource Review**
   - `service-config.yaml` must be reviewed and approved by the infrastructure team.
   - Resource allocations (CPU, memory, database connection pool size) must match traffic capacity targets.

4. **Rollback State Clearance**
   - The service must not have any active, unverified, or unresolved rollbacks in `deployments.json`.
   - Any prior rollback incident within 48 hours must have an attached root-cause analysis (RCA) and resolution ticket.
