# Checkout incident triage notes

## Dependency path
Directly observed path from user impact to root cause:

1. `checkout-web` returned checkout submit failures with `401` from `payment-api` (`/workspace/in/logs/checkout-web.log`).
2. `payment-api` rejected the same flow because token validation failed at `auth-gateway` with `invalid_issuer` / `issuer_not_allowed` (`/workspace/in/logs/payment-api.log`).
3. `auth-gateway` had just deployed `AUTH-2026-0318`, then logged a `partner-v2` token issuer against `allowed_issuers=partner-v1`, which is the first clear broken condition in the chain (`/workspace/in/logs/auth-gateway.log`).
4. `topology.json` matches this path: `checkout-web -> payment-api -> auth-gateway` (`/workspace/in/topology.json`).

## Directly observed facts
- `/workspace/in/logs/auth-gateway.log` shows `AUTH-2026-0318` deployed at `2026-03-22T14:05:12Z` with `jwks_namespace=partner-v2 issuer=partner-v2`.
- The same log shows `validation failed reason=issuer_not_allowed token_issuer=partner-v2 allowed_issuers=partner-v1` at `2026-03-22T14:08:34Z`.
- `/workspace/in/logs/payment-api.log` shows `create_payment` rejected `req-8812` with `auth_result=invalid_issuer` and says `order-db dependency not used before auth gate for failing requests`.
- `/workspace/in/logs/checkout-web.log` shows checkout submit failed with `status=401 upstream=payment-api` and `invalid issuer`.
- `/workspace/in/metrics/service_metrics.csv` shows a sharp 401 rise at 14:10Z in `auth-gateway` (28.4), `payment-api` (21.2), and `checkout-web` (18.7).
- `/workspace/in/logs/orders-db.log` shows `errors=0`, `p95_query_ms=35`, and that failed request `req-8812` never reached `orders-db`.

## Inferences
- High-confidence root cause: `auth-gateway` change `AUTH-2026-0318` left issuer validation out of sync with the new `partner-v2` issuer/JWKS namespace.
- The user-visible checkout failure is a dependency cascade, not an app-only bug in `checkout-web`.
- `orders-db` and `cdn-edge` produced noise during the incident window but did not drive the blocked checkout path.

## Red herrings excluded
- **orders-db CPU spike**: directly observed CPU was high, but latency stayed normal and no failing checkout reached the DB. So this is not the primary cause.
- **cdn-edge 5xx on images**: directly observed as isolated to static assets; checkout-web logged assets recovered while checkout stayed blocked by auth.

## Immediate mitigation
1. Roll back `AUTH-2026-0318` on `auth-gateway`, or restore `allowed_issuers` so `partner-v2` is accepted.
2. Clear or rebuild the JWKS cache namespace so lookups do not fall back from `partner-v2` to `partner-v1`.
3. Watch `auth-gateway`, `payment-api`, and `checkout-web` for 401 drop after the fix.

## Verification steps
1. Replay or inspect a fresh checkout and confirm `checkout-web` no longer logs `submit_order failed status=401 upstream=payment-api`.
2. Confirm `payment-api` stops logging `auth_result=invalid_issuer`.
3. Confirm `auth-gateway` stops logging `issuer_not_allowed` for `token_issuer=partner-v2`.
4. Check service metrics for 401 rates and latency returning toward the 14:00Z baseline in `/workspace/in/metrics/service_metrics.csv`.
5. Confirm no new blocker appears downstream once auth passes, including a quick check that `orders-db` remains error-free.
