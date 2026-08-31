# Checkout incident triage notes

## Summary
User impact flowed through this path:

`checkout-web -> payment-api -> auth-gateway`

The primary break was in `auth-gateway`, where partner tokens with issuer `partner-v2` were rejected because `allowed_issuers` still showed `partner-v1` after change `AUTH-2026-0318`.

## Directly observed facts
- **Fact:** `/workspace/in/logs/checkout-web.log` shows checkout submit failures with `status=401` from `payment-api`, plus `auth_failed invalid issuer` during checkout sessions.
- **Fact:** `/workspace/in/logs/payment-api.log` shows token validation failure at `auth-gateway` with `reason=issuer_not_allowed` and `auth_result=invalid_issuer`.
- **Fact:** `/workspace/in/logs/auth-gateway.log` shows deploy `AUTH-2026-0318`, then `jwks cache lookup miss namespace=partner-v2 fallback=partner-v1`, then `validation failed reason=issuer_not_allowed token_issuer=partner-v2 allowed_issuers=partner-v1`.
- **Fact:** `/workspace/in/metrics/service_metrics.csv` shows a sharp 401 rise at `checkout-web` (18.7), `payment-api` (21.2), and `auth-gateway` (28.4) at `2026-03-22T14:10:00Z`.
- **Fact:** `/workspace/in/topology.json` shows the dependency chain `checkout-web -> payment-api -> auth-gateway` and lists `AUTH-2026-0318` as a recent auth-gateway change.
- **Fact:** `/workspace/in/logs/orders-db.log` shows high CPU during vacuum, but query latency stayed normal and no failed checkout transaction for `req-8812` reached `orders-db`.

## Inferences
- **Inference:** The user-visible checkout failure started in `checkout-web`, but the first causal failure on the request path was token validation in `auth-gateway`.
- **Inference:** `AUTH-2026-0318` likely changed issuer/JWKS settings in a way that left `partner-v2` tokens active in deployment metadata but not in the effective `allowed_issuers` validation set.
- **Inference:** `payment-api` acted as a propagator, not the origin, because it reports auth rejection from its upstream auth dependency.

## Dependency path from impact to root cause
1. Users hit `checkout-web` and see submit failures.  
   Evidence: `/workspace/in/logs/checkout-web.log`
2. `checkout-web` depends on `payment-api` for checkout submit flow.  
   Evidence: `/workspace/in/topology.json`
3. `payment-api` rejects payment creation because auth fails before any order DB work starts.  
   Evidence: `/workspace/in/logs/payment-api.log`
4. `payment-api` depends on `auth-gateway`, which rejects `partner-v2` tokens as `issuer_not_allowed`.  
   Evidence: `/workspace/in/logs/auth-gateway.log`
5. That auth failure lines up in time with the recent auth change `AUTH-2026-0318`.  
   Evidence: `/workspace/in/topology.json`, `/workspace/in/logs/auth-gateway.log`

## Red herrings ruled out
- **orders-db CPU spike** — not primary. Query p95 stayed normal, errors stayed at 0, and the failed request did not reach the DB path.  
  Evidence: `/workspace/in/metrics/service_metrics.csv`, `/workspace/in/logs/orders-db.log`, `/workspace/in/logs/payment-api.log`
- **cdn-edge 5xx spike** — not primary. Metrics say it was isolated to static images, and checkout-web says assets recovered while checkout stayed blocked.  
  Evidence: `/workspace/in/metrics/service_metrics.csv`, `/workspace/in/logs/checkout-web.log`
- **DB-2026-0144** — not primary. The change note says vacuum tuning only, with no schema or credential change.  
  Evidence: `/workspace/in/topology.json`

## Immediate mitigation
1. Restore `auth-gateway` validation so `partner-v2` is present in the effective `allowed_issuers` set.
2. If that cannot be done fast, roll back `AUTH-2026-0318`.
3. Flush or rebuild the bad JWKS/issuer cache path if rollback alone does not clear the mismatch.

## Verification steps
1. Confirm new `auth-gateway` logs no longer show `issuer_not_allowed` for `token_issuer=partner-v2`.
2. Confirm `payment-api` no longer logs `auth_result=invalid_issuer` for checkout traffic.
3. Confirm `checkout-web` 401 rate and p95 move back toward baseline in `/workspace/in/metrics/service_metrics.csv`.
4. Run a known-good checkout and confirm the request reaches downstream order work only after auth succeeds.

## Bottom line
- **Root cause:** `auth-gateway`
- **Likely triggering change:** `AUTH-2026-0318`
- **Confidence:** High
