# Checkout Incident Triage

## Finding

**Directly observed facts:** Checkout submissions returned 401 responses. `payment-api` logged `issuer_not_allowed` for token issuer `partner-v2`, and `auth-gateway` showed that `AUTH-2026-0318` deployed `partner-v2` while the allowed issuer remained `partner-v1`. At 14:10 UTC, the metrics showed elevated 401 rates for `checkout-web` (18.7%), `payment-api` (21.2%), and `auth-gateway` (28.4%).

**Inference:** The primary cause is an issuer configuration incompatibility introduced by `AUTH-2026-0318` in `auth-gateway`, not a checkout-web defect or database outage.

## Dependency Path

**Directly observed:** The topology in `/workspace/in/topology.json` defines the relevant path as `checkout-web -> payment-api -> auth-gateway`. `/workspace/in/logs/checkout-web.log` shows checkout-web receiving a 401 from payment-api for `req-8812`. `/workspace/in/logs/payment-api.log` shows payment-api rejecting the payment because auth-gateway returned an invalid issuer result. `/workspace/in/logs/auth-gateway.log` shows the issuer mismatch and the deployment immediately preceding it.

**Inference:** A customer submitting checkout reached payment-api, which invoked auth-gateway. Auth-gateway rejected the partner token, payment-api rejected payment creation, and checkout-web blocked the order. The failure occurred before order persistence.

## Excluded Signals

**Directly observed:** `/workspace/in/logs/orders-db.log` reports normal 35 ms query latency, zero errors, and no failed checkout transaction reaching orders-db despite 86% CPU. `/workspace/in/logs/checkout-web.log` reports static assets served normally after retry. The metrics file records CDN 5xx errors as isolated to images.

**Inference:** The orders-db CPU spike and CDN image errors are concurrent red herrings. They do not explain the authentication-specific 401 chain or the failed checkout request.

## Immediate Mitigation

1. Restore `partner-v2` in auth-gateway's allowed issuer configuration, or roll back `AUTH-2026-0318` through the approved emergency-change process.
2. Avoid retry storms while the auth configuration is corrected; preserve representative request IDs for post-incident analysis.

## Verification

**Directly observed baseline:** Before the incident, checkout-web had a 0.1% 401 rate and 410 ms p95 at 14:00 UTC.

**Verify after mitigation:**

1. Submit a known-good partner-v2 token to auth-gateway and confirm issuer validation and JWKS resolution succeed.
2. Create a payment through payment-api and confirm no `invalid_issuer` or `issuer_not_allowed` errors.
3. Complete an end-to-end checkout and confirm checkout-web 401 rate and p95 latency trend back toward baseline.
4. Confirm orders-db receives the successful transaction and remains error-free.
