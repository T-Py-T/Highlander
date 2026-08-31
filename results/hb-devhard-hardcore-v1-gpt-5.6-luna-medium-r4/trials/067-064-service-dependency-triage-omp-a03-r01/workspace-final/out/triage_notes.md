# Checkout incident triage

## Conclusion

**Directly observed:** `checkout-web` payment submissions returned HTTP 401 because `payment-api` rejected partner tokens as invalid issuer. **Inference:** the production root cause is the `auth-gateway` rollout `AUTH-2026-0318`, which made the active issuer/JWKS namespace inconsistent with the allowed issuer configuration.

## Dependency path

`user checkout` → `checkout-web` → `payment-api` → `auth-gateway`

- **Directly observed in `in/topology.json`:** this is the declared dependency path; `orders-api` and `cdn-edge` are separate checkout-web dependencies, while `orders-api` leads to `orders-db`.
- **Directly observed in `in/logs/checkout-web.log`:** request `req-8812` failed at `14:09:41Z` with status 401 from `payment-api`; the checkout session then reported `auth_failed invalid issuer`. Static assets later recovered, but checkout remained blocked.
- **Directly observed in `in/logs/payment-api.log`:** at `14:08:59Z`, payment token validation failed against `auth-gateway` with `issuer_not_allowed`, for issuer `partner-v2`; `req-8812` was rejected at `14:09:04Z`.
- **Directly observed in `in/logs/auth-gateway.log`:** `AUTH-2026-0318` deployed at `14:05:12Z` with namespace/issuer `partner-v2`. At `14:08:34Z`, validation still allowed only `partner-v1` and rejected `partner-v2`. The log explicitly names restoring `partner-v2` or reverting the change as rollback candidates.
- **Directly observed in `in/metrics/service_metrics.csv`:** at `14:10Z`, HTTP 401 rates were 18.7% for checkout-web, 21.2% for payment-api, and 28.4% for auth-gateway. Checkout p95 was 2400 ms and payment p95 was 1800 ms.

**Inference:** the timing, issuer-specific error, and dependency direction make `AUTH-2026-0318` the primary causal change with high confidence. The checkout and payment symptoms are downstream propagation, not separate failures.

## Signals excluded from primary cause

- **Directly observed:** `orders-db` CPU was 86%, but query p95 was 35 ms with zero errors. `orders-db` logged that no failed checkout transaction reached it. **Inference:** this is unrelated workload noise, not the checkout blocker.
- **Directly observed:** `cdn-edge` had 4.8% HTTP 5xx, isolated to images; checkout logs report assets served normally after retry. **Inference:** CDN image failures do not cause the issuer-specific payment 401 chain.
- **Directly observed:** the JWKS cache miss fell back to `partner-v1`. **Inference:** this is part of the auth configuration inconsistency introduced by `AUTH-2026-0318`, not an independent dependency outage.

## Immediate mitigation

1. Restore `partner-v2` in `auth-gateway`'s allowed issuer configuration, or revert `AUTH-2026-0318` through the approved rollback mechanism.
2. Refresh/invalidate the affected JWKS cache namespace after the configuration correction.
3. Avoid routing failing checkout traffic through an auth configuration that still rejects `partner-v2`; do not bypass token validation.

## Verification

1. Validate a known-good `partner-v2` token at `auth-gateway`; confirm no `issuer_not_allowed` or `allowed_issuers=partner-v1` errors.
2. Run a synthetic checkout through payment authorization and confirm the corresponding payment and checkout requests succeed.
3. Confirm HTTP 401 rates for `auth-gateway`, `payment-api`, and `checkout-web` fall back toward the `14:00Z` baseline, and checkout latency returns toward baseline.
4. Confirm a successful order reaches downstream order processing without introducing database errors.
5. Review deployment configuration to ensure issuer and JWKS namespace changes are rolled out atomically and add a pre-deployment mismatch check.
