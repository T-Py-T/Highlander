# Checkout incident triage

## Conclusion

**Root cause (inference, high confidence):** `auth-gateway` rejected valid partner-token requests after change `AUTH-2026-0318` changed the issuer/JWKS namespace to `partner-v2` while the configured allowed issuer remained `partner-v1`. This broke payment authorization and consequently blocked checkout submissions.

## Dependency path

**Directly observed topology:** `/workspace/in/topology.json` defines the path `checkout-web -> payment-api -> auth-gateway` (and separately `checkout-web -> orders-api -> orders-db`).

**Directly observed user impact:** `/workspace/in/logs/checkout-web.log` records `submit_order` failing with HTTP 401 from `payment-api` at 14:09:41Z and states that the checkout flow remained blocked even after static assets recovered.

**Directly observed dependency failure:** `/workspace/in/logs/payment-api.log` records token validation failing upstream at `auth-gateway` with `issuer_not_allowed` for `partner-v2`, followed by rejection of `create_payment`.

**Directly observed root-cause change/configuration mismatch:** `/workspace/in/logs/auth-gateway.log` records deployment of `AUTH-2026-0318` at 14:05:12Z with `partner-v2`, then a validation failure showing `token_issuer=partner-v2` but `allowed_issuers=partner-v1`. It also records a rollback/remediation candidate.

**Corroborating metrics (directly observed):** `/workspace/in/metrics/service_metrics.csv` shows elevated 401 rates at 14:10Z on checkout-web (18.7%), payment-api (21.2%), and auth-gateway (28.4%), with elevated checkout/payment p95 latency. The timing and dependency alignment support the root-cause inference.

## Red herrings

- **orders-db CPU spike:** Directly observed at 86%, but `/workspace/in/logs/orders-db.log` reports 35 ms query p95, zero errors, and no failed checkout transaction reached the database. It is not the primary cause.
- **cdn-edge 5xx rate:** Directly observed at 4.8% in `/workspace/in/metrics/service_metrics.csv`, but the note limits it to images and checkout-web reports static assets recovered while submissions stayed blocked. It is not the primary cause.

## Immediate mitigation

1. Pause or revert `AUTH-2026-0318`, or correct `allowed_issuers` to include the intended `partner-v2` issuer after validating the change.
2. Refresh/invalidate the affected JWKS cache and verify the `partner-v2` JWKS is available; eliminate the `partner-v2` to `partner-v1` fallback mismatch.
3. Keep monitoring checkout and payment traffic while the auth configuration is corrected.

## Verification and exit criteria

1. Execute a controlled end-to-end checkout payment-authentication request.
2. Confirm auth-gateway accepts the intended partner token and payment-api returns a successful payment authorization.
3. Confirm checkout-web completes `submit_order` rather than returning 401.
4. Confirm HTTP 401 rates and p95 latency for auth-gateway, payment-api, and checkout-web return near their pre-incident baseline; verify no new issuer/JWKS mismatch messages.
5. Confirm orders-db remains healthy and that successful checkout transactions reach it normally.

Statements labeled **directly observed** come from the offline fixture files. The causal conclusion, prioritization of `AUTH-2026-0318`, and expected recovery behavior are **inferences** drawn from those observations and the topology.
