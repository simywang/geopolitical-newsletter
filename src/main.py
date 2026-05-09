import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from src.fetcher import fetch_all
from src.summarizer import summarize
from src.publisher import publish
from src.podcast import generate_podcast, generate_episode_title
from src.market_data import fetch_prices, build_price_context
from src.translator import translate_data


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")


def _date_str() -> str:
    return datetime.now(timezone.utc).strftime("%B %-d, %Y")


def main():
    print(f"[{_ts()}] === Geopolitical Briefing starting ===")
    print(f"[{_ts()}] Provider: {config.AI_MODEL} | SEND_MODE: {config.SEND_MODE} | DRY_RUN: {config.DRY_RUN}")

    config.validate()

    # Step 1: Fetch
    print(f"\n[{_ts()}] Step 1/3 — Fetching articles...")
    articles = fetch_all()
    if not articles:
        print(f"[{_ts()}] ERROR: No articles fetched. Aborting.")
        sys.exit(1)
    if len(articles) < 5:
        print(f"[{_ts()}] WARNING: Only {len(articles)} articles fetched — briefing may be thin.")

    # Step 2: Fetch market prices
    print(f"\n[{_ts()}] Step 2/4 — Fetching market prices...")
    prices = fetch_prices()
    price_context = build_price_context(prices)
    if prices:
        print(f"[{_ts()}] Prices loaded: {', '.join(prices.keys())}")
    else:
        print(f"[{_ts()}] WARNING: No prices fetched — continuing without price context")

    # Step 3: Summarize
    print(f"\n[{_ts()}] Step 3/4 — Summarizing with AI...")
    data = summarize(articles, price_context)

    # Step 4: Publish newsletter (all languages)
    date_str = _date_str()
    episode_title = generate_episode_title(data, date_str)
    data["episode_title"] = episode_title

    lang_subjects = {
        "en": f"Commodity Frontier News — {date_str}",
        "nl": f"Commodity Frontier News — {date_str}",
        "zh": f"大宗商品前沿 — {date_str}",
    }

    print(f"\n[{_ts()}] Step 4/5 — Publishing newsletter ({', '.join(config.PUBLISH_LANGUAGES)})...")
    for lang in config.PUBLISH_LANGUAGES:
        if lang == "en":
            lang_data = data
        else:
            print(f"[{_ts()}] Translating to {lang}...")
            lang_data = translate_data(data, lang)
        publish(lang_data, date_str, lang_subjects.get(lang, lang_subjects["en"]), lang=lang)

    # Step 5: Generate podcast (controlled by PODCAST_ENABLED)
    print(f"\n[{_ts()}] Step 5/5 — Generating podcast...")
    generate_podcast(data, date_str)

    print(f"\n[{_ts()}] === Done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
