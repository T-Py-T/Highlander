# Production checkout incident triage

## Conclusion

**Root cause (inference, high confidence):** `auth-gateway` rejected valid partner-v2 tokens after change `AUTH-2026-0318` rotated the issuer/JWKS cache namespace but left the allowed issuer configured as `partner-v1` (with a cache fallback to `partner-v1`). This broke payment authorization and therefore checkout submission.

## Dependency path

**Directly observed topology:** `/workspace/in/topology.json` defines the user-facing path as:

`checkout-web -> payment-api -> auth-gateway`

`checkout-web` also depends on `orders-api -> orders-db` and `cdn-edge`, but those branches do not explain the authorization failure.

**Directly observed impact:** `/workspace/in/logs/checkout-web.log` shows `submit_order` failing with HTTP 401 from `payment-api`; it also says static assets were served normally while checkout remained blocked.

**Directly observed propagation:** `/workspace/in/logs/payment-api.log` records auth validation failure from `auth-gateway` (`issuer_not_allowed`, token issuer `partner-v2`) and then rejects `create_payment` with `invalid_issuer`.

**Directly observed root symptom and change correlation:** `/workspace/in/logs/auth-gateway.log` records deployment of `AUTH-2026-0318` at 14:05:12Z, followed by a partner-v2 JWKS cache miss, fallback to partner-v1, and rejection because `allowed_issuers=partner-v1`. The same log explicitly names reverting the change or restoring partner-v2 as rollback candidates.

**Metric corroboration (directly observed):** `/workspace/in/metrics/service_metrics.csv` shows at 14:10Z:

- `checkout-web`: 18.7% HTTP 401, p95 2400 ms
- `payment-api`: 21.2% HTTP 401, p95 1800 ms, note says auth dependency returned invalid issuer
- `auth-gateway`: 28.4% HTTP 401, note says JWKS cache miss and issuer mismatch

The aligned 401 spike and issuer-specific notes support the dependency chain. The statement that `AUTH-2026-0318` caused the incident is an **inference from temporal correlation plus the matching configuration failure**, not a directly observed causal experiment.

## Signals excluded as primary causes

- **orders-db CPU spike:** Directly observed in `/workspace/in/metrics/service_metrics.csv` and `/workspace/in/logs/orders-db.log`, but query p95 was 35 ms, errors were zero, and no failing checkout transaction reached the database. This is a maintenance/vacuum signal, not the primary cause.
- **cdn-edge 5xx spike:** Directly observed in `/workspace/in/metrics/service_metrics.csv`, but it was isolated to images. Checkout-web directly reports static assets serving normally after retry; the checkout failure is an HTTP 401 authorization failure. Not primary.

## Immediate mitigation

1. Roll back `AUTH-2026-0318`, or restore `partner-v2` in `auth-gateway`'s allowed issuer configuration and restore the intended JWKS cache namespace.
2. Invalidate/rebuild the affected JWKS cache after configuration correction.
3. Keep checkout recovery scoped to the auth/payment path; do not alter orders-db or CDN based only on their misleading signals.

These are **recommended actions/inferences**, not actions performed against a live service. This triage used offline fixtures only.

## Verification steps

1. Confirm auth-gateway accepts a known-good partner-v2 token and no longer falls back to partner-v1.
2. Confirm auth-gateway HTTP 401 rate returns near the 14:00Z baseline, then confirm payment-api and checkout-web 401 rates decline.
3. Exercise a complete checkout and verify the same request path reaches payment authorization and order persistence.
4. Confirm checkout-web p95 returns toward baseline and inspect logs for absence of `issuer_not_allowed` / `invalid_issuer`.
5. Continue observing orders-db query latency/errors and CDN image errors separately; recovery of checkout must not be inferred from either branch alone.

Steps 1–5 are **verification plans**, not directly observed facts from the supplied evidence.
