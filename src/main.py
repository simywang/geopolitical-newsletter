import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from src.fetcher import fetch_all
from src.summarizer import summarize
from src.publisher import publish


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

    # Step 2: Summarize
    print(f"\n[{_ts()}] Step 2/3 — Summarizing with AI...")
    data = summarize(articles)

    # Step 3: Publish
    date_str = _date_str()
    subject = f"🌍 Geopolitical Briefing — {date_str}"
    print(f"\n[{_ts()}] Step 3/3 — Publishing...")
    publish(data, date_str, subject)

    print(f"\n[{_ts()}] === Done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
