# Production checkout incident triage

## Scope
This triage is based only on offline fixture evidence. No live systems or external APIs were used.

## Dependency path from user impact to root cause
User impact flowed through this path:

checkout-web -> payment-api -> auth-gateway

Directly observed facts:
- `/workspace/in/topology.json` shows `checkout-web` depends on `payment-api`, and `payment-api` depends on `auth-gateway`.
- `/workspace/in/logs/checkout-web.log` shows checkout submission failures with `status=401 upstream=payment-api` and `invalid issuer`.
- `/workspace/in/logs/payment-api.log` shows payment creation was rejected because token validation failed at `upstream=auth-gateway` with `reason=issuer_not_allowed`.
- `/workspace/in/logs/auth-gateway.log` shows change `AUTH-2026-0318` was deployed, followed by `jwks cache lookup miss`, fallback to `partner-v1`, and `validation failed reason=issuer_not_allowed token_issuer=partner-v2 allowed_issuers=partner-v1`.
- `/workspace/in/metrics/service_metrics.csv` shows a coordinated rise in 401s at `auth-gateway` (28.4%), `payment-api` (21.2%), and `checkout-web` (18.7%) at 2026-03-22T14:10:00Z.

Inference:
- The most likely root cause is that `AUTH-2026-0318` introduced or exposed an auth-gateway configuration mismatch: partner-v2 tokens/JWKS namespace were deployed, but the effective allowed issuer set still pointed at partner-v1 during validation. That mismatch propagated upstream as payment authorization failures and then checkout failures.

## Why this is the primary cause
Directly observed facts:
- The error chain is temporally aligned: auth-gateway change at 14:05, auth validation errors at 14:08, payment rejection at 14:09, checkout failure at 14:09-14:10.
- The failure mode is consistent across all layers: `issuer_not_allowed` -> `invalid_issuer` -> checkout `401`.
- `auth-gateway.log` explicitly suggests rollback/fix of `AUTH-2026-0318` as a candidate.

Inference:
- Because the observed failure begins at the lowest shared dependency in the checkout auth path and propagates upward unchanged, auth-gateway is the best-supported root cause rather than a symptom.

## Excluded red herrings
Directly observed facts:
- `/workspace/in/logs/orders-db.log` shows `cpu_high cpu=86 pct maintenance=vacuum`, but also `p95_query_ms=35`, `errors=0`, and `no failed checkout transaction reached orders-db for request_id=req-8812`.
- `/workspace/in/logs/payment-api.log` states `order-db dependency not used before auth gate for failing requests`.
- `/workspace/in/metrics/service_metrics.csv` shows `cdn-edge` had `4.8` 5xx rate isolated to images.
- `/workspace/in/logs/checkout-web.log` says `static assets served normally after retry; user checkout flow still blocked`.

Inference:
- orders-db CPU and CDN image 5xx are misleading concurrent signals, but neither sits on the observed failing auth path that caused checkout submission rejection.

## Immediate mitigation
1. Revert `AUTH-2026-0318` on `auth-gateway`, or restore `allowed_issuers` and JWKS cache/config so `partner-v2` tokens are accepted.
2. Flush or rebuild the stale JWKS cache namespace if rollback alone does not remove fallback behavior to `partner-v1`.
3. If a full revert is risky, apply the smallest safe config-only correction: align `allowed_issuers`, token issuer, and JWKS namespace to the same partner version.

## Verification steps
1. Check post-mitigation auth-gateway logs for disappearance of:
   - `jwks cache lookup miss namespace=partner-v2 fallback=partner-v1`
   - `validation failed reason=issuer_not_allowed`
2. Check payment-api logs for disappearance of:
   - `token validation failed upstream=auth-gateway`
   - `auth_result=invalid_issuer`
3. Check checkout-web logs for successful checkout submissions replacing `status=401 upstream=payment-api`.
4. Confirm service metrics return toward baseline, especially 401 rates on:
   - `auth-gateway`
   - `payment-api`
   - `checkout-web`
5. Verify a representative checkout request now traverses past auth and reaches downstream order processing if expected.

## Fixture files cited
- `/workspace/in/topology.json`
- `/workspace/in/metrics/service_metrics.csv`
- `/workspace/in/logs/checkout-web.log`
- `/workspace/in/logs/payment-api.log`
- `/workspace/in/logs/auth-gateway.log`
- `/workspace/in/logs/orders-db.log`
