# Checkout incident triage

## Conclusion

**Directly observed fact:** The user-visible failure is checkout submission rejection with HTTP 401. The dependency path in `/workspace/in/topology.json` is:

`checkout-web -> payment-api -> auth-gateway`

**Inference:** The primary root cause is `auth-gateway` change `AUTH-2026-0318`, which changed the partner-token issuer/JWKS-cache configuration incompatibly. The evidence supports high confidence because the change preceded the failure and the same issuer mismatch appears at the auth, payment, and checkout layers.

## Dependency path from impact to cause

1. **Directly observed — user-facing layer:** `/workspace/in/logs/checkout-web.log` records `submit_order` failing with status 401 from `payment-api` at 14:09:41Z. It also records `invalid issuer` from the payment dependency and says the checkout flow stayed blocked even after static assets recovered.
2. **Directly observed — payment layer:** `/workspace/in/logs/payment-api.log` records token validation failure from `auth-gateway` with `reason=issuer_not_allowed`, followed by `create_payment` rejection as `invalid_issuer`.
3. **Directly observed — authentication layer:** `/workspace/in/logs/auth-gateway.log` records deployment of `AUTH-2026-0318` at 14:05:12Z with issuer/JWKS namespace `partner-v2`. It then records a JWKS cache miss, fallback to `partner-v1`, and rejection of token issuer `partner-v2` because the allowed issuer remained `partner-v1`.
4. **Directly observed — metrics correlation:** `/workspace/in/metrics/service_metrics.csv` shows the 14:10Z spike in HTTP 401s: 18.7% for checkout-web, 21.2% for payment-api, and 28.4% for auth-gateway. The notes explicitly identify invalid issuer at payment-api and issuer mismatch at auth-gateway.
5. **Directly observed — topology/change correlation:** `/workspace/in/topology.json` places auth-gateway directly on the checkout payment path and identifies `AUTH-2026-0318` as the recent auth change.

**Inference:** Invalid issuer handling at auth-gateway propagated as payment authorization failures, which propagated as checkout submission failures. Orders were not reached for the failing request, so the database is not the initiating failure.

## Misleading signals excluded

- **Orders DB CPU:** `/workspace/in/metrics/service_metrics.csv` reports 86% CPU, but `/workspace/in/logs/orders-db.log` reports normal 35 ms query p95, zero errors, and no failed checkout transaction reached the database. This is maintenance-related and not primary.
- **CDN errors:** The metrics show 4.8% CDN 5xx, but the note isolates them to images. `/workspace/in/logs/checkout-web.log` says static assets recovered while checkout remained blocked. This does not explain the payment 401s.
- **Elevated latency:** Checkout and payment p95 increased, but the correlated 401/issuer errors indicate downstream retries or rejected authorization rather than an independent latency root cause.

## Immediate mitigation

1. Roll back `AUTH-2026-0318`, or restore `partner-v2` to the auth-gateway allowed issuer configuration as the safer targeted fix if rollback is not available.
2. Refresh/invalidate the affected JWKS cache namespace after correcting configuration, following the normal change-control procedure.
3. Keep checkout traffic/error monitoring active while the fix propagates; do not treat CDN or orders-db remediation as the primary incident action.

## Verification steps

- **Direct verification:** Validate a known-good `partner-v2` token at auth-gateway and confirm no `issuer_not_allowed` or issuer mismatch is logged.
- **Direct verification:** Execute a controlled payment authorization/create_payment request and confirm payment-api no longer returns `invalid_issuer` or HTTP 401.
- **Direct verification:** Execute a controlled checkout submit and confirm checkout-web returns success rather than 401.
- **Direct verification:** Confirm checkout-web and payment-api 401 rates and p95 latency trend back toward the 14:00Z baseline, while watching for recurrence of JWKS cache misses.

