Root cause: `compose.yaml` had drifted away from `config/service-policy.yml` during the incident. The stack used the wrong API image tag (`latest`), exposed the API with the wrong variable name and default port, renamed `redis` to `cache`, downgraded `depends_on` conditions from `service_healthy`, used the wrong Redis environment key and host, changed the queue from `critical` to `default`, changed the API data mount from `api-data:/data` to `/var/lib/composeapp`, and replaced the required healthchecks with non-compliant or missing checks.

Fix applied: restored the service names, image tags, dependency conditions, healthchecks, queue values, Redis URLs, API port mapping, and the `api-data` volume mount at `/data` so the file matches the local deployment contract. `.env.example` already matched the required defaults, so it was left unchanged.

Final validation command: `PYTHONPATH=. python3 tools/validate_compose.py`
