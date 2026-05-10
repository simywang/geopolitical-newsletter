import sys
import io
import re
import json
import base64
import uuid
import tempfile
import os
import requests
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

REPO_ROOT = Path(__file__).parent.parent
RSS_PATH = REPO_ROOT / "podcast.xml"

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"

_DIALOGUE_SYSTEM = """You are a podcast script writer for Commodity Frontier — a sharp, fast-paced daily intelligence show for commodity traders, procurement teams, and supply chain professionals.

Write a two-host dialogue that sounds like a real conversation between two people who genuinely follow markets — NOT a news read, NOT a lecture.

Hosts:
- Sarah (speaker A): quick, commercially minded, reacts like a trader. Asks "so what does that mean for the price?", "who gets hurt by this?", "wait — how fast does that flow through?". Gets genuinely surprised by supply chain connections she hadn't considered.
- James (speaker B): the analyst — loves revealing the second-order angle nobody's talking about. Connects weather to futures, geopolitics to freight rates, harvest delays to crush margins. Passionate, not dry. Drops context like a revelation.

CRITICAL rules for natural, engaging speech:
- Keep each turn SHORT: 1-3 sentences maximum. Rapid back-and-forth. No monologues.
- Sarah reacts like a trader: "Okay, so that's a buy signal on cocoa?", "Wait — how much of the crop is that?", "So processors are just... stuck?", "That's a squeeze then.", "Hold on —"
- James reveals angles: "Right, and here's what the market's not pricing yet —", "Exactly. And the second-order effect is —", "Think about it this way —", "This is the part that surprised me —"
- Make the price chain tangible: name the commodity, the region, the futures contract, the direction. "That's Brent, not WTI — European buyers feel this first." "Abidjan port data is the tell."
- Use contractions everywhere: it's, we're, didn't, you'd, that's, what's, who's, I'd
- Use trailing em dashes for natural pauses: "And look —", "The thing is —", "But here's what I keep thinking —"
- Use ellipsis for hesitation: "I mean... where does that leave the grinders?"
- Vary energy: some exchanges fast (2-word reactions), some slow (a beat of reflection on a big number)
- NO reading lists. Convert every bullet into a natural sentence in conversation.
- Open with the biggest market-moving story of the day as a punchy hook.
- Close with 1-2 "what to watch" items, then a warm "see you tomorrow."
- Total: ~600-750 words spoken aloud (~5 minutes)
- Do NOT mention URLs, source names, or publication names
- Return ONLY a valid JSON array, no markdown fences, no extra text:
[{"speaker": "A", "text": "..."}, {"speaker": "B", "text": "..."}, ...]

EXAMPLE of the right energy:
[
  {"speaker": "A", "text": "Okay — cocoa just broke twelve thousand dollars a tonne. Like, that number still doesn't feel real to me."},
  {"speaker": "B", "text": "It shouldn't. That's a record. And the mid-crop data out of Ivory Coast today just made it worse."},
  {"speaker": "A", "text": "How much worse?"},
  {"speaker": "B", "text": "Eighteen percent below the five-year average. So the market was already stretched — and now the next harvest is looking thin too."},
  {"speaker": "A", "text": "So chocolate companies are just... paying whatever it takes right now?"},
  {"speaker": "B", "text": "They have to. And here's the part that surprised me — the ones without forward cover are locking in at these record levels because waiting feels even riskier."},
  {"speaker": "A", "text": "That's a squeeze. What's the tell to watch here?"},
  {"speaker": "B", "text": "Abidjan port arrivals. Weekly data. If throughput drops, you know the physical market is confirming what futures are already saying."}
]"""

