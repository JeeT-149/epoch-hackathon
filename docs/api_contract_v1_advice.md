# Frozen API Contract: `/v1/advice` (WhatsApp & Voice Interface Specification)

This document freezes the request and response contract for the `/v1/advice` decision endpoint. All downstream conversational UI (WhatsApp bot, Twilio voice agents, and web dashboards) must integrate against this specification.

## 1. Canonical Recommendation Statuses

The decision engine outputs one of exactly five statuses:

| Status | Meaning | Voice / WhatsApp Prompt Guidance |
| :--- | :--- | :--- |
| `ACCEPT_OFFER` | Trader's farmgate offer meets or beats mandi net return (accounting for transport, loading, mandi fees, and travel hassle buffer). | "Accept the buyer's offer on your farm. It beats traveling to the mandi after transport and fees." |
| `SWITCH_MARKET_NOW` | Selling today at an alternative (neighboring) mandi yields higher net return than your nearest mandi by more than the switching hurdle (`min_gain_to_switch_rs`). | "Sell today, but take your produce to {mandi_id} instead of {nearest_mandi}. Net gain is +₹{gain}/quintal." |
| `WAIT_WITH_TRIGGER` | Holding produce and monitoring market triggers yields higher expected return than selling today by more than the holding hurdle (`min_gain_to_hold_rs`). | "Hold your crop and watch for prices to reach ₹{target_price}. We will alert you immediately when to sell." |
| `SELL_NOW_NEAREST` | Immediate sale at your nearest local mandi is the optimal or safest choice (or holding risk/spoilage outweighs gains). | "Sell today at your local mandi ({mandi_id}). Holding is not advantageous." |
| `NO_CONFIDENT_ADVICE` | Market policy shock detected (price spike/crash |z| ≥ 3.0), confidence below hurdle, or data quality too low. | "Market conditions are unusually volatile or data is uncertain. Hold sales decisions until market settles." |

---

## 2. Mandatory Governance Rules (ADR-001)

1. **Headline ₹ Claims**:
   - `headline_gain_claim` is populated **ONLY for crops with real prices** (`price_source == "real"`, currently **Soybean**).
   - For **Onion** and **Tomato**, `headline_gain_claim` is strictly `null`. Downstream bots must never announce speculative rupee gains for synthetic crops.
2. **Simulation Notice**:
   - For **Onion** and **Tomato**, `is_synthetic: true`, `price_source: "synthetic"`, and `simulation_notice` is populated.
   - `advice_message` carries `[SIMULATED PRICES: Onion/Tomato prices are simulated by human decision (time constraint). Real-world headline ₹ claims disabled.]`.
3. **Demo Ready Flag**:
   - `demo_ready: false` whenever any unverified economic parameter remains in `docs/assumptions_register.md`. Downstream interfaces must show appropriate test/disclaimer badges.

---

## 3. Sample Requests & Responses

### Request (Soybean Standard)
```json
POST /v1/advice HTTP/1.1
Content-Type: application/json

{
  "crop": "soybean",
  "quantity_q": 25.0,
  "village": {
    "text": "Dewas",
    "lat": 22.96,
    "lon": 76.05
  },
  "cash_deadline_days": 10
}
```

### Response (Soybean Real - `SELL_NOW_NEAREST`)
```json
{
  "status": "SELL_NOW_NEAREST",
  "recommendation": "SELL_NOW_NEAREST",
  "crop": "soybean",
  "is_synthetic": false,
  "price_source": "real",
  "confidence": "MEDIUM",
  "confidence_score": 0.628,
  "advice_message": "Recommendation: SELL_NOW_NEAREST at madhy_dewas_dewas. Expected net return: ₹4523/q.",
  "headline_gain_claim": null,
  "simulation_notice": null,
  "demo_ready": false,
  "best_option": {
    "mandi_id": "madhy_dewas_dewas",
    "days_from_now": 0,
    "sell_date": "2026-10-03",
    "expected_net_return_per_q": 4523.45
  },
  "trader_offer_comparison": {},
  "reasoning": [
    "Forecast gating rule: Model did not beat baseline or pass calibration gate. Answering 'WHERE' to sell today only; 'WHEN' (hold) recommendations are disabled.",
    "Best net return is today at madhy_dewas_dewas."
  ],
  "disclaimers": [
    "⚠ Modal price is a market-level reference, not a guaranteed realisation price. Actual prices received by a specific farmer may differ.",
    "This output is decision support under uncertainty. No guaranteed profit or exact price realisation is implied.",
    "⚠ DEMO NOT READY: One or more economic parameters are marked PLACEHOLDER and have not been verified from field data. Numbers are illustrative only."
  ],
  "meta": {
    "pricing_rule": "Headline ₹ claims allowed only for crops with real prices (ADR-001)",
    "modal_price_proxy_note": "Modal price is a market-level reference, not a guaranteed realisation price."
  }
}
```

---

### Request (Onion with Farmgate Trader Offer)
```json
POST /v1/advice HTTP/1.1
Content-Type: application/json

{
  "crop": "onion",
  "quantity_q": 30.0,
  "village": {
    "text": "Lasalgaon",
    "lat": 20.14,
    "lon": 74.23
  },
  "trader_offer_per_q": 2600.0,
  "cash_deadline_days": 14
}
```

### Response (Onion Synthetic - `ACCEPT_OFFER`)
```json
{
  "status": "ACCEPT_OFFER",
  "recommendation": "ACCEPT_OFFER",
  "crop": "onion",
  "is_synthetic": true,
  "price_source": "synthetic",
  "confidence": "LOW",
  "confidence_score": 0.439,
  "advice_message": "[SIMULATED PRICES: Onion prices are simulated by human decision (time constraint). Real-world headline ₹ claims disabled.] Recommendation: ACCEPT_OFFER at mahar_nashik_lasalgaon. Note: Price levels for onion are synthetic simulation benchmarks.",
  "headline_gain_claim": null,
  "simulation_notice": "SIMULATED PRICES: Onion price series are synthetic by human decision (time constraint, ADR-001). Real-world headline ₹ claims are disabled.",
  "demo_ready": false,
  "best_option": {
    "mandi_id": "mahar_nashik_lasalgaon",
    "days_from_now": 0,
    "sell_date": "2026-10-03",
    "expected_net_return_per_q": 2473.67
  },
  "trader_offer_comparison": {
    "trader_offer_per_q": 2600.0,
    "mandi_net_return_today": 2473.67,
    "parity_buffer_per_q": 10.0,
    "difference_per_q": -136.33,
    "recommendation": "accept_trader"
  },
  "reasoning": [
    "Trader offer (₹2600.0/q) meets or beats mandi net return today (₹2474/q). Consider accepting on farm.",
    "Data provenance notice: Onion prices are simulated by human decision (time constraint). Real-world headline ₹ claims are disabled per ADR-001."
  ],
  "disclaimers": [
    "⚠ Modal price is a market-level reference, not a guaranteed realisation price.",
    "⚠ SIMULATED PRICES: Price series for this crop are synthetic by human decision (time constraint, ADR-001). Headline ₹ claims are disabled. All numbers are simulation benchmarks."
  ]
}
```
