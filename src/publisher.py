import sys
import json
import requests

sys.path.insert(0, __file__.rsplit("/src/", 1)[0])
import config

# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

_SPOTIFY_SVG = '<svg width="15" height="15" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path fill="#000000" d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/></svg>'

_CSS = """
body { font-family: Georgia, 'Times New Roman', serif; background: #e8e4dc; margin: 0; padding: 0; }
.wrapper { max-width: 680px; margin: 0 auto; background: #ffffff; }

.header { background: #0a0a0a; border-top: 3px solid #755b00; }
.header-main { padding: 26px 40px 28px; }
.header-brand { margin: 0 0 10px 0; font-size: 22px; font-weight: 700; letter-spacing: 0.3px; color: #ffffff; font-family: Georgia, serif; }
.header-meta { font-size: 12px; color: rgba(255,255,255,0.45); font-family: Arial, sans-serif; letter-spacing: 0.5px; margin-bottom: 14px; }
.header-meta .issue { color: #755b00; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; }
.spotify-header-btn { display: inline-flex; align-items: center; gap: 7px; text-decoration: none; background: #1DB954; padding: 7px 14px; }
.spotify-header-btn span { font-size: 12px; color: #000000; font-family: Arial, sans-serif; font-weight: 700; letter-spacing: 0.3px; }

.overview { background: #fffbf0; border-left: 4px solid #755b00; padding: 20px 40px; }
.overview-label { font-size: 10px; font-family: Arial, sans-serif; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; color: #755b00; margin: 0 0 8px 0; }
.overview p { margin: 0; font-size: 15px; line-height: 1.75; color: #2a2a2a; }

.articles { padding: 0 40px; background: #ffffff; }
.article { border-bottom: 1px solid #e8e4dc; padding: 24px 0; }
.article:last-child { border-bottom: none; }
.article-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.article-num { font-size: 11px; font-weight: 700; color: #755b00; font-family: Arial, sans-serif; }
.article-source { font-size: 10px; background: #0a0a0a; color: #ffffff; padding: 2px 8px; font-family: Arial, sans-serif; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; }
.article h3 { margin: 0 0 10px 0; font-size: 17px; line-height: 1.45; }
.article h3 a { color: #0a0a0a; text-decoration: none; border-bottom: 1px solid transparent; }
.article h3 a:hover { border-bottom-color: #755b00; }
.article p { margin: 0 0 10px 0; font-size: 14px; line-height: 1.8; color: #444444; font-family: Arial, sans-serif; }
.market-impact { background: #fffbf0; border-left: 3px solid #755b00; padding: 10px 14px; margin-top: 10px; }
.market-impact strong { font-size: 10px; font-family: Arial, sans-serif; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #755b00; display: block; margin-bottom: 4px; }
.market-impact p { margin: 0; font-size: 13px; color: #555; line-height: 1.6; font-family: Arial, sans-serif; }
.second-order { background: #f5f5f5; border-left: 3px solid #aaaaaa; padding: 10px 14px; margin-top: 8px; }
.second-order strong { font-size: 10px; font-family: Arial, sans-serif; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #888; display: block; margin-bottom: 4px; }
.second-order p { margin: 0; font-size: 13px; color: #666; line-height: 1.6; font-family: Arial, sans-serif; }
.watch-next { background: #fff; border: 1px dashed #ccb97a; padding: 8px 14px; margin-top: 8px; display: flex; align-items: flex-start; gap: 8px; }
.watch-next-label { font-size: 10px; font-family: Arial, sans-serif; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #755b00; white-space: nowrap; margin-top: 2px; }
.watch-next p { margin: 0; font-size: 13px; color: #555; line-height: 1.6; font-family: Arial, sans-serif; }

.watch-week { background: #fafaf8; border-top: 2px solid #755b00; padding: 24px 40px; }
.watch-week-label { font-size: 10px; font-family: Arial, sans-serif; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; color: #755b00; margin: 0 0 14px 0; }
.watch-week-list { margin: 0; padding: 0; list-style: none; }
.watch-week-list li { display: flex; gap: 12px; padding: 8px 0; border-bottom: 1px solid #e8e4dc; font-family: Arial, sans-serif; font-size: 13px; line-height: 1.6; color: #444; }
.watch-week-list li:last-child { border-bottom: none; }
.watch-week-list li strong { color: #0a0a0a; white-space: nowrap; min-width: 0; }

.podcast-banner { background: #0a0a0a; padding: 22px 40px; display: flex; align-items: center; justify-content: space-between; gap: 20px; }
.podcast-banner-label { font-size: 10px; color: rgba(255,255,255,0.4); font-family: Arial, sans-serif; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 5px 0; }
.podcast-banner-title { font-size: 14px; color: #ffffff; margin: 0; font-family: Georgia, serif; line-height: 1.4; }
.podcast-btn { display: inline-flex; align-items: center; gap: 8px; background: #1DB954; color: #000000; padding: 11px 20px; font-family: Arial, sans-serif; font-size: 12px; font-weight: 700; text-decoration: none; white-space: nowrap; letter-spacing: 0.3px; flex-shrink: 0; }

.footer { background: #fafaf8; border-top: 1px solid #e8e4dc; padding: 18px 40px; text-align: center; }
.footer p { margin: 0 0 5px 0; font-size: 11px; font-family: Arial, sans-serif; color: #aaa; line-height: 1.6; }
.footer a { color: #755b00; text-decoration: none; font-weight: 600; }
.footer a:hover { text-decoration: underline; }
.footer-sep { color: #ccc; margin: 0 6px; }
"""