_DIALOGUE_USER = """Convert this briefing into a podcast dialogue. Date: {date}

Follow this narrative structure:

OPEN (2-3 exchanges)
- Sarah sets the scene using the "overview" — what kind of day is it for markets?
- James gives the one-line "biggest story" hook to pull listeners in.

FOR EACH STORY — follow this arc every time:
1. WHAT HAPPENED (2-3 exchanges)
   Sarah introduces the story in plain terms. James fills in the key facts.
   Use the "title" and "summary" fields. Keep it accessible — what actually happened?

2. MARKET IMPACT (3-4 exchanges)
   Now they go deeper — like two analysts at a trading desk.
   James uses "market_impact" to walk through the price chain: which region, which commodity, which futures contract, which direction.
   Sarah asks the sharp trader questions: "So who gets squeezed first?", "How fast does that move through?"

3. SECOND-ORDER EFFECT (2-3 exchanges)
   James uses "second_order_effect" to reveal the downstream angle most people aren't talking about yet.
   Sarah reacts with genuine surprise or concern: "Wait — so that hits [downstream industry] too?"

CLOSE (3-4 exchanges)
- Sarah asks: "So what are you watching this week?"
- James picks 2-3 items from "watch_this_week" and explains why each one matters.
- Warm sign-off: "See you tomorrow."

RULES:
- Each turn: 1-3 sentences max. No monologues.
- Maintain rapid back-and-forth throughout.
- Do NOT mention URLs, source names, or publication names.
- Return ONLY a valid JSON array, no markdown, no extra text:
[{{"speaker": "A", "text": "..."}}, {{"speaker": "B", "text": "..."}}]

BRIEFING:
{briefing_json}"""


# ---------------------------------------------------------------------------
# Step 1: Generate dialogue script via AI
# ---------------------------------------------------------------------------

def build_dialogue_script(data: dict, date_str: str) -> list[dict]:
    """Call the configured AI to turn newsletter data into a two-host dialogue."""
    briefing = {
        "overview": data.get("overview", ""),
        "stories": [
            {
                "title": a.get("title", ""),
                "summary": a.get("summary", ""),
                "market_impact": a.get("market_impact") or a.get("why_it_matters", ""),
                "second_order_effect": a.get("second_order_effect", ""),
            }
            for a in data.get("articles", [])
        ],
        "watch_this_week": data.get("watch_this_week", []),
    }
    user_msg = _DIALOGUE_USER.format(
        date=date_str,
        briefing_json=json.dumps(briefing, ensure_ascii=False, indent=2),
    )

    provider = config.AI_MODEL
    print(f"[podcast] Generating dialogue via {provider}...")

    if provider == "claude":
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=4096,
            system=_DIALOGUE_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = msg.content[0].text
    else:
        import openai as _openai
        if provider == "deepseek":
            client = _openai.OpenAI(
                base_url="https://api.deepseek.com", api_key=config.DEEPSEEK_API_KEY
            )
            model = config.DEEPSEEK_MODEL
        else:
            client = _openai.OpenAI(
                base_url="https://open.bigmodel.cn/api/paas/v4/",
                api_key=config.GLM_API_KEY,
            )
            model = config.GLM_MODEL
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _DIALOGUE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=4096,
            temperature=0.7,
        )
        raw = resp.choices[0].message.content

    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    dialogue = json.loads(raw.strip())
    print(f"[podcast] Dialogue: {len(dialogue)} lines")
    return dialogue


# ---------------------------------------------------------------------------
# Step 2: Text-to-speech → MP3
# ---------------------------------------------------------------------------

_VOLC_TTS_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
_volc_session = requests.Session()


_VOLC_CONTEXT_A = "Speak as Sarah, a sharp and emotionally reactive podcast host. React with genuine surprise, concern, or excitement. Use natural rising and falling intonation. Short punchy sentences. Sound like you're actually talking to your co-host, not reading. Vary your pace — speed up when excited, slow down on key words."
_VOLC_CONTEXT_B = "Speak as James, a passionate analyst who loves revealing hidden angles. Sound like you're letting someone in on something important. Build energy as the sentence progresses. Pause naturally before key insights. Warm but confident — never monotone or lecture-like."


