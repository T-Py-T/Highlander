# Checkout Incident Triage

## Impact and Dependency Path

**Directly observed:** `checkout-web` returned a 401 from `payment-api` and reported that checkout submissions were blocked (`/workspace/in/logs/checkout-web.log`).

**Directly observed:** The topology defines the relevant path as `checkout-web -> payment-api -> auth-gateway` (`/workspace/in/topology.json`). Payment authorization therefore depends on the auth gateway before the order reaches the database.

**Directly observed:** `payment-api` received `issuer_not_allowed` from `auth-gateway` for issuer `partner-v2` and rejected `create_payment` with `invalid_issuer` (`/workspace/in/logs/payment-api.log`).

**Directly observed:** `auth-gateway` deployed `AUTH-2026-0318` at 14:05:12Z, configured `partner-v2`, then fell back from a partner-v2 JWKS cache miss to partner-v1 and rejected partner-v2 because `allowed_issuers=partner-v1` (`/workspace/in/logs/auth-gateway.log`).

**Inference:** `AUTH-2026-0318` introduced an inconsistent issuer/JWKS and allowed-issuer configuration. That mismatch is the primary root cause, propagating auth failures through payment-api to checkout-web.

## Corroboration and Exclusions

**Directly observed:** At 14:10Z, 401 rates were 18.7% for checkout-web, 21.2% for payment-api, and 28.4% for auth-gateway; the auth metric explicitly notes a JWKS cache miss and issuer mismatch (`/workspace/in/metrics/service_metrics.csv`).

**Directly observed:** orders-db had 86% CPU but 35 ms query p95 and zero errors, and no failed checkout transaction reached it (`/workspace/in/logs/orders-db.log`). This is not the primary cause.

**Directly observed:** CDN errors were isolated to images, while checkout assets recovered and the flow remained blocked (`/workspace/in/metrics/service_metrics.csv`, `/workspace/in/logs/checkout-web.log`). CDN is not the primary cause.

## Immediate Mitigation

1. Roll back `AUTH-2026-0318`, or make the intended configuration internally consistent by allowing `partner-v2` and ensuring its JWKS namespace/key set is available. Use the rollback candidate recorded in `/workspace/in/logs/auth-gateway.log`.
2. Pause further auth-related rollout and preserve relevant request, issuer, and configuration evidence.
3. Avoid changing orders-db or CDN as a checkout remediation; their observed signals do not explain the auth-gated failure.

## Verification

1. Confirm auth-gateway has the intended allowed issuer and JWKS namespace, with a successful cache lookup and no partner-v1 fallback.
2. Validate a representative partner-v2 token directly through auth-gateway.
3. Submit a test payment through payment-api and complete an end-to-end checkout through checkout-web.
4. Confirm checkout-web/payment-api/auth-gateway 401 and 5xx rates, latency, and checkout success return to baseline; confirm no new `invalid_issuer` or `issuer_not_allowed` events.
