# Checkout Incident Triage Notes

## Summary

Dependency path from user impact to root cause:

`checkout-web` user checkout submission failure (`401`) -> `payment-api` rejects `create_payment` because auth result is `invalid_issuer` -> `auth-gateway` rejects partner tokens after `AUTH-2026-0318` changed issuer/JWKS settings but left `allowed_issuers` effectively on `partner-v1`.

## Directly Observed Facts

- [`/workspace/in/topology.json`](/workspace/in/topology.json) shows `checkout-web` depends on `payment-api`, and `payment-api` depends on `auth-gateway`.
- [`/workspace/in/topology.json`](/workspace/in/topology.json) lists recent change `AUTH-2026-0318` on `auth-gateway` at `2026-03-22T14:05:00Z` with summary: issuer and JWKS cache namespace rotation for partner-token validation.
- [`/workspace/in/logs/auth-gateway.log`](/workspace/in/logs/auth-gateway.log) logs deployment of `AUTH-2026-0318` at `2026-03-22T14:05:12Z`, then a `jwks cache lookup miss namespace=partner-v2 fallback=partner-v1`, followed by `validation failed reason=issuer_not_allowed token_issuer=partner-v2 allowed_issuers=partner-v1`.
- [`/workspace/in/logs/payment-api.log`](/workspace/in/logs/payment-api.log) logs `token validation failed upstream=auth-gateway reason=issuer_not_allowed issuer=partner-v2` at `2026-03-22T14:08:59Z`, then `create_payment rejected ... auth_result=invalid_issuer` at `2026-03-22T14:09:04Z`.
- [`/workspace/in/logs/checkout-web.log`](/workspace/in/logs/checkout-web.log) logs `submit_order failed status=401 upstream=payment-api` at `2026-03-22T14:09:41Z` and `payment-api returned auth_failed invalid issuer` at `2026-03-22T14:10:03Z`.
- [`/workspace/in/metrics/service_metrics.csv`](/workspace/in/metrics/service_metrics.csv) shows a synchronized `401` spike at `2026-03-22T14:10:00Z`: `checkout-web=18.7%`, `payment-api=21.2%`, `auth-gateway=28.4%`.
- [`/workspace/in/logs/orders-db.log`](/workspace/in/logs/orders-db.log) reports `p95_query_ms=35 connections=64 errors=0` and explicitly says no failed checkout transaction for `req-8812` reached `orders-db`.

## Inferences

- The most likely primary fault is a partial or inconsistent rollout in `auth-gateway`: `AUTH-2026-0318` switched runtime traffic to `partner-v2` issuer/JWKS namespace, but validation policy still allowed only `partner-v1`.
- `payment-api` and `checkout-web` are impacted dependents, not originators, because their failures are temporally downstream of the auth-gateway validation errors and both logs point to `invalid_issuer`.
- `orders-db` and `cdn-edge` are red herrings for this incident. They show noise in the same window, but the failing checkout path is blocked before database use, and CDN recovery does not restore checkout success.

## Immediate Mitigation

- Roll back `AUTH-2026-0318`, or restore `partner-v2` in `auth-gateway` `allowed_issuers` and matching JWKS cache configuration.
- Clear or repopulate the `partner-v2` JWKS cache to stop fallback to `partner-v1`.
- Temporarily route partner-token validation through the last known-good issuer/JWKS config if rollback is slower than a targeted config fix.

## Verification Steps

- Send a known-good `partner-v2` token through `auth-gateway` and confirm no `issuer_not_allowed` or cache fallback logs are emitted.
- Retry the `payment-api` create-payment flow and confirm `auth_result=invalid_issuer` no longer appears.
- Monitor [`/workspace/in/metrics/service_metrics.csv`](/workspace/in/metrics/service_metrics.csv)-equivalent live metrics after mitigation: `auth-gateway`, `payment-api`, and `checkout-web` `401` rates should return near the `2026-03-22T14:00:00Z` baseline.
- Confirm checkout requests progress beyond auth and that requests begin reaching the order path again without database errors.
