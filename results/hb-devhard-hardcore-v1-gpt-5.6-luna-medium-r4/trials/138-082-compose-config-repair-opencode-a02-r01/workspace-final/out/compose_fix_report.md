# Compose Configuration Repair

## Root Cause

The incident edit broke the local deployment contract by using the `latest` API image, mapping `WEB_PORT`, renaming the Redis environment variable and service to `cache`, using the wrong queue and API data directory, mounting the named volume at the wrong target, omitting required service healthchecks, and weakening dependency conditions to `service_started`.

The compose file now uses the policy-pinned images, `redis` service, `critical` queue, required environment variables, `/data` volume mount, meaningful healthchecks, and `service_healthy` dependencies. `.env.example` already documented the matching defaults.

## Validation

Final validation command:

```bash
PYTHONPATH=/workspace python3 tools/validate_compose.py
```

Result: `compose contract ok`
