# Pricing & Synthetic Crop Rules (Antigravity Rule)

## Rule: Headline ₹ Claims Restriction
Headline ₹ claims (e.g., "Gain +₹90/quintal", "Earn an extra ₹150/q by holding") are allowed **ONLY for crops with real prices** (`price_source == "real"`).

### Provenance Mapping:
- **Soybean**: Real Agmarknet prices (`price_source: "real"`, `is_synthetic: false`). Realized historical comparisons and headline ₹ claims are permitted when backed by out-of-sample backtests.
- **Onion**: Synthetic prices by human decision (`price_source: "synthetic"`, `is_synthetic: true`).
- **Tomato**: Synthetic prices by human decision (`price_source: "synthetic"`, `is_synthetic: true`).

### Mandatory Directives for Onion and Tomato:
1. **Headline ₹ Claims are Forbidden**: Never present simulated price increases as realized real-money returns or guarantee headline ₹ claims for Onion or Tomato.
2. **Visible Simulation Disclosure**: Every advice response, report header, and API output (`/v1/advice`) for Onion or Tomato must visibly state:
   `[SIMULATED PRICES] This crop uses a synthetic price series by human decision (time constraint). Real-world headline ₹ claims are disabled.`
3. **Data Tagging**: Every record and response must explicitly carry `is_synthetic: true` and `price_source: "synthetic"`.
