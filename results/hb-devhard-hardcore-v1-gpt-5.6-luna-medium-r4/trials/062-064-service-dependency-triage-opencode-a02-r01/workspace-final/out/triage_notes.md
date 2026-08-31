# Checkout Incident Triage

## Conclusion

**Directly observed facts:** `checkout-web` rejected a checkout submission with HTTP 401 from `payment-api`. `payment-api` rejected the request after `auth-gateway` returned `issuer_not_allowed` for issuer `partner-v2`. `auth-gateway` had just deployed change `AUTH-2026-0318`, which used the `partner-v2` JWKS namespace, while its allowed issuer remained `partner-v1`.

**Inference:** The primary root cause is an issuer/JWKS configuration incompatibility introduced by `AUTH-2026-0318` in `auth-gateway`. Confidence is high because the deployment timing, explicit issuer mismatch, dependency path, and matching 401 metrics agree.

## Dependency Path

**Directly observed from `/workspace/in/topology.json`:**

`checkout-web -> payment-api -> auth-gateway`

The user-visible checkout failure begins at `checkout-web`, which calls `payment-api`. Payment authorization depends on `auth-gateway`; authentication failure prevents payment creation and therefore blocks checkout. **Directly observed:** the payment log states the order database was not used before the auth gate for failing requests.

## Timeline and Evidence

- **14:05:00Z:** **Directly observed in `/workspace/in/topology.json`:** `AUTH-2026-0318` was deployed to `auth-gateway` to rotate the issuer and JWKS cache namespace.
- **14:05:12Z:** **Directly observed in `/workspace/in/logs/auth-gateway.log`:** the deployment configured `partner-v2`.
- **14:08:33-14:08:34Z:** **Directly observed in `/workspace/in/logs/auth-gateway.log`:** the `partner-v2` JWKS lookup missed, fell back to `partner-v1`, and rejected a `partner-v2` token because `partner-v1` was the only allowed issuer.
- **14:09:04Z:** **Directly observed in `/workspace/in/logs/payment-api.log`:** payment creation for `req-8812` was rejected as `invalid_issuer`.
- **14:09:41Z-14:10:03Z:** **Directly observed in `/workspace/in/logs/checkout-web.log`:** checkout received a 401 from payment-api and remained blocked.
- **14:10:00Z:** **Directly observed in `/workspace/in/metrics/service_metrics.csv`:** HTTP 401 rates were 18.7% for checkout-web, 21.2% for payment-api, and 28.4% for auth-gateway, with issuer mismatch noted for auth-gateway.

## Excluded Signals

**Directly observed:** orders DB CPU was 86%, but query p95 was 35 ms with zero errors, and no failed checkout transaction reached it. This is not the primary cause.

**Directly observed:** CDN edge had a 4.8% 5xx rate isolated to images; checkout static assets served normally after retry. This is unrelated to the authentication rejection.

**Inference:** checkout-web latency and 401s are downstream symptoms, not an independent checkout-web root cause.

## Immediate Mitigation

1. Restore `partner-v2` in `auth-gateway`'s allowed issuer configuration, or revert `AUTH-2026-0318` as the log recommends.
2. Ensure the JWKS cache points to the matching `partner-v2` namespace and invalidate any stale/fallback cache state.
3. Avoid retrying checkout requests indefinitely until token validation is healthy; preserve request and payment idempotency.

## Verification

**Directly observed verification targets:** `auth-gateway` must stop logging `issuer_not_allowed`; `payment-api` must stop returning `invalid_issuer`; and checkout-web 401s must fall from the 14:10Z level.

**Inferred end-to-end check:** execute a synthetic checkout, confirm payment authorization succeeds, and verify the resulting transaction reaches `orders-db`. Also monitor auth-gateway, payment-api, and checkout-web 401 rates and p95 latency for at least one normal traffic interval.