def _volc_tts(text: str, voice: str, context: str = "") -> bytes:
    """Call Volcengine 豆包 TTS V3 (API Key only). Returns raw MP3 bytes."""
    headers = {
        "X-Api-Key": config.VOLC_API_KEY,
        "X-Api-Resource-Id": config.VOLC_TTS_RESOURCE_ID,
        "X-Api-Request-Id": str(uuid.uuid4()),
    }
    req_params: dict = {
        "text": text,
        "speaker": voice,
        "audio_params": {"format": "mp3", "sample_rate": 24000},
    }
    if context:
        req_params["additions"] = json.dumps({"context_texts": [context]})
    body = {
        "user": {"uid": "podcast_bot"},
        "req_params": req_params,
    }
    resp = _volc_session.post(_VOLC_TTS_URL, headers=headers, json=body, stream=True, timeout=60)
    resp.raise_for_status()

    chunks: list[bytes] = []
    for line in resp.iter_lines():
        if not line:
            continue
        data = json.loads(line)
        code = data.get("code", 0)
        if code == 20000000:
            break
        if code != 0:
            raise RuntimeError(f"Volcengine TTS error code={code}: {data.get('message')}")
        if data.get("data"):
            chunks.append(base64.b64decode(data["data"]))
    return b"".join(chunks)


def generate_audio(dialogue: list[dict]) -> tuple[bytes, int]:
    """Convert dialogue to a single MP3 using OpenAI TTS.

    Returns (mp3_bytes, duration_seconds).
    """
    from pydub import AudioSegment

    use_volc = bool(config.VOLC_API_KEY)
    if use_volc:
        voice_a = config.VOLC_VOICE_A
        voice_b = config.VOLC_VOICE_B
        print(f"[podcast] TTS provider: Volcengine ({config.VOLC_TTS_RESOURCE_ID})")
    else:
        import openai
        _openai_client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        voice_a = config.PODCAST_VOICE_A
        voice_b = config.PODCAST_VOICE_B
        print(f"[podcast] TTS provider: OpenAI ({config.PODCAST_TTS_MODEL})")

    segments: list[AudioSegment] = []
    silence_short = AudioSegment.silent(duration=300)
    silence_long = AudioSegment.silent(duration=600)

    total = len(dialogue)
    for i, line in enumerate(dialogue):
        speaker = line.get("speaker", "A")
        text = line.get("text", "").strip()
        if not text:
            continue

        voice = voice_a if speaker == "A" else voice_b
        if use_volc:
            context = _VOLC_CONTEXT_A if speaker == "A" else _VOLC_CONTEXT_B
            mp3_bytes_chunk = _volc_tts(text, voice, context)
        else:
            response = _openai_client.audio.speech.create(
                model=config.PODCAST_TTS_MODEL,
                voice=voice,
                input=text,
                response_format="mp3",
            )
            mp3_bytes_chunk = response.read()
        # Write to temp file so ffmpeg can seek (BytesIO pipe causes seek errors)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(mp3_bytes_chunk)
            tmp_path = tmp.name
        try:
            seg = AudioSegment.from_mp3(tmp_path)
        finally:
            os.unlink(tmp_path)
        segments.append(seg)
        segments.append(silence_long if speaker == "B" else silence_short)

        if (i + 1) % 10 == 0:
            print(f"[podcast] TTS: {i+1}/{total} lines done")

    full = sum(segments, AudioSegment.empty())
    duration_sec = int(len(full) / 1000)

    buf = io.BytesIO()
    full.export(buf, format="mp3", bitrate="128k")
    mp3_bytes = buf.getvalue()

    print(f"[podcast] Audio ready: {duration_sec}s, {len(mp3_bytes)//1024} KB")
    return mp3_bytes, duration_sec


# ---------------------------------------------------------------------------
# Step 3a: Generate episode cover image via StepFun
# ---------------------------------------------------------------------------

