# T002 — Reject non-canonical Linewatch alarm IDs

## Problem

Linewatch currently accepts an alarm whose `id` has leading or trailing whitespace, but the GET route trims its path ID before lookup. A successful POST can therefore create an alarm that cannot be retrieved consistently.

## Required behavior

Adopt one explicit identity rule: alarm IDs are already canonical and must not contain leading or trailing whitespace.

- `Service.Raise` must reject an alarm when `ID != strings.TrimSpace(ID)` or the trimmed ID is empty.
- `Service.Get` must apply the same rule rather than silently canonicalizing the requested ID.
- `POST /v1/alarms` must return HTTP 400 with the stable code `invalid_alarm` for a padded ID.
- `GET /v1/alarms/{id}` must return HTTP 400 with the stable code `invalid_id` for a URL-encoded padded ID.
- Existing valid alarm creation, retrieval, duplicate detection, and error codes must continue to work.
- Add regression tests at the domain and HTTP interfaces.

## Boundaries

- Modify only `internal/alarm/` and `internal/httpapi/`.
- Do not change route names, JSON field names, storage technology, module path, CI, or repository instructions.
- Do not commit, push, open a PR, or contact an upstream repository. Highlander captures the raw patch after the Trial.
- Do not read files outside the disposable Arena.

## Validation

Run and report:

```text
go test ./...
go test -race ./...
go vet ./...
```

Review the final diff for scope, stable error behavior, and regression coverage.
