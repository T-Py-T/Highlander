# Compose configuration repair report

## Root cause

`compose.yaml` had drifted from `config/service-policy.yml` in several contract-critical ways:

- The API image used the forbidden `latest` tag instead of `1.4.2`.
- The API published `${WEB_PORT:-8000}` rather than `${API_PORT:-8080}:8000`.
- The API exposed `REDIS_DSN` instead of the required `REDIS_URL`, pointed its default URL at the old `cache` service, and used the wrong `/status` health endpoint.
- The API used `/tmp/data` and mounted the named volume at `/var/lib/composeapp` instead of mounting `api-data` at `/data`.
- The service was named `cache` instead of `redis`.
- API and worker dependencies were list-style or used `service_started`, rather than conditional `service_healthy` dependencies on `db` and `redis`.
- The API and worker queue was `default` instead of the policy-required `critical`.
- Database and Redis healthchecks were absent.

The compose file was repaired to restore the policy image tags, service names, required environment variables, healthchecks, health-gated dependencies, queue name, API port, and `/data` volume mount. `.env.example` was already consistent with the required defaults (`API_PORT=8080`, Redis at `redis://redis:6379/0`, queue `critical`, and `APP_DATA_DIR=/data`), so it was not changed.

## Validation

Network access and image/container execution were intentionally not used. The system Python did not have PyYAML installed, and `python` is unavailable in this environment; therefore the unchanged validator was run offline with a temporary YAML shim:

```text
PYTHONPATH=/tmp python3 tools/validate_compose.py
```

Result:

```text
compose contract ok
```
