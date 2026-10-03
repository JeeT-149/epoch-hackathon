import os
import yaml
from .schemas import AdviceResponse

def format_advice(response: AdviceResponse, config_path: str = None) -> str:
    """
    Deterministically formats an AdviceResponse into a user-facing string
    using templates from messages.yaml.
    """
    if not config_path:
        base_dir = os.path.dirname(__file__)
        config_path = os.path.join(base_dir, "config", "messages.yaml")

    with open(config_path, "r", encoding="utf-8") as f:
        messages_config = yaml.safe_load(f)

    # Convert the pydantic message to dict and extract relevant fields
    template_id = response.message.template_id
    language = response.message.language
    slots = response.message.slots.model_dump(exclude_none=True)

    if template_id not in messages_config:
        return f"Error: Template {template_id} not found."

    template_node = messages_config[template_id]
    
    if language not in template_node:
        language = "en"  # fallback to english if translation missing

    template_str = template_node.get(language, "")

    try:
        formatted_text = template_str.format(**slots)
        
        # Append proxy footer if caution flag exists
        if "modal_price_proxy" in response.caution_flags:
            footer_node = messages_config.get("footer_proxy", {})
            footer_str = footer_node.get(language, footer_node.get("en", ""))
            if footer_str:
                formatted_text += "\n\n" + footer_str

        return formatted_text
    except KeyError as e:
        return f"Error: Missing slot {e} for template {template_id}."
