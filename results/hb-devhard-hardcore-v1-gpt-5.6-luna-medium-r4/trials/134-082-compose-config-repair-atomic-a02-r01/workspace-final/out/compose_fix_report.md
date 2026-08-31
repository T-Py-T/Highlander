# Compose repair report

## Root cause

`compose.yaml` had drifted from `config/service-policy.yml`: it used the `latest` API image, the wrong host-port variable, `REDIS_DSN`, the `cache` service name, the `default` queue, `/tmp/data`, and the wrong volume target. It also lacked required condition-based dependencies and meaningful DB/Redis healthchecks, and the API healthcheck used `/status`.

The compose file now matches the policy: pinned images, `redis`, `critical` queue, `/data` mounted from `api-data`, required environment keys, health-based dependencies, and healthchecks for `/healthz`, `pg_isready`, and `redis-cli ping`. `.env.example` already matched the required defaults and was left unchanged.

## Validation

Final offline validation command run:

```bash
PYTHONPATH=/tmp/compose-validator-shim python3 tools/validate_compose.py
```

Result: `compose contract ok`

No containers were started and no images were pulled.
