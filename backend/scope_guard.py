import re

# Keywords related to agriculture, selling, crops, quantities, and locations in Marathi, Hindi, English
AGRICULTURE_KEYWORDS = [
    "kanda", "pyaz", "onion", "crop", "peek", "pik", "sheti",
    "कांदा", "प्याज़", "प्याज", "दुंगरी", "dungri",
    "tomato", "tamatar", "tameta", "टोमॅटो", "टमाटर",
    "soybean", "soya", "soyabean", "सोयाबीन", "kapus", "cotton", "tur", "harbhara", "chana", "jwari", "bajri", "wheat", "gavhu",
    "quintal", "quintals", "क्विंटल", "क्विंटल्स", "kg", "kilo", "किलो", "kilogram", "ton", "टन", "praman", "quantity",
    "farmer", "शेतकरी", "किसान", "mandi", "मंडी", "बाजार", "बाजारभाव", "market",
    "trader", "व्यापारी", "वापारी", "buyer", "खरेदीदार",
    "offer", "भाव", "दर", "price", "किंमत", "विक्री", "बेचना", "sell", "विकणे", "vikry", "vikaycha", "vikne",
    "storage", "साठवण", "गोदाम", "sathvan",
    "cash", "रोख", "पैसे", "payment", "pese", "paise",
    "deadline", "दिवस", "nondni", "gaon", "village", "madhe", "ahe", "majhyakade", "deto", "rate"
]

def is_in_scope(message: str) -> bool:
    """
    Determines if the message is related to agricultural selling.
    STEP 1: High-confidence deterministic rejection of clearly unrelated requests.
    """
    msg_lower = message.lower()
    
    has_agri = any(kw in msg_lower for kw in AGRICULTURE_KEYWORDS)
    
    # Check for direct prompt injections or obvious unrelated questions
    has_injection = any(injection in msg_lower for injection in [
        "ignore all previous instructions", "ignore previous instructions", 
        "write python", "write me a", "react dashboard", 
        "system prompt", "api key", "translate", "tell me a joke",
        "calculate", "what is the capital"
    ])
    
    if has_injection and not has_agri:
        return False
        
    if has_agri:
        return True
        
    # Block very short gibberish
    if len(message.strip()) < 2:
        return False
        
    return True
