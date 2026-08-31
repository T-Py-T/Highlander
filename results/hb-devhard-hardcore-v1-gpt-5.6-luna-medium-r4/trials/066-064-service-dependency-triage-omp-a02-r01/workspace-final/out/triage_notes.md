# Checkout dependency triage

## Conclusion

**Root cause: `auth-gateway`, change `AUTH-2026-0318` (high confidence).** The change deployed at 14:05Z and introduced an issuer/JWKS namespace mismatch: tokens carrying issuer `partner-v2` were rejected because the configured allowed issuer remained `partner-v1`.

## Dependency path

The user-facing path is:

`checkout-web` → `payment-api` → `auth-gateway`

This path is directly defined in `in/topology.json`. At 14:09:41Z, `checkout-web` logged `submit_order` failing with HTTP 401 from `payment-api` (`in/logs/checkout-web.log`). `payment-api` then recorded that validation failed upstream at `auth-gateway` with `issuer_not_allowed` for `partner-v2`, and rejected the payment request as `invalid_issuer` (`in/logs/payment-api.log`). `auth-gateway` recorded the deployment, JWKS cache miss, and the decisive mismatch—`token_issuer=partner-v2` versus `allowed_issuers=partner-v1`—in `in/logs/auth-gateway.log`.

The metrics corroborate the same chain: at 14:10Z, HTTP 401 rates were 18.7% for `checkout-web`, 21.2% for `payment-api`, and 28.4% for `auth-gateway`; the corresponding notes identify rejected checkout submits, invalid issuer responses, and issuer mismatch (`in/metrics/service_metrics.csv`).

**Directly observed facts:** the dependency edges, deployment/change ID, log messages, issuer values, allowed issuer, request rejection, and 14:10Z metric values stated above are present in the cited fixtures.

**Inference:** the issuer configuration/cache namespace behavior introduced by `AUTH-2026-0318` is the primary causal fault because it precedes and explains the correlated 401s across the dependency path. The fixture evidence supports this with high confidence, but does not show the change diff itself.

## Misleading signals

- `orders-db` CPU reached 86%, but `in/metrics/service_metrics.csv` shows normal 35 ms query latency and zero errors. `in/logs/orders-db.log` says the failing request never reached the database. This is maintenance-related, not the checkout blocker.
- `cdn-edge` showed 4.8% HTTP 5xx, but the metric limits the issue to images. `in/logs/checkout-web.log` says static assets recovered while checkout remained blocked, and CDN is not on the payment authorization path.
- Elevated checkout latency is a downstream symptom of failed payment authorization, not a separate root cause.

## Immediate mitigation

1. Halt or roll back `AUTH-2026-0318`, **or** restore `partner-v2` to `allowed_issuers`, following the approved emergency-change process.
2. Invalidate/rebuild the JWKS cache for the intended `partner-v2` namespace.
3. Avoid retry storms while authorization is failing; preserve representative request IDs such as `req-8812` for correlation.

## Verification

1. Submit a controlled checkout payment authorization and confirm `auth-gateway` accepts a `partner-v2` token.
2. Confirm `payment-api` returns success and the request proceeds to order creation; this must be a new controlled transaction because the failing fixture request stopped before `orders-db`.
3. Confirm HTTP 401 rates and p95 latency for `auth-gateway`, `payment-api`, and `checkout-web` return toward the baseline shown in `in/metrics/service_metrics.csv`.
4. Verify no new `invalid_issuer` or `issuer_not_allowed` entries appear in the three service logs during the observation window. Track the independent CDN image errors and database CPU separately.
