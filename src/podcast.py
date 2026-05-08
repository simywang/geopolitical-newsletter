import sys
import io
import re
import json
import base64
import uuid
import requests
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

REPO_ROOT = Path(__file__).parent.parent
RSS_PATH = REPO_ROOT / "podcast.xml"

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"

# Volcengine TTS endpoint
_VOLC_TTS_URL = "https://openspeech.bytedance.com/api/v1/tts"
# Max bytes per Volcengine TTS request
_VOLC_MAX_BYTES = 900  # conservative, limit is 1024

_DIALOGUE_SYSTEM = """You are a podcast script writer for a daily geopolitical briefing show.
Convert the provided news briefing JSON into a natural two-host dialogue.

Hosts:
- Sarah (speaker A): reports headlines and key facts clearly and concisely
- James (speaker B): adds context, analysis, and explains why each story matters

Rules:
- Conversational and engaging — not a news reading
- Total length: ~700-800 words when spoken aloud (~5 minutes)
- Do NOT mention URLs, source names, or publication names
- Return ONLY a valid JSON array, no markdown fences, no extra text:
[{"speaker": "A", "text": "..."}, {"speaker": "B", "text": "..."}, ...]"""

_DIALOGUE_USER = """Convert this briefing into a podcast dialogue. Date: {date}

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
                "title": a["title"],
                "summary": a["summary"],
                "why_it_matters": a["why_it_matters"],
            }
            for a in data.get("articles", [])
        ],
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
# Step 2: Text-to-speech → MP3  (Volcengine TTS)
# ---------------------------------------------------------------------------

def _split_text(text: str, max_bytes: int = _VOLC_MAX_BYTES) -> list[str]:
    """Split text into chunks that fit within Volcengine's byte limit.

    Splits on sentence boundaries (. ! ?) first, then on commas, then hard-cuts.
    """
    if len(text.encode("utf-8")) <= max_bytes:
        return [text]

    chunks: list[str] = []
    # Split on sentence-ending punctuation
    sentences = re.split(r"(?<=[.!?])\s+", text)
    current = ""
    for sentence in sentences:
        candidate = (current + " " + sentence).strip() if current else sentence
        if len(candidate.encode("utf-8")) <= max_bytes:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # If a single sentence is still too long, split on commas
            if len(sentence.encode("utf-8")) > max_bytes:
                parts = re.split(r",\s*", sentence)
                sub = ""
                for part in parts:
                    cand2 = (sub + ", " + part).strip(", ") if sub else part
                    if len(cand2.encode("utf-8")) <= max_bytes:
                        sub = cand2
                    else:
                        if sub:
                            chunks.append(sub)
                        sub = part
                if sub:
                    chunks.append(sub)
            else:
                current = sentence
    if current:
        chunks.append(current)
    return chunks


def _volc_tts_chunk(text: str, voice: str) -> bytes:
    """Call Volcengine TTS for a single text chunk. Returns raw MP3 bytes."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer;{config.VOLC_TTS_ACCESS_TOKEN}",
    }
    body = {
        "app": {
            "appid": config.VOLC_TTS_APP_ID,
            "token": config.VOLC_TTS_ACCESS_TOKEN,
            "cluster": config.VOLC_TTS_CLUSTER,
        },
        "user": {"uid": "podcast_bot"},
        "audio": {
            "voice_type": voice,
            "encoding": "mp3",
            "speed_ratio": 1.0,
            "rate": 24000,
            "loudness_ratio": 1.0,
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "operation": "query",
        },
    }
    resp = requests.post(_VOLC_TTS_URL, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != 3000:
        raise RuntimeError(
            f"Volcengine TTS error code={result.get('code')}: {result.get('message')}"
        )
    return base64.b64decode(result["data"])


def generate_audio(dialogue: list[dict]) -> tuple[bytes, int]:
    """Convert dialogue to a single MP3 using Volcengine TTS.

    Returns (mp3_bytes, duration_seconds).
    """
    from pydub import AudioSegment

    voice_a = config.VOLC_VOICE_A   # en_female_sarah
    voice_b = config.VOLC_VOICE_B   # en_male_adam

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

        # Split long text into chunks (Volcengine limit: 1024 bytes)
        chunks = _split_text(text)
        for chunk in chunks:
            mp3 = _volc_tts_chunk(chunk, voice)
            seg = AudioSegment.from_mp3(io.BytesIO(mp3))
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
# Step 3: Upload MP3 to GitHub Releases (idempotent)
# ---------------------------------------------------------------------------

def upload_mp3(mp3_bytes: bytes, date_str: str) -> str:
    """Upload MP3 to a dated GitHub Release. Returns public download URL."""
    tag = f"briefing-{date_str}"
    filename = f"briefing-{date_str}.mp3"
    base = f"https://api.github.com/repos/{config.GITHUB_REPO}"
    headers = {
        "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Resolve or create release
    r = requests.get(f"{base}/releases/tags/{tag}", headers=headers, timeout=30)
    if r.status_code == 200:
        release = r.json()
        print(f"[podcast] Reusing existing release: {tag}")
    else:
        r = requests.post(
            f"{base}/releases",
            headers=headers,
            json={
                "tag_name": tag,
                "name": f"Briefing {date_str}",
                "draft": False,
                "prerelease": False,
            },
            timeout=30,
        )
        r.raise_for_status()
        release = r.json()
        print(f"[podcast] Created release: {tag}")

    release_id = release["id"]
    upload_url = release["upload_url"].split("{")[0]

    # Delete existing asset with same name (idempotent re-run)
    assets = requests.get(
        f"{base}/releases/{release_id}/assets", headers=headers, timeout=30
    ).json()
    for asset in assets:
        if asset["name"] == filename:
            requests.delete(
                f"{base}/releases/assets/{asset['id']}", headers=headers, timeout=30
            )
            print(f"[podcast] Replaced existing asset: {filename}")

    # Upload
    upload_headers = {**headers, "Content-Type": "audio/mpeg"}
    r = requests.post(
        f"{upload_url}?name={filename}",
        headers=upload_headers,
        data=mp3_bytes,
        timeout=120,
    )
    r.raise_for_status()
    url = r.json()["browser_download_url"]
    print(f"[podcast] Uploaded: {url}")
    return url


# ---------------------------------------------------------------------------
# Step 4: Update podcast.xml RSS feed
# ---------------------------------------------------------------------------

def update_rss_feed(
    mp3_url: str,
    mp3_size: int,
    duration_sec: int,
    overview: str,
    date_str: str,
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
    guid = f"briefing-{date_str}"
    title = f"Geopolitical Briefing — {date_str}"

    item = ET.Element("item")
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "guid", isPermaLink="false").text = guid
    ET.SubElement(item, "pubDate").text = pub_date
    ET.SubElement(item, "description").text = overview
    ET.SubElement(item, f"{{{ITUNES_NS}}}summary").text = overview
    ET.SubElement(item, f"{{{ITUNES_NS}}}duration").text = duration_str
    ET.SubElement(item, f"{{{ITUNES_NS}}}episodeType").text = "full"
    ET.SubElement(
        item,
        "enclosure",
        url=mp3_url,
        length=str(mp3_size),
        type="audio/mpeg",
    )

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
        print(
            f"[podcast] PODCAST_DRY_RUN=true — skipping upload. "
            f"Audio: {len(mp3_bytes)//1024} KB, {duration_sec}s"
        )
        return

    mp3_url = upload_mp3(mp3_bytes, date_str)
    update_rss_feed(mp3_url, len(mp3_bytes), duration_sec, data.get("overview", ""), date_str)
    print(f"[podcast] --- Done: {mp3_url} ---")
