# Checkout incident triage

## Dependency path

**Directly observed facts:** `in/topology.json` defines the request path as `checkout-web → payment-api → auth-gateway`. `in/logs/checkout-web.log` records `submit_order` failing with HTTP 401 from `payment-api`, and reports that the checkout flow remained blocked. `in/logs/payment-api.log` records token validation failing at `auth-gateway` with `issuer_not_allowed`, followed by rejection of the payment request.

**Directly observed facts:** `in/logs/auth-gateway.log` records deployment of `AUTH-2026-0318` at 14:05Z, setting the JWKS namespace and issuer to `partner-v2`. It then records a cache miss, fallback to `partner-v1`, and validation failure because only `partner-v1` was allowed while the token issuer was `partner-v2`. The same file names restoring `partner-v2` or reverting `AUTH-2026-0318` as rollback candidates.

**Inference:** The production checkout impact began when the auth change made partner-token validation reject the issuer. That rejection propagated upstream through `payment-api` to `checkout-web`; `auth-gateway` and change `AUTH-2026-0318` are therefore the primary root cause.

## Scope and red herrings

**Directly observed facts:** `in/metrics/service_metrics.csv` shows elevated HTTP 401 rates at 14:10Z for checkout-web (18.7%), payment-api (21.2%), and auth-gateway (28.4%), with notes tying the latter two to invalid issuer/mismatch. The same file shows orders-db CPU at 86%, but 35 ms query p95 and zero errors. `in/logs/orders-db.log` says no failed checkout transaction reached the database. The CDN 5xx rate is 4.8%, but `in/metrics/service_metrics.csv` says it was isolated to images; `in/logs/checkout-web.log` says static assets served normally after retry.

**Inference:** Orders DB load and the CDN image errors are concurrent, misleading signals, not causes of the checkout authorization failures. The checkout and payment latency/5xx changes are downstream effects of auth rejection.

## Immediate mitigation

1. Restore `partner-v2` to `allowed_issuers` on auth-gateway, or revert `AUTH-2026-0318`.
2. Ensure every auth-gateway instance uses the matching JWKS cache namespace and issuer configuration.
3. Avoid replaying failed payments until token validation is healthy; then retry safely under normal idempotency controls.

## Verification

- **Directly observed baseline:** before the incident, checkout-web had 0.1% 401 and 410 ms p95 in `in/metrics/service_metrics.csv`.
- Check auth-gateway logs and metrics for disappearance of `issuer_not_allowed` and a return of 401 rate toward baseline.
- Send a controlled partner-v2 token validation test and confirm accepted issuer/JWKS lookup on all instances.
- Run a controlled `create_payment` request, then `submit_order`; confirm successful responses and that the request reaches orders-db.
- Confirm checkout-web 401/latency recover without relying on CDN or orders-db changes.
