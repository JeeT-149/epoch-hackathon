"""
sell_smart.common.disclaimers
Standard disclaimers injected into every farmer-facing output (R9, R11).
"""
MODAL_PRICE_PROXY = (
    "⚠ Modal price is a market-level reference, not a guaranteed realisation price. "
    "Actual prices received by a specific farmer may differ."
)

DECISION_SUPPORT = (
    "This output is decision support under uncertainty. "
    "No guaranteed profit or exact price realisation is implied."
)

PLACEHOLDER_WARNING = (
    "⚠ DEMO NOT READY: One or more economic parameters (spoilage, transport, storage) "
    "are marked PLACEHOLDER and have not been verified from field data. "
    "Numbers are illustrative only."
)

SYNTHETIC_LABEL = "📊 Synthetic inputs were used in this run. See 'Synthetic inputs used' section."


def get_disclaimers(demo_ready: bool = True, has_synthetic: bool = False) -> list[str]:
    out = [MODAL_PRICE_PROXY, DECISION_SUPPORT]
    if not demo_ready:
        out.append(PLACEHOLDER_WARNING)
    if has_synthetic:
        out.append(SYNTHETIC_LABEL)
    return out
