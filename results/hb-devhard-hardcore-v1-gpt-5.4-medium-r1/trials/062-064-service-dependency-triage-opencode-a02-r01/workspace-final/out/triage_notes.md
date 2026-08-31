# Checkout Incident Triage Notes

## Summary

Dependency path from user impact to root cause:

`checkout-web` user submits checkout -> `payment-api` validates payment auth -> `auth-gateway` rejects partner token issuer -> `payment-api` returns 401 -> `checkout-web` checkout flow fails.

## Directly Observed Facts

- `/workspace/in/topology.json` shows `checkout-web` depends on `payment-api`, and `payment-api` depends on `auth-gateway`.
- `/workspace/in/topology.json` lists recent change `AUTH-2026-0318` on `auth-gateway` at `2026-03-22T14:05:00Z` with summary `rotated issuer and JWKS cache namespace for partner-token validation`.
- `/workspace/in/logs/auth-gateway.log` shows `AUTH-2026-0318` deployed, then a `jwks cache lookup miss`, then `validation failed reason=issuer_not_allowed token_issuer=partner-v2 allowed_issuers=partner-v1`.
- `/workspace/in/logs/payment-api.log` shows `token validation failed upstream=auth-gateway reason=issuer_not_allowed issuer=partner-v2` and then `create_payment rejected ... auth_result=invalid_issuer`.
- `/workspace/in/logs/checkout-web.log` shows `submit_order failed status=401 upstream=payment-api` and `payment-api returned auth_failed invalid issuer`.
- `/workspace/in/metrics/service_metrics.csv` shows concurrent 401 spikes at `14:10:00Z` on `checkout-web`, `payment-api`, and `auth-gateway`.
- `/workspace/in/logs/orders-db.log` shows `p95_query_ms=35`, `errors=0`, and `no failed checkout transaction reached orders-db for request_id=req-8812`.

## Inferences

- The primary root cause is `auth-gateway`, not `checkout-web` or `payment-api`, because the downstream services report upstream auth rejection and the first concrete validation failure is logged inside `auth-gateway`.
- The most likely bad change is `AUTH-2026-0318`, because it immediately precedes the incident window and its stated scope matches the observed issuer/JWKS mismatch.
- `orders-db` is not the checkout blocker, because the failure occurs before the orders path is reached.
- `cdn-edge` is not the checkout blocker, because the observed impact is authorization failure during submit, not persistent asset unavailability.

## Root Cause Statement

`auth-gateway` change `AUTH-2026-0318` appears to have rotated the issuer/JWKS namespace to `partner-v2` without updating `allowed_issuers` consistently. That left validation falling back to `partner-v1`, producing `issuer_not_allowed` errors for `partner-v2` tokens and causing `payment-api` and then `checkout-web` to reject checkout requests with 401s.

## Misleading Signals Excluded

- `orders-db` CPU spike: directly observed, but query latency stayed normal and no failing checkout reached the DB.
- `cdn-edge` image 5xx: directly observed, but isolated to static assets and explicitly not the reason the checkout submit path remained blocked.

## Immediate Mitigation

1. Revert `AUTH-2026-0318`, or restore `auth-gateway` configuration so `allowed_issuers` includes `partner-v2` and matches the active JWKS namespace.
2. Refresh or clear the JWKS cache after the config rollback/fix to stop fallback to `partner-v1`.
3. Monitor `checkout-web`, `payment-api`, and `auth-gateway` for disappearance of `invalid issuer` and `issuer_not_allowed` errors.

## Verification Steps

1. Confirm `auth-gateway` no longer logs `validation failed reason=issuer_not_allowed` for `partner-v2` tokens.
2. Confirm `payment-api` stops logging `auth_result=invalid_issuer` and payment creation requests succeed.
3. Confirm `checkout-web` no longer returns `status=401 upstream=payment-api` for checkout submit requests.
4. Check that 401 rates in `/workspace/in/metrics/service_metrics.csv` equivalent live dashboards return near baseline for `checkout-web`, `payment-api`, and `auth-gateway`.
5. Run a partner-token checkout smoke test that exercises the exact dependency chain `checkout-web -> payment-api -> auth-gateway`.