def render_html(data: dict, date_str: str) -> str:
    articles_html = ""
    for i, article in enumerate(data.get("articles", []), 1):
        impact = (article.get("market_impact") or article.get("why_it_matters", "")).strip()
        second = article.get("second_order_effect", "").strip()
        watch = article.get("watch_next", "").strip()

        impact_block = (
            f'<div class="market-impact"><strong>Market Impact</strong><p>{impact}</p></div>'
            if impact else ""
        )
        second_block = (
            f'<div class="second-order"><strong>Second-Order Effect</strong><p>{second}</p></div>'
            if second else ""
        )
        watch_block = (
            f'<div class="watch-next"><span class="watch-next-label">Watch&nbsp;Next</span><p>{watch}</p></div>'
            if watch else ""
        )
        articles_html += f"""
        <div class="article">
          <div class="article-meta">
            <span class="article-num">#{i:02d}</span>
            <span class="article-source">{article.get("source", "")}</span>
          </div>
          <h3><a href="{article.get("url", "#")}">{article.get("title", "")}</a></h3>
          <p>{article.get("summary", "")}</p>
          {impact_block}
          {second_block}
          {watch_block}
        </div>
        """

    overview = data.get("overview", "")
    episode_title = data.get("episode_title", f"Commodity Frontier — {date_str}")

    watch_items = data.get("watch_this_week", [])
    if watch_items:
        items_html = "".join(
            f'<li><strong>{w.get("item", "")}</strong> — {w.get("detail", "")}</li>'
            for w in watch_items
        )
        watch_section = f"""
  <div class="watch-week">
    <p class="watch-week-label">What to Watch This Week</p>
    <ul class="watch-week-list">{items_html}</ul>
  </div>"""
    else:
        watch_section = ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Commodity Frontier News — {date_str}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrapper">

  <div class="header">
    <div class="header-main">
      <h1 class="header-brand">Commodity Frontier News</h1>
      <div class="header-meta">
        {date_str} &nbsp;·&nbsp; <span class="issue">Daily Briefing</span> &nbsp;·&nbsp; Creator Ximin
      </div>
      <a class="spotify-header-btn" href="https://open.spotify.com/show/033dFGpcN8nVTjTjR3uOuE">
        {_SPOTIFY_SVG}
        <span>Listen on Spotify</span>
      </a>
    </div>
  </div>

  <div class="overview">
    <p class="overview-label">Market Intelligence Brief</p>
    <p>{overview}</p>
  </div>

  <div class="articles">
    {articles_html}
  </div>

  {watch_section}

  <div class="podcast-banner">
    <div>
      <p class="podcast-banner-label">Commodity Frontier · Daily Podcast</p>
      <p class="podcast-banner-title">{episode_title}</p>
    </div>
    <a class="podcast-btn" href="https://open.spotify.com/show/033dFGpcN8nVTjTjR3uOuE">
      {_SPOTIFY_SVG}
      Open in Spotify
    </a>
  </div>

  <div class="footer">
    <p>
      <a href="https://geopolitical-newsletter-three.vercel.app">Commodity Frontier News</a>
      <span class="footer-sep">·</span>
      <a href="https://open.spotify.com/show/033dFGpcN8nVTjTjR3uOuE">Listen on Spotify</a>
      <span class="footer-sep">·</span>
      <a href="{{{{ unsubscribe_url }}}}">Unsubscribe</a>
    </p>
    <p>Daily market intelligence for commodity traders and supply chain professionals.</p>
  </div>

</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Buttondown API
# ---------------------------------------------------------------------------

def _headers() -> dict:
    return {"Authorization": f"Token {config.BUTTONDOWN_API_KEY}"}


def _create_draft(html: str, subject: str, lang: str) -> str:
    payload = {"subject": subject, "body": html, "status": "draft"}
    if lang != "en":
        payload["filters"] = [{"type": "tag", "value": f"lang:{lang}"}]
    resp = requests.post(
        f"{config.BUTTONDOWN_API_BASE}/emails",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    email_id = resp.json()["id"]
    print(f"[publisher] Draft created: id={email_id} (lang={lang})")
    return email_id


def _trigger_send(email_id: str) -> None:
    resp = requests.patch(
        f"{config.BUTTONDOWN_API_BASE}/emails/{email_id}",
        headers=_headers(),
        json={"status": "about_to_send"},
        timeout=30,
    )
    resp.raise_for_status()
    print(f"[publisher] Email queued for sending: id={email_id}")


def publish(data: dict, date_str: str, subject: str, lang: str = "en") -> None:
    html = render_html(data, date_str)

    if config.DRY_RUN:
        print(f"[publisher] DRY_RUN=true — skipping Buttondown API call [{lang}]")
        print("[publisher] HTML preview (first 500 chars):")
        print(html[:500])
        return

    email_id = _create_draft(html, subject, lang)

    if config.SEND_MODE == "send":
        _trigger_send(email_id)
        print(f"[publisher] Newsletter sent [{lang}]: '{subject}'")
    else:
        print(f"[publisher] Draft saved [{lang}] (SEND_MODE=draft). Subject: '{subject}'")
