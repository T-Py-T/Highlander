# Checkout incident triage

## Dependency path
User impact starts at `checkout-web`, which depends on `payment-api`, which depends on `auth-gateway` for token validation (`in/topology.json`). The failing path is:

`checkout-web` -> `payment-api` -> `auth-gateway`

`orders-db` is downstream of `orders-api`, not the failing payment-auth path, and the evidence shows the failing request never reached the DB.

## Directly observed facts
- `in/topology.json` shows `checkout-web` depends on `payment-api`, and `payment-api` depends on `auth-gateway`. The same file lists recent change `AUTH-2026-0318` on `auth-gateway`, described as rotating the issuer and JWKS cache namespace for partner-token validation.
- `in/logs/auth-gateway.log` shows `AUTH-2026-0318` deployed at `2026-03-22T14:05:12Z`, then a `jwks cache lookup miss` for `partner-v2`, fallback to `partner-v1`, and `validation failed reason=issuer_not_allowed token_issuer=partner-v2 allowed_issuers=partner-v1`.
- `in/logs/payment-api.log` shows `create_payment rejected` with `auth_result=invalid_issuer`, and explicitly states `order-db dependency not used before auth gate for failing requests`.
- `in/logs/checkout-web.log` shows `submit_order failed status=401 upstream=payment-api` and `payment-api returned auth_failed invalid issuer`.
- `in/metrics/service_metrics.csv` shows the incident window at `2026-03-22T14:10:00Z`: `checkout-web` 401 rate `18.7`, `payment-api` 401 rate `21.2`, `auth-gateway` 401 rate `28.4`. `orders-db` shows `p95_ms=35` with note `cpu spike but query latency normal`. `cdn-edge` shows `4.8` 5xx rate, but the note says it is isolated to images.
- `in/logs/orders-db.log` shows `cpu_high cpu=86 pct maintenance=vacuum`, then `p95_query_ms=35 connections=64 errors=0`, and `no failed checkout transaction reached orders-db for request_id=req-8812`.

## Inferences
- [INFERENCE] The primary fault is an auth-gateway configuration regression introduced by `AUTH-2026-0318`: the deploy changed issuer/JWKS settings, then auth-gateway rejected `partner-v2` tokens because its effective allowed issuer remained `partner-v1` after a cache miss and fallback.
- [INFERENCE] `payment-api` and `checkout-web` are symptomatic victims, not origin services, because their errors are downstream 401/auth failures that match the auth-gateway rejection chain.
- [INFERENCE] `orders-db` and `cdn-edge` are red herrings for this checkout outage. They had anomalous signals, but neither aligns with the request path or failure mode that blocked checkout submission.

## Most likely root cause
`auth-gateway` is the root-cause service. The most likely root-cause change is `AUTH-2026-0318`.

## Immediate mitigation
1. Revert `AUTH-2026-0318` or restore `allowed_issuers` to include `partner-v2` in `auth-gateway`.
2. Rebuild or warm the JWKS cache for `partner-v2` so validation no longer falls back to `partner-v1`.
3. Pause further auth-gateway config changes until token validation succeeds for partner-v2 end to end.

## Verification steps
1. Replay a checkout with a `partner-v2` token.
2. Confirm `auth-gateway` no longer logs `issuer_not_allowed` for `partner-v2` (`in/logs/auth-gateway.log` equivalent signal).
3. Confirm `payment-api` stops returning `auth_result=invalid_issuer` (`in/logs/payment-api.log` equivalent signal).
4. Confirm `checkout-web` no longer returns upstream `401` from `payment-api` on submit (`in/logs/checkout-web.log` equivalent signal).
5. Confirm 401 rates in the same metric families fall back toward baseline in `in/metrics/service_metrics.csv`.

## Excluded red herrings
- `orders-db` / `DB-2026-0144`: directly observed normal query latency and zero DB errors; failing checkout requests did not reach the DB.
- `cdn-edge` / `CDN-2026-0091`: directly observed as isolated to static images; checkout remained blocked by auth failures after static assets recovered.