def generate_episode_image(data: dict) -> bytes | None:
    """Generate a 1400x1400 episode cover image using StepFun. Returns JPEG bytes or None."""
    if not config.STEPFUN_API_KEY:
        print("[podcast] STEPFUN_API_KEY not set — skipping episode image")
        return None

    stories = data.get("articles", [])[:3]
    topics = "; ".join(a.get("title", "")[:80] for a in stories if a.get("title"))
    image_prompt = (
        f"flat vector editorial illustration, bold graphic shapes, limited color palette of 3 colors, "
        f"clean lines, modern sophisticated style, no text, no faces, no logos. "
        f"Symbolic geopolitical imagery representing: {topics}"
    )[:500]
    print(f"[podcast] Image prompt: {image_prompt[:80]}...")

    import openai as _openai

    # Generate image via StepFun
    img_client = _openai.OpenAI(
        api_key=config.STEPFUN_API_KEY,
        base_url="https://api.stepfun.com/v1",
    )
    img_resp = img_client.images.generate(
        model="step-image-edit-2",
        prompt=image_prompt,
        response_format="b64_json",
        size="1024x1024",
        n=1,
        extra_body={"cfg_scale": 4.0, "steps": 20},
    )
    img_b64 = img_resp.data[0].b64_json
    raw_bytes = base64.b64decode(img_b64)

    # Upscale to 1400x1400 (Spotify minimum) and convert to JPEG
    from PIL import Image
    img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    img = img.resize((1400, 1400), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    print("[podcast] Episode image generated (1400x1400 JPEG)")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Step 3b: Upload assets to GitHub Releases (idempotent)
# ---------------------------------------------------------------------------

def _get_or_create_release(base: str, headers: dict, tag: str, date_str: str) -> tuple[int, str]:
    """Return (release_id, upload_url_base) for the given tag."""
    r = requests.get(f"{base}/releases/tags/{tag}", headers=headers, timeout=30)
    if r.status_code == 200:
        release = r.json()
        print(f"[podcast] Reusing existing release: {tag}")
    else:
        r = requests.post(
            f"{base}/releases",
            headers=headers,
            json={"tag_name": tag, "name": f"Briefing {date_str}", "draft": False, "prerelease": False},
            timeout=30,
        )
        r.raise_for_status()
        release = r.json()
        print(f"[podcast] Created release: {tag}")
    return release["id"], release["upload_url"].split("{")[0]


def _upload_asset(upload_url: str, headers: dict, release_id: int, base: str,
                  filename: str, content_type: str, data: bytes) -> str:
    """Upload a single asset, replacing any existing asset with the same name."""
    assets = requests.get(f"{base}/releases/{release_id}/assets", headers=headers, timeout=30).json()
    for asset in assets:
        if asset["name"] == filename:
            requests.delete(f"{base}/releases/assets/{asset['id']}", headers=headers, timeout=30)
            print(f"[podcast] Replaced existing asset: {filename}")

    r = requests.post(
        f"{upload_url}?name={filename}",
        headers={**headers, "Content-Type": content_type},
        data=data,
        timeout=120,
    )
    r.raise_for_status()
    url = r.json()["browser_download_url"]
    print(f"[podcast] Uploaded: {url}")
    return url


def upload_mp3(mp3_bytes: bytes, date_str: str, img_bytes: bytes | None = None) -> tuple[str, str | None]:
    """Upload MP3 (and optional cover image) to GitHub Releases. Returns (mp3_url, img_url)."""
    iso_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tag = f"briefing-{iso_date}"
    base = f"https://api.github.com/repos/{config.GITHUB_REPO}"
    headers = {
        "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    release_id, upload_url = _get_or_create_release(base, headers, tag, date_str)

    mp3_url = _upload_asset(upload_url, headers, release_id, base,
                            f"briefing-{iso_date}.mp3", "audio/mpeg", mp3_bytes)

    img_url = None
    if img_bytes:
        img_url = _upload_asset(upload_url, headers, release_id, base,
                                f"cover-{iso_date}.jpg", "image/jpeg", img_bytes)

    return mp3_url, img_url


# ---------------------------------------------------------------------------
# Step 3b: Generate episode title from top story
# ---------------------------------------------------------------------------

def generate_episode_title(data: dict, date_str: str) -> str:
    """Pick the single most market-moving headline and return a short episode title.
    Format: 'May 9 · <impactful headline under 55 chars>'
    Falls back to 'Commodity Frontier — <date_str>' on any error.
    """
    stories = data.get("articles", [])
    headlines = "\n".join(f"- {a.get('title', '')}" for a in stories[:8] if a.get("title"))
    try:
        short_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %-d")
    except ValueError:
        short_date = date_str  # already human-readable e.g. "May 9, 2026"
    fallback = f"Commodity Frontier — {date_str}"

    if not headlines:
        return fallback

    prompt = (
        f"Today's date: {date_str}\n"
        f"Headlines:\n{headlines}\n\n"
        "Pick the single most market-moving story for commodity traders (coffee, cocoa, oil, corn, "
        "agricultural commodities, supply chain, geopolitics). Write a podcast episode title: "
        f"'{short_date} · <headline>'. "
        "The part after '· ' must be under 55 characters. Be specific and punchy. "
        "Return ONLY the title, nothing else."
    )
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
        )
        resp = client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            max_tokens=60,
            messages=[{"role": "user", "content": prompt}],
        )
        title = resp.choices[0].message.content.strip().strip('"')
        if len(title) > 80:
            title = title[:77] + "..."
        print(f"[podcast] Episode title: {title}")
        return title
    except Exception as e:
        print(f"[podcast] Title generation failed: {e} — using fallback")
        return fallback


