# Checkout Incident Triage Notes

## Summary

Directly observed facts:

- `/workspace/in/topology.json` shows the user-impact path `checkout-web -> payment-api -> auth-gateway`.
- `/workspace/in/logs/checkout-web.log` shows checkout submission failures returning `401` from `payment-api` and records `auth_failed invalid issuer`.
- `/workspace/in/logs/payment-api.log` shows `token validation failed upstream=auth-gateway` with `reason=issuer_not_allowed issuer=partner-v2`, followed by `auth_result=invalid_issuer`.
- `/workspace/in/logs/auth-gateway.log` shows deployment of `AUTH-2026-0318`, then a `jwks cache lookup miss`, fallback from `partner-v2` to `partner-v1`, and validation failure because `token_issuer=partner-v2` while `allowed_issuers=partner-v1`.
- `/workspace/in/metrics/service_metrics.csv` shows synchronized 401-rate increases at `2026-03-22T14:10:00Z` on `checkout-web`, `payment-api`, and `auth-gateway`.

Inference:

- The production checkout impact was caused by an auth-gateway configuration regression introduced by `AUTH-2026-0318`, which changed partner-token issuer/JWKS settings in a way that rejected valid `partner-v2` tokens. That failure propagated upstream through `payment-api` and blocked checkout requests at `checkout-web`.

## Dependency Path

Directly observed facts:

1. User impact appears at `checkout-web` as failed `submit_order` requests with upstream `401` responses in `/workspace/in/logs/checkout-web.log`.
2. The next dependency on the request path is `payment-api`, per `/workspace/in/topology.json`.
3. `payment-api` reports the request is rejected during token validation by `auth-gateway`, not during database work, in `/workspace/in/logs/payment-api.log`.
4. `auth-gateway` logs the concrete validation mismatch immediately after deployment of `AUTH-2026-0318` in `/workspace/in/logs/auth-gateway.log`.

Inference:

1. The shortest causal chain is `checkout-web` user failure -> `payment-api` auth rejection -> `auth-gateway` issuer/JWKS misconfiguration from `AUTH-2026-0318`.

## Red Herrings Excluded

Directly observed facts:

- `/workspace/in/metrics/service_metrics.csv` shows `orders-db` CPU at `86%`, but still `http_5xx_rate=0.0`, `http_401_rate=0.0`, and `p95_ms=35`.
- `/workspace/in/logs/orders-db.log` reports `errors=0` and states no failed checkout transaction reached `orders-db` for `req-8812`.
- `/workspace/in/metrics/service_metrics.csv` shows `cdn-edge` 5xxs, but the note says they were isolated to static assets.
- `/workspace/in/logs/checkout-web.log` states static assets served normally after retry while the checkout flow remained blocked.

Inference:

- `orders-db` maintenance load and `cdn-edge` image errors are misleading concurrent signals, but neither is on the primary failure path for the checkout rejection.

## Immediate Mitigation

1. Revert `AUTH-2026-0318`, or restore `auth-gateway` configuration so `allowed_issuers` and JWKS namespace both support `partner-v2`.
2. Flush or rebuild the incorrect JWKS cache namespace if rollback alone does not clear the `partner-v1` fallback behavior.
3. Hold further auth-gateway rollouts until issuer/JWKS compatibility checks pass.

## Verification Steps

1. Confirm in auth-gateway logs that `token_issuer=partner-v2` is accepted and that cache lookups hit the intended `partner-v2` namespace without fallback.
2. Replay or retest checkout and verify requests move past `payment-api` auth gating into downstream order processing.
3. Check that 401 rates on `checkout-web`, `payment-api`, and `auth-gateway` return near the `2026-03-22T14:00:00Z` baseline from `/workspace/in/metrics/service_metrics.csv`.
4. Confirm no new evidence appears tying failed requests to `orders-db` or `cdn-edge`.
