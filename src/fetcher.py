import sys
import html
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

import feedparser
from dateutil import parser as dateutil_parser

sys.path.insert(0, __file__.rsplit("/src/", 1)[0])
import config

HEADERS = {"User-Agent": "GeopoliticalBriefing/1.0 (+newsletter)"}


def _parse_time(entry) -> datetime | None:
    """Try multiple time fields to get a timezone-aware datetime."""
    # 1. feedparser's parsed struct → datetime
    for field in ("published_parsed", "updated_parsed"):
        struct = getattr(entry, field, None)
        if struct:
            try:
                return datetime(*struct[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    # 2. Raw string → dateutil
    for field in ("published", "updated"):
        raw = getattr(entry, field, None)
        if raw:
            try:
                dt = dateutil_parser.parse(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
    return None


def _clean_html(text: str) -> str:
    """Strip HTML tags and decode entities."""
    if not text:
        return ""
    import re
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return " ".join(text.split())


def _source_name(feed, feed_cfg: dict) -> str:
    return feed_cfg.get("name") or urlparse(feed_cfg["url"]).netloc


def fetch_all() -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.LOOKBACK_HOURS)
    seen_urls: set[str] = set()
    articles: list[dict] = []

    for feed_cfg in config.RSS_FEEDS:
        try:
            feed = feedparser.parse(
                feed_cfg["url"],
                request_headers=HEADERS,
            )
            source = _source_name(feed.feed, feed_cfg)
            count = 0

            for entry in feed.entries:
                if count >= config.MAX_ARTICLES_PER_FEED:
                    break

                url = getattr(entry, "link", None)
                if not url or url in seen_urls:
                    continue

                pub_time = _parse_time(entry)
                if pub_time and pub_time < cutoff:
                    continue

                title = _clean_html(getattr(entry, "title", ""))
                description = _clean_html(
                    getattr(entry, "summary", "")
                    or getattr(entry, "description", "")
                )
                if not title:
                    continue

                seen_urls.add(url)
                articles.append({
                    "title": title,
                    "description": description[:500],
                    "source": source,
                    "url": url,
                    "published_at": pub_time.isoformat() if pub_time else "unknown",
                })
                count += 1

            print(f"[fetcher] {source}: {count} articles")

        except Exception as e:
            print(f"[fetcher] ERROR fetching {feed_cfg['url']}: {e}")

    print(f"[fetcher] Total: {len(articles)} articles from {len(config.RSS_FEEDS)} feeds")
    return articles
