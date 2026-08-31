# Checkout Incident Triage Notes

## Summary

- Directly observed fact: `checkout-web` depends on `payment-api`, and `payment-api` depends on `auth-gateway` (`/workspace/in/topology.json`).
- Directly observed fact: user-facing checkout failures were `401` responses from `payment-api`, with `invalid issuer` called out in the web tier logs (`/workspace/in/logs/checkout-web.log`).
- Directly observed fact: `auth-gateway` deployed `AUTH-2026-0318`, then logged `token_issuer=partner-v2` being rejected because `allowed_issuers=partner-v1` (`/workspace/in/logs/auth-gateway.log`).
- Inference: the production incident propagated along `checkout-web -> payment-api -> auth-gateway`, and the root cause was the auth-gateway issuer/JWKS configuration change `AUTH-2026-0318`.

## Dependency Path

- Directly observed fact: `checkout-web` calls `payment-api` (`/workspace/in/topology.json`).
- Directly observed fact: `payment-api` calls `auth-gateway` for token validation (`/workspace/in/topology.json`, `/workspace/in/logs/payment-api.log`).
- Directly observed fact: `auth-gateway` rejected `partner-v2` tokens with `reason=issuer_not_allowed` after `AUTH-2026-0318` (`/workspace/in/logs/auth-gateway.log`).
- Directly observed fact: `payment-api` then rejected `create_payment` with `auth_result=invalid_issuer` (`/workspace/in/logs/payment-api.log`).
- Directly observed fact: `checkout-web` surfaced this as failed order submission with `status=401 upstream=payment-api` (`/workspace/in/logs/checkout-web.log`).
- Inference: checkout availability degraded because payment authorization is a hard dependency in the checkout path.

## Supporting Evidence

- Directly observed fact: metrics at `2026-03-22T14:10:00Z` show synchronized `401` spikes on `auth-gateway` (28.4%), `payment-api` (21.2%), and `checkout-web` (18.7%), with notes referencing `invalid issuer`, `jwks cache miss`, and `issuer mismatch` (`/workspace/in/metrics/service_metrics.csv`).
- Directly observed fact: `AUTH-2026-0318` changed the auth service issuer and JWKS cache namespace for partner-token validation shortly before the incident (`/workspace/in/topology.json`).
- Inference: the timing and exact error text make `AUTH-2026-0318` the most likely causative change rather than a coincidental nearby deploy.

## Excluded Red Herrings

- Directly observed fact: `orders-db` showed high CPU during vacuum, but query latency stayed normal, error count stayed at zero, and failed checkout request `req-8812` never reached the DB (`/workspace/in/logs/orders-db.log`, `/workspace/in/metrics/service_metrics.csv`, `/workspace/in/logs/payment-api.log`).
- Inference: `orders-db` load is not the primary cause because the failure happens earlier at auth.
- Directly observed fact: `cdn-edge` had isolated static-image `5xx` errors, while checkout-web reported static assets were normal after retry and user checkout remained blocked (`/workspace/in/metrics/service_metrics.csv`, `/workspace/in/logs/checkout-web.log`).
- Inference: CDN issues were concurrent noise, not the checkout transaction blocker.

## Immediate Mitigation

- Revert `AUTH-2026-0318` on `auth-gateway`, or restore `partner-v2` in `allowed_issuers` while keeping issuer/JWKS settings internally consistent.
- Flush or rebuild the `partner-v2` JWKS cache namespace so validation does not fall back to `partner-v1` state.
- If rollback is not immediately possible, temporarily route affected partner traffic back to the last known-good issuer configuration.

## Verification Steps

- Confirm `auth-gateway` accepts a representative `partner-v2` token without `issuer_not_allowed`.
- Confirm `payment-api` no longer logs `auth_result=invalid_issuer` for new `create_payment` requests.
- Confirm `checkout-web` order submissions stop returning `401 upstream=payment-api`.
- Confirm `401` rates for `auth-gateway`, `payment-api`, and `checkout-web` return near the 14:00 baseline in `/workspace/in/metrics/service_metrics.csv`.
