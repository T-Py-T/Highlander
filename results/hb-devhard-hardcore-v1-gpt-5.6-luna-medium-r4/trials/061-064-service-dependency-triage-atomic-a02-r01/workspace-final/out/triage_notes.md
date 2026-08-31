# Checkout incident triage

## Dependency path

**Directly observed:** `in/topology.json` defines the request path `checkout-web -> payment-api -> auth-gateway`. The same fixture shows `orders-api -> orders-db` as a separate branch.

**Directly observed:** `in/logs/checkout-web.log` records `submit_order` failing with HTTP 401 from `payment-api`, followed by `invalid issuer`; the checkout flow stayed blocked.

**Directly observed:** `in/logs/payment-api.log` records token validation failure at `auth-gateway` with `issuer_not_allowed` for issuer `partner-v2`, then rejects payment creation as `invalid_issuer`.

**Directly observed:** `in/logs/auth-gateway.log` records deployment of `AUTH-2026-0318` at 14:05Z, then a JWKS cache miss and validation of `partner-v2` against an allowlist containing only `partner-v1`. It explicitly lists restoring `partner-v2` or reverting the change as a rollback candidate.

**Inference:** The most likely root cause is `AUTH-2026-0318` leaving the auth issuer allowlist inconsistent with the newly selected `partner-v2` issuer (possibly alongside the JWKS namespace change). This makes `auth-gateway` the root-cause service and causes payment and then checkout failures.

## Red herrings

**Directly observed:** `in/logs/orders-db.log` shows high CPU during vacuum, but 35 ms query p95, zero errors, and no failing checkout transaction reached the database. This is not the primary cause.

**Directly observed:** `in/metrics/service_metrics.csv` reports CDN 5xx errors isolated to images; checkout logs report static assets served normally after retry. CDN degradation does not explain payment 401s.

## Immediate mitigation

1. Restore `partner-v2` to the `auth-gateway` allowed issuer set, or roll back `AUTH-2026-0318`.
2. Confirm the JWKS cache points to the intended `partner-v2` namespace and clear or refresh stale auth cache entries if needed.
3. Keep the checkout/payment error path under heightened monitoring; do not treat the orders-db CPU spike as the checkout fix.

## Verification

1. Validate a known-good `partner-v2` token at `auth-gateway`; confirm no `issuer_not_allowed` errors and successful JWKS lookup.
2. Run a payment-api `create_payment` canary and then a complete checkout canary.
3. Confirm checkout-web and payment-api 401/5xx rates and p95 latency return near the 14:00Z baseline in `in/metrics/service_metrics.csv`.
4. Confirm the canary reaches orders-db only after successful auth and completes without transaction errors.
