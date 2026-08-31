# Checkout Incident Triage Notes

## Summary

Directly observed fact: the user-facing failure starts at `checkout-web`, which returns `submit_order failed status=401 upstream=payment-api` in `/workspace/in/logs/checkout-web.log`.

Directly observed fact: `payment-api` rejects the same request because token validation from `auth-gateway` returns `issuer_not_allowed` / `invalid_issuer` in `/workspace/in/logs/payment-api.log`.

Directly observed fact: `auth-gateway` deployed `AUTH-2026-0318`, then logged a `jwks cache lookup miss`, followed by `validation failed` because `token_issuer=partner-v2` while `allowed_issuers=partner-v1` in `/workspace/in/logs/auth-gateway.log`.

Inference: the production checkout incident was caused by an auth-gateway configuration regression introduced by `AUTH-2026-0318`, not by the database or CDN signals.

## Dependency Path

Directly observed fact: `/workspace/in/topology.json` defines the user path as `checkout-web -> payment-api -> auth-gateway`.

Directly observed fact: `/workspace/in/metrics/service_metrics.csv` shows the correlated impact window at `2026-03-22T14:10:00Z`:
- `checkout-web` `http_401_rate=18.7`
- `payment-api` `http_401_rate=21.2`
- `auth-gateway` `http_401_rate=28.4`

Inference: the rising 401s align along the dependency chain, so the deepest shared failing dependency is the most probable root cause.

## Root Cause

Directly observed fact: `/workspace/in/topology.json` lists `AUTH-2026-0318` on `auth-gateway` as the recent change touching issuer and JWKS cache namespace handling.

Directly observed fact: `/workspace/in/logs/auth-gateway.log` shows:
- deployed change `AUTH-2026-0318`
- `jwks_namespace=partner-v2 issuer=partner-v2`
- later fallback to `partner-v1`
- validation failure because `allowed_issuers=partner-v1`

Inference: the rollout changed the active token issuer/namespace to `partner-v2` without updating the accepted issuer list consistently, producing invalid issuer decisions that blocked payment authorization and therefore checkout submission.

## Excluded Red Herrings

Directly observed fact: `/workspace/in/logs/orders-db.log` reports `cpu_high` during vacuum, but also `p95_query_ms=35`, `errors=0`, and `no failed checkout transaction reached orders-db for request_id=req-8812`.

Inference: `orders-db` is noisy but not causal, because the failing requests never reached it and the latency/error profile stayed normal.

Directly observed fact: `/workspace/in/metrics/service_metrics.csv` shows `cdn-edge` `http_5xx_rate=4.8`, and `/workspace/in/logs/checkout-web.log` says static assets were normal after retry while checkout remained blocked.

Inference: CDN image failures were concurrent but isolated; they do not explain the checkout 401 path.

## Immediate Mitigation

1. Revert `AUTH-2026-0318` or restore `allowed_issuers` to include `partner-v2` on `auth-gateway`.
2. Flush or repopulate the JWKS cache namespace so `partner-v2` tokens do not fall back to `partner-v1`.
3. Monitor `auth-gateway`, `payment-api`, and `checkout-web` 401 rates during rollback to confirm the dependency chain clears from the root outward.

## Verification

1. Run a checkout using a partner token that previously failed and confirm `checkout-web` no longer returns 401 from `payment-api`.
2. Confirm `payment-api` stops logging `auth_result=invalid_issuer`.
3. Confirm `auth-gateway` no longer logs `issuer_not_allowed` or `fallback=partner-v1` for `partner-v2` tokens.
4. Recheck service metrics and verify the 401 rates on all three services return near the `2026-03-22T14:00:00Z` baseline from `/workspace/in/metrics/service_metrics.csv`.
