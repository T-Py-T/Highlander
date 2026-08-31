# Checkout incident triage

## Finding

**Directly observed facts:** The checkout request `req-8812` failed with HTTP 401 at `checkout-web`, which received the failure from `payment-api` (`/workspace/in/logs/checkout-web.log`). `payment-api` recorded `issuer_not_allowed` from `auth-gateway` and rejected payment creation (`/workspace/in/logs/payment-api.log`). `auth-gateway` deployed `AUTH-2026-0318` at 14:05Z, selected issuer `partner-v2`, then rejected it because only `partner-v1` was allowed (`/workspace/in/logs/auth-gateway.log`).

**Inferred root cause:** `AUTH-2026-0318` left the auth gateway's allowed-issuer configuration inconsistent with its new `partner-v2` issuer/JWKS namespace. This is the primary cause with high confidence because the failure starts after that change and the logs identify the exact mismatch.

## Dependency path

The topology defines `checkout-web -> payment-api -> auth-gateway` (`/workspace/in/topology.json`). A checkout submit calls payment creation; payment authentication calls the auth gateway; the issuer mismatch causes auth rejection, payment rejection, and then user-visible checkout failure. Metrics support this path: at 14:10Z, HTTP 401 rates were 18.7% for checkout-web, 21.2% for payment-api, and 28.4% for auth-gateway (`/workspace/in/metrics/service_metrics.csv`).

Orders-db was not on the failing request path after the auth gate. Its 86% CPU signal occurred during vacuum, but query p95 was 35 ms with no errors and the request did not reach it (`/workspace/in/logs/orders-db.log`). CDN image 5xx errors were isolated; assets recovered while checkout remained blocked (`/workspace/in/logs/checkout-web.log`). These are **directly observed facts**; the conclusion that they are red herrings is an **inference** from those facts and the dependency graph.

## Immediate mitigation

1. Under change control, revert `AUTH-2026-0318`, or update `allowed_issuers` to accept the intended `partner-v2` issuer as the auth log recommends.
2. Refresh/invalidate the affected JWKS cache and confirm the `partner-v2` keys match the issuer configuration.
3. Avoid disabling authentication or bypassing the payment auth gate.

## Verification

- Confirm a known-good partner token validates at `auth-gateway` with no `issuer_not_allowed` events.
- Submit a payment through `payment-api`, then run an end-to-end checkout submit through `checkout-web`.
- Check that 401/5xx rates and p95 latency return toward baseline for all three services, and that no new issuer mismatch events occur.
- Confirm orders-db and CDN signals separately; neither should be used as the success criterion for the auth fix.
