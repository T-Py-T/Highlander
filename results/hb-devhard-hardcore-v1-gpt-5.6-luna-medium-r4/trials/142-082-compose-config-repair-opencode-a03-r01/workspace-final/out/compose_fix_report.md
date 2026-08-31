# Compose Repair Report

## Root Cause

`compose.yaml` had drifted from `config/service-policy.yml`: the API used a `latest` image and wrong port, Redis environment key and hostname were incorrect, the queue and data path were wrong, the data volume target was wrong, dependencies used `service_started` and the `cache` name, and required API, database, and Redis healthchecks were missing or pointed at the wrong command/path.

The existing `.env.example` already documented the required API port, Redis URL, critical queue, and `/data` path, so it was left unchanged.

## Validation

Final validation command run offline:

```text
PYTHONPATH=/workspace python3 tools/validate_compose.py
```

Result: `compose contract ok`

The environment did not provide `python` or PyYAML. The validator itself was unchanged; a temporary local YAML compatibility shim supplied the missing offline import and was removed after validation. No images were pulled and no containers were started.
