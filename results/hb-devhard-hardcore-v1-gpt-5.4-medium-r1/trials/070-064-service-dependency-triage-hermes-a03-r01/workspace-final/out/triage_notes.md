# Production checkout incident triage

## Summary

Directly observed fact: The user-visible failure path is checkout-web -> payment-api -> auth-gateway.

Directly observed fact: checkout-web logs show order submission failures as HTTP 401s from payment-api with `invalid issuer` messaging.
Source: /workspace/in/logs/checkout-web.log

Directly observed fact: payment-api logs attribute the failure to auth-gateway rejecting tokens with `issuer_not_allowed` / `invalid_issuer`.
Source: /workspace/in/logs/payment-api.log

Directly observed fact: auth-gateway deployed change `AUTH-2026-0318` at 14:05:12Z, then logged a JWKS cache miss and `validation failed reason=issuer_not_allowed token_issuer=partner-v2 allowed_issuers=partner-v1`.
Source: /workspace/in/logs/auth-gateway.log

Inference: The most likely root cause is a bad auth-gateway rollout (`AUTH-2026-0318`) that changed issuer/JWKS settings to partner-v2 without updating the effective allowed issuer set, causing partner-v2 tokens to be rejected and cascading 401s back through payment-api to checkout-web.

## Dependency path from user impact to root cause

1. Directly observed fact: `checkout-web` is the entrypoint and depends on `payment-api`.
   Source: /workspace/in/topology.json
2. Directly observed fact: `payment-api` depends on `auth-gateway`.
   Source: /workspace/in/topology.json
3. Directly observed fact: checkout submission failed in `checkout-web` because `payment-api` returned auth failure / invalid issuer.
   Source: /workspace/in/logs/checkout-web.log
4. Directly observed fact: `payment-api` rejected payment creation because `auth-gateway` returned `issuer_not_allowed`.
   Source: /workspace/in/logs/payment-api.log
5. Directly observed fact: `auth-gateway` itself logged the mismatched configuration after deploying `AUTH-2026-0318`.
   Source: /workspace/in/logs/auth-gateway.log
6. Inference: Since the auth-gateway change precedes the errors and the metrics show synchronized 401 spikes on auth-gateway, payment-api, and checkout-web, auth-gateway is the originating failure point.
   Source support: /workspace/in/metrics/service_metrics.csv, /workspace/in/topology.json

## Key evidence

- Directly observed fact: At 14:10:00Z, http_401_rate increased to 28.4 on auth-gateway, 21.2 on payment-api, and 18.7 on checkout-web.
  Source: /workspace/in/metrics/service_metrics.csv
- Directly observed fact: `orders-db` had high CPU during vacuum, but also logged `p95_query_ms=35`, `errors=0`, and `no failed checkout transaction reached orders-db for request_id=req-8812`.
  Source: /workspace/in/logs/orders-db.log
- Directly observed fact: `cdn-edge` had image-related 5xx noise, while checkout-web logged `static assets served normally after retry; user checkout flow still blocked`.
  Source: /workspace/in/metrics/service_metrics.csv and /workspace/in/logs/checkout-web.log

## Excluded red herrings

1. Directly observed fact: orders-db showed CPU spike from vacuum activity.
   Inference: Not primary cause, because the failed checkout request never reached orders-db and query latency/errors stayed normal.
   Sources: /workspace/in/logs/orders-db.log, /workspace/in/logs/payment-api.log

2. Directly observed fact: cdn-edge showed elevated 5xx on static assets.
   Inference: Not primary cause, because the checkout flow remained blocked by auth failures even after static assets recovered.
   Sources: /workspace/in/metrics/service_metrics.csv, /workspace/in/logs/checkout-web.log

3. Directly observed fact: payment-api is the immediate upstream seen by checkout-web.
   Inference: Not the originating cause, because payment-api explicitly reports auth-gateway token validation failure as the reason for rejection.
   Source: /workspace/in/logs/payment-api.log

## Immediate mitigation

- Immediately roll back change `AUTH-2026-0318` on auth-gateway, or restore `allowed_issuers` to include `partner-v2`.
- Clear/rebuild the affected JWKS cache namespace so auth-gateway stops falling back to stale `partner-v1` expectations.
- After config correction, re-run a checkout using a partner-v2 token path.

## Verification steps

1. Directly verify auth-gateway logs no longer emit `issuer_not_allowed` for partner-v2 tokens.
2. Directly verify payment-api no longer returns `auth_result=invalid_issuer` during payment creation.
3. Directly verify checkout-web no longer logs `submit_order failed status=401 upstream=payment-api` for the same flow.
4. Verify service metrics return toward baseline, especially 401 rates on auth-gateway, payment-api, and checkout-web.
5. Inference check: if 401s clear without any database or CDN changes, that further confirms auth-gateway configuration was the true root cause.

## Fixture files cited

- /workspace/in/topology.json
- /workspace/in/metrics/service_metrics.csv
- /workspace/in/logs/checkout-web.log
- /workspace/in/logs/payment-api.log
- /workspace/in/logs/auth-gateway.log
- /workspace/in/logs/orders-db.log
