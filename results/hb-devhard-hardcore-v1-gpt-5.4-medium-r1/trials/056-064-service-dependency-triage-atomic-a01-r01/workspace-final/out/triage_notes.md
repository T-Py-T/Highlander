# Checkout incident triage

## Summary
User impact flowed on this path: `checkout-web -> payment-api -> auth-gateway`.

The direct user-facing failure was checkout rejection at `checkout-web`, but the deepest failing dependency in the evidence is `auth-gateway`. The most likely root cause is change `AUTH-2026-0318`, which rotated the issuer and JWKS cache namespace for partner-token validation and left `allowed_issuers` out of sync with `partner-v2` tokens.

## Directly observed facts
- `/workspace/in/topology.json` shows `checkout-web` depends on `payment-api`, and `payment-api` depends on `auth-gateway`.
- `/workspace/in/topology.json` lists recent change `AUTH-2026-0318` on `auth-gateway` with summary: rotated issuer and JWKS cache namespace for partner-token validation.
- `/workspace/in/logs/auth-gateway.log` shows:
  - deploy of `AUTH-2026-0318`
  - `jwks cache lookup miss namespace=partner-v2`
  - `validation failed reason=issuer_not_allowed token_issuer=partner-v2 allowed_issuers=partner-v1`
- `/workspace/in/logs/payment-api.log` shows payment requests failed because token validation failed upstream at `auth-gateway`, with `reason=issuer_not_allowed` and `auth_result=invalid_issuer`.
- `/workspace/in/logs/checkout-web.log` shows checkout submission failed with `status=401` from `payment-api`, and it logs `invalid issuer`.
- `/workspace/in/metrics/service_metrics.csv` shows a sharp 401 rise at 14:10 for `checkout-web` (18.7), `payment-api` (21.2), and `auth-gateway` (28.4).

## Inferences
- The dependency path from user impact to root cause is: checkout submit fails in `checkout-web` because `payment-api` rejects the request, and `payment-api` rejects it because `auth-gateway` no longer accepts the token issuer used by partner-v2.
- `AUTH-2026-0318` is the root-cause change because it is the matching recent config change on the failing service, and its change scope matches the exact error text in the logs.
- The incident did not start in `orders-db` or `cdn-edge` because the failing checkout request never reached `orders-db`, and the asset issue is separate from the auth failure that blocks checkout.

## Red herrings ruled out
- **`orders-db` CPU spike**: `/workspace/in/metrics/service_metrics.csv` shows high CPU, but `/workspace/in/logs/orders-db.log` reports normal query latency and zero errors, and `/workspace/in/logs/payment-api.log` says the failing requests did not use order-db before the auth gate.
- **`cdn-edge` static asset 5xx**: `/workspace/in/metrics/service_metrics.csv` says the issue was isolated to images, and `/workspace/in/logs/checkout-web.log` says assets served after retry while checkout stayed blocked.

## Immediate mitigation
1. Revert `AUTH-2026-0318` on `auth-gateway`, or restore `allowed_issuers` to include `partner-v2`.
2. Clear or rebuild the `partner-v2` JWKS cache namespace so issuer validation and key lookup line up.
3. Watch 401 rates on `auth-gateway`, `payment-api`, and `checkout-web` during the rollback or config fix.

## Verification steps
1. Confirm `auth-gateway` no longer logs `issuer_not_allowed` for `partner-v2` tokens.
2. Confirm `payment-api` no longer returns `auth_result=invalid_issuer` for checkout traffic.
3. Confirm `checkout-web` submit requests stop failing with upstream 401s.
4. Run a checkout with a partner-v2 token and verify the request passes auth and reaches downstream order handling.
