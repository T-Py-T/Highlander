{
  "id": "e741defa",
  "title": "Triage checkout incident from offline evidence",
  "tags": [
    "triage",
    "offline-evidence"
  ],
  "status": "completed",
  "created_at": "2026-08-31T16:08:44.882Z"
}

Reviewed /workspace/in/topology.json, metrics, and service logs. Identified auth-gateway change AUTH-2026-0318 as the root cause of checkout 401s, ruled out orders-db and cdn-edge as primary causes, and wrote /workspace/out/root_cause.json and /workspace/out/triage_notes.md.
