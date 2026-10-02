# Sell Smart Project Rules

## Synthetic Crops & Pricing Governance Rule
1. **Headline ₹ Claims**: Headline ₹ claims (e.g. "+₹90/quintal") are allowed **ONLY for crops with real prices** (`price_source == "real"`, currently Soybean).
2. **Synthetic Perishables**: Onion and Tomato price series are synthetic by human decision (time constraint). Every advice response, API output (`/v1/advice`), and report header involving Onion or Tomato MUST visibly disclose:
   `[SIMULATED PRICES: Onion/Tomato prices are synthetic by human decision (time constraint). Real-world headline ₹ claims disabled.]`
3. **Data Tagging**: All rows and advice payloads must carry `is_synthetic: bool` and `price_source: "real" | "synthetic"`.
