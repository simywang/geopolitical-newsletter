import os

# --- API Keys ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
GLM_API_KEY = os.getenv("GLM_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
BUTTONDOWN_API_KEY = os.getenv("BUTTONDOWN_API_KEY", "")

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
PODCAST_SITE_URL = os.getenv("PODCAST_SITE_URL", "https://geopolitical-newsletter.vercel.app")

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
ARTICLES_TO_SELECT = 8
LOOKBACK_HOURS = 24

# --- Buttondown ---
BUTTONDOWN_API_BASE = "https://api.buttondown.email/v1"

# --- RSS Sources ---
RSS_FEEDS = [
    {"url": "https://feeds.reuters.com/reuters/worldNews", "name": "Reuters"},
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "name": "BBC"},
    {"url": "https://www.aljazeera.com/xml/rss/all.xml", "name": "Al Jazeera"},
    {"url": "https://www.theguardian.com/world/rss", "name": "The Guardian"},
    {"url": "https://feeds.cfr.org/dailybrief", "name": "CFR Daily Brief"},
    {"url": "https://news.google.com/rss/search?q=geopolitical+crisis&hl=en", "name": "Google News: Geopolitical Crisis"},
    {"url": "https://news.google.com/rss/search?q=global+conflict&hl=en", "name": "Google News: Global Conflict"},
    {"url": "https://news.google.com/rss/search?q=international+sanctions&hl=en", "name": "Google News: Sanctions"},
    {"url": "https://news.google.com/rss/search?q=US+China+relations&hl=en", "name": "Google News: US-China"},
    {"url": "https://news.google.com/rss/search?q=Middle+East+war&hl=en", "name": "Google News: Middle East"},
    {"url": "https://news.google.com/rss/search?q=Russia+Ukraine&hl=en", "name": "Google News: Russia-Ukraine"},
    {"url": "https://www.reddit.com/r/geopolitics.rss", "name": "Reddit: r/geopolitics"},
    {"url": "https://www.reddit.com/r/worldnews.rss", "name": "Reddit: r/worldnews"},
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
