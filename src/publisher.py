import sys
import json
import requests

sys.path.insert(0, __file__.rsplit("/src/", 1)[0])
import config

# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

_CSS = """
body { font-family: Georgia, 'Times New Roman', serif; background: #f9f7f4; margin: 0; padding: 0; }
.wrapper { max-width: 680px; margin: 0 auto; background: #ffffff; }
.header { background: #ffffff; border-bottom: 3px solid #1a1a2e; padding: 32px 40px; }
.header h1 { margin: 0 0 4px 0; font-size: 24px; font-weight: 700; letter-spacing: 0.5px; color: #1a1a2e; }
.header p { margin: 0; font-size: 13px; color: #888888; }
.overview { background: #f0f4ff; border-left: 4px solid #3a5fc8; padding: 20px 40px; }
.overview h2 { margin: 0 0 10px 0; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #3a5fc8; }
.overview p { margin: 0; font-size: 15px; line-height: 1.7; color: #333; }
.articles { padding: 0 40px; }
.article { border-bottom: 1px solid #eeeeee; padding: 28px 0; }
.article:last-child { border-bottom: none; }
.article-meta { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.article-num { font-size: 12px; font-weight: 700; color: #999; }
.article-source { font-size: 11px; background: #eef2ff; color: #3a5fc8; padding: 2px 8px; border-radius: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
.article h3 { margin: 0 0 12px 0; font-size: 17px; line-height: 1.4; }
.article h3 a { color: #1a1a2e; text-decoration: none; }
.article h3 a:hover { text-decoration: underline; }
.article p { margin: 0 0 10px 0; font-size: 14px; line-height: 1.75; color: #444; }
.why { background: #fffbf0; border-left: 3px solid #f0a500; padding: 10px 14px; margin-top: 10px; }
.why strong { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #c07800; display: block; margin-bottom: 4px; }
.why p { margin: 0; font-size: 13px; color: #555; line-height: 1.6; }
.footer { background: #f5f5f5; padding: 24px 40px; text-align: center; font-size: 12px; color: #999; line-height: 1.6; }
.footer a { color: #3a5fc8; text-decoration: none; }
"""

def render_html(data: dict, date_str: str) -> str:
    articles_html = ""
    for i, article in enumerate(data.get("articles", []), 1):
        why = article.get("why_it_matters", "").strip()
        why_block = (
            f'<div class="why"><strong>Why it matters</strong><p>{why}</p></div>'
            if why else ""
        )
        articles_html += f"""
        <div class="article">
          <div class="article-meta">
            <span class="article-num">#{i}</span>
            <span class="article-source">{article.get("source", "")}</span>
          </div>
          <h3><a href="{article.get("url", "#")}">{article.get("title", "")}</a></h3>
          <p>{article.get("summary", "")}</p>
          {why_block}
        </div>
        """

    overview = data.get("overview", "")

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Geopolitical Briefing — {date_str}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>🌍 Geopolitical Briefing</h1>
    <p>{date_str}</p>
  </div>
  <div class="overview">
    <h2>Today's Overview</h2>
    <p>{overview}</p>
  </div>
  <div class="articles">
    {articles_html}
  </div>
  <div class="footer">
    <p>This briefing is generated automatically from public news sources and summarized by AI.<br>
    It is intended for informational purposes only.</p>
    <p><a href="{{{{ unsubscribe_url }}}}">Unsubscribe</a></p>
  </div>
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Buttondown API
# ---------------------------------------------------------------------------

def _headers() -> dict:
    return {"Authorization": f"Token {config.BUTTONDOWN_API_KEY}"}


def _create_draft(html: str, subject: str) -> str:
    """Create a draft email and return its ID."""
    resp = requests.post(
        f"{config.BUTTONDOWN_API_BASE}/emails",
        headers=_headers(),
        json={"subject": subject, "body": html, "status": "draft"},
        timeout=30,
    )
    resp.raise_for_status()
    email_id = resp.json()["id"]
    print(f"[publisher] Draft created: id={email_id}")
    return email_id


def _trigger_send(email_id: str) -> None:
    """Move email to about_to_send, entering Buttondown's send queue."""
    resp = requests.patch(
        f"{config.BUTTONDOWN_API_BASE}/emails/{email_id}",
        headers=_headers(),
        json={"status": "about_to_send"},
        timeout=30,
    )
    resp.raise_for_status()
    print(f"[publisher] Email queued for sending: id={email_id}")


def publish(data: dict, date_str: str, subject: str) -> None:
    html = render_html(data, date_str)

    if config.DRY_RUN:
        print("[publisher] DRY_RUN=true — skipping Buttondown API call")
        print("[publisher] HTML preview (first 500 chars):")
        print(html[:500])
        return

    email_id = _create_draft(html, subject)

    if config.SEND_MODE == "send":
        _trigger_send(email_id)
        print(f"[publisher] Newsletter sent: '{subject}'")
    else:
        print(f"[publisher] Draft saved (SEND_MODE=draft). Subject: '{subject}'")
