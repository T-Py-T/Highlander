# Compose Fix Report

## Root Cause

The compose file had been altered to use an unapproved API `latest` image, the wrong host port variable, `REDIS_DSN`, the `cache` service name, default queue and data directory values, short-form dependency declarations, an incorrect API volume target, and missing database and Redis healthchecks. These changes conflicted with `config/service-policy.yml` and the local validator contract.

The compose file now uses the policy image tags, `API_PORT`, `REDIS_URL`, the `critical` queue, `/data`, `redis`, healthy dependency conditions, meaningful healthchecks, and the `api-data:/data` named volume. `.env.example` already contained matching defaults and was not changed.

## Validation

Final validation command run offline:

```text
PYTHONPATH=/workspace python3 tools/validate_compose.py
```

Result: `compose contract ok`

The environment did not provide a `python` executable or PyYAML, so the unchanged validator was run with `python3` and a temporary local YAML compatibility shim. No images were pulled and no containers were started.
