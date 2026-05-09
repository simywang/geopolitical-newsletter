import os

# --- API Keys ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
GLM_API_KEY = os.getenv("GLM_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
BUTTONDOWN_API_KEY = os.getenv("BUTTONDOWN_API_KEY", "")
STEPFUN_API_KEY = os.getenv("STEPFUN_API_KEY", "")

# --- AI Provider & Model ---
AI_MODEL = os.getenv("AI_MODEL", "claude").lower()  # claude | deepseek | glm
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
GLM_MODEL = os.getenv("GLM_MODEL", "glm-4.7-flash")

# --- Behavior Flags ---
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
SEND_MODE = os.getenv("SEND_MODE", "draft").lower()  # draft | send

# --- Podcast ---
PODCAST_ENABLED = os.getenv("PODCAST_ENABLED", "false").lower() == "true"
PODCAST_DRY_RUN = os.getenv("PODCAST_DRY_RUN", "true").lower() == "true"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "simywang/geopolitical-newsletter")
PODCAST_SITE_URL = os.getenv("PODCAST_SITE_URL", "https://geopolitical-newsletter-three.vercel.app")

# Volcengine TTS — primary (豆包语音合成, V3 HTTP API, API Key only)
VOLC_API_KEY = os.getenv("VOLC_API_KEY", "")
VOLC_TTS_RESOURCE_ID = os.getenv("VOLC_TTS_RESOURCE_ID", "seed-tts-2.0")
VOLC_VOICE_A = os.getenv("VOLC_VOICE_A", "en_female_dacey_uranus_bigtts")  # Dacey — Sarah
VOLC_VOICE_B = os.getenv("VOLC_VOICE_B", "en_male_tim_uranus_bigtts")      # Tim — James

# OpenAI TTS — fallback (used when VOLC_API_KEY is not set)
PODCAST_TTS_MODEL = os.getenv("PODCAST_TTS_MODEL", "tts-1-hd")
PODCAST_VOICE_A = os.getenv("PODCAST_VOICE_A", "nova")   # Sarah — Host A
PODCAST_VOICE_B = os.getenv("PODCAST_VOICE_B", "onyx")   # James — Host B

# --- Fetcher Settings ---
MAX_ARTICLES_PER_FEED = 10
ARTICLES_TO_SELECT = 5
LOOKBACK_HOURS = 24

# --- Buttondown ---
BUTTONDOWN_API_BASE = "https://api.buttondown.email/v1"
BUTTONDOWN_API_KEY_NL = os.getenv("BUTTONDOWN_API_KEY_NL", "")
BUTTONDOWN_API_KEY_ZH = os.getenv("BUTTONDOWN_API_KEY_ZH", "")

# Languages to publish (comma-separated: en,nl,zh). en is always included.
PUBLISH_LANGUAGES = [l.strip() for l in os.getenv("PUBLISH_LANGUAGES", "en").split(",") if l.strip()]

# --- RSS Sources ---
RSS_FEEDS = [
    # Macro / geopolitical (kept lean — wars, sanctions, shipping disruptions)
    {"url": "https://feeds.reuters.com/reuters/businessNews", "name": "Reuters Business"},
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "name": "BBC World"},

    # Energy
    {"url": "https://oilprice.com/rss/main", "name": "OilPrice.com"},
    {"url": "https://www.eia.gov/rss/news.xml", "name": "EIA News"},

    # Agriculture / soft commodities
    {"url": "https://www.agrimoney.com/feed/", "name": "Agrimoney"},
    {"url": "https://www.icco.org/feed/", "name": "ICCO"},
    {"url": "https://dailycoffeenews.com/feed/", "name": "Daily Coffee News"},
    {"url": "https://perfectdailygrind.com/feed/", "name": "Perfect Daily Grind"},

    # Weather / climate
    {"url": "https://droughtmonitor.unl.edu/rss.xml", "name": "NOAA Drought Monitor"},
    {"url": "https://public.wmo.int/en/rss.xml", "name": "WMO"},

    # Google News — commodity keywords
    {"url": "https://news.google.com/rss/search?q=cocoa+futures+west+africa&hl=en", "name": "Google News: Cocoa"},
    {"url": "https://news.google.com/rss/search?q=crude+oil+supply+OPEC&hl=en", "name": "Google News: Oil"},
    {"url": "https://news.google.com/rss/search?q=wheat+prices+Black+Sea&hl=en", "name": "Google News: Wheat"},
    {"url": "https://news.google.com/rss/search?q=LNG+shipping+reroute&hl=en", "name": "Google News: LNG"},
    {"url": "https://news.google.com/rss/search?q=drought+Brazil+soybean&hl=en", "name": "Google News: Brazil Soy"},
    {"url": "https://news.google.com/rss/search?q=El+Nino+crop+damage&hl=en", "name": "Google News: El Nino"},
    {"url": "https://news.google.com/rss/search?q=arabica+coffee+futures+brazil&hl=en", "name": "Google News: Coffee"},
    {"url": "https://news.google.com/rss/search?q=EUDR+cocoa+coffee+supply+chain&hl=en", "name": "Google News: EUDR"},
]

# --- Validation ---
_REQUIRED = {
    "BUTTONDOWN_API_KEY": BUTTONDOWN_API_KEY,
}
_PROVIDER_KEYS = {
    "claude": ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY),
    "deepseek": ("DEEPSEEK_API_KEY", DEEPSEEK_API_KEY),
    "glm": ("GLM_API_KEY", GLM_API_KEY),
}

def validate():
    ok = True
    for name, val in _REQUIRED.items():
        if not val:
            print(f"[config] WARNING: {name} is not set")
            ok = False
    key_name, key_val = _PROVIDER_KEYS.get(AI_MODEL, ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY))
    if not key_val:
        print(f"[config] WARNING: {key_name} is not set (required for AI_MODEL={AI_MODEL})")
        ok = False
    if AI_MODEL not in ("claude", "deepseek", "glm"):
        print(f"[config] WARNING: Unknown AI_MODEL '{AI_MODEL}', defaulting to claude")
    if SEND_MODE not in ("draft", "send"):
        print(f"[config] WARNING: Unknown SEND_MODE '{SEND_MODE}', defaulting to draft")
    if PODCAST_ENABLED and not ANTHROPIC_API_KEY and not DEEPSEEK_API_KEY and not GLM_API_KEY:
        print("[config] WARNING: No AI API key set (required for podcast dialogue generation)")
        ok = False
    if PODCAST_ENABLED and not VOLC_API_KEY and not OPENAI_API_KEY:
        print("[config] WARNING: Neither VOLC_API_KEY nor OPENAI_API_KEY is set (one required for podcast TTS)")
        ok = False
    if PODCAST_ENABLED and not PODCAST_DRY_RUN and not GITHUB_TOKEN:
        print("[config] WARNING: GITHUB_TOKEN is not set (required to upload podcast to Releases)")
        ok = False
    return ok