# Step 4: Update podcast.xml RSS feed
# ---------------------------------------------------------------------------

def update_rss_feed(
    mp3_url: str,
    mp3_size: int,
    duration_sec: int,
    overview: str,
    date_str: str,
    img_url: str | None = None,
    episode_title: str | None = None,
) -> None:
    """Prepend a new <item> to podcast.xml using the XML parser (not string ops)."""
    ET.register_namespace("", "")
    ET.register_namespace("itunes", ITUNES_NS)

    tree = ET.parse(RSS_PATH)
    root = tree.getroot()
    channel = root.find("channel")

    mins, secs = divmod(duration_sec, 60)
    duration_str = f"{mins:02d}:{secs:02d}"
    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    iso_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    guid = f"briefing-{iso_date}"
    title = episode_title or f"Commodity Frontier — {date_str}"

    item = ET.Element("item")
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "guid", isPermaLink="false").text = guid
    ET.SubElement(item, "pubDate").text = pub_date
    ET.SubElement(item, "description").text = overview
    ET.SubElement(item, f"{{{ITUNES_NS}}}summary").text = overview
    ET.SubElement(item, f"{{{ITUNES_NS}}}duration").text = duration_str
    ET.SubElement(item, f"{{{ITUNES_NS}}}episodeType").text = "full"
    if img_url:
        ET.SubElement(item, f"{{{ITUNES_NS}}}image", href=img_url)
    ET.SubElement(
        item,
        "enclosure",
        url=mp3_url,
        length=str(mp3_size),
        type="audio/mpeg",
    )

    # Remove existing item with the same guid (prevent duplicates on re-runs)
    for old_item in channel.findall("item"):
        old_guid = old_item.findtext("guid")
        if old_guid == guid:
            channel.remove(old_item)

    # Insert before first existing <item> (newest episode first)
    existing = channel.findall("item")
    if existing:
        idx = list(channel).index(existing[0])
        channel.insert(idx, item)
    else:
        channel.append(item)

    ET.indent(tree, space="  ")
    tree.write(str(RSS_PATH), encoding="unicode", xml_declaration=True)
    print(f"[podcast] RSS updated: {RSS_PATH.name}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_podcast(data: dict, date_str: str) -> None:
    """Orchestrate all podcast steps."""
    if not config.PODCAST_ENABLED:
        print("[podcast] PODCAST_ENABLED=false — skipping.")
        return

    print("[podcast] --- Podcast generation starting ---")

    dialogue = build_dialogue_script(data, date_str)
    mp3_bytes, duration_sec = generate_audio(dialogue)

    if config.PODCAST_DRY_RUN:
        out_path = REPO_ROOT / f"podcast-preview-{date_str}.mp3"
        out_path.write_bytes(mp3_bytes)
        print(
            f"[podcast] PODCAST_DRY_RUN=true — saved locally to {out_path.name}. "
            f"Audio: {len(mp3_bytes)//1024} KB, {duration_sec}s"
        )
        return

    img_bytes = generate_episode_image(data)
    mp3_url, img_url = upload_mp3(mp3_bytes, date_str, img_bytes)
    ep_title = generate_episode_title(data, date_str)
    update_rss_feed(mp3_url, len(mp3_bytes), duration_sec, data.get("overview", ""), date_str, img_url, ep_title)
    print(f"[podcast] --- Done: {mp3_url} ---")
