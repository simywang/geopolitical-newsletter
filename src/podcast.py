import sys
import io
import re
import json
import requests
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

REPO_ROOT = Path(__file__).parent.parent
RSS_PATH = REPO_ROOT / "podcast.xml"

VOICE_A = "nova"   # Sarah — reports headlines and facts
VOICE_B = "onyx"   # James — provides analysis

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"

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
# Step 2: Text-to-speech → MP3
# ---------------------------------------------------------------------------

def generate_audio(dialogue: list[dict]) -> tuple[bytes, int]:
    """Call OpenAI TTS for each dialogue line, concatenate into a single MP3.

    Returns (mp3_bytes, duration_seconds).
    """
    import openai
    from pydub import AudioSegment

    client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
    model = config.PODCAST_TTS_MODEL
    supports_instructions = model == "gpt-4o-mini-tts"

    segments: list[AudioSegment] = []
    silence_short = AudioSegment.silent(duration=300)
    silence_long = AudioSegment.silent(duration=600)

    for i, line in enumerate(dialogue):
        speaker = line.get("speaker", "A")
        text = line.get("text", "").strip()
        if not text:
            continue

        voice = VOICE_A if speaker == "A" else VOICE_B
        kwargs: dict = {"model": model, "voice": voice, "input": text}
        if supports_instructions:
            kwargs["instructions"] = (
                "Speak as a professional, calm news anchor."
                if speaker == "A"
                else "Speak as a thoughtful, warm analyst adding context."
            )

        response = client.audio.speech.create(**kwargs)
        seg = AudioSegment.from_mp3(io.BytesIO(response.content))
        segments.append(seg)

        # Longer pause at end of each story (every even B line)
        segments.append(silence_long if speaker == "B" else silence_short)

        if (i + 1) % 10 == 0:
            print(f"[podcast] TTS: {i+1}/{len(dialogue)} lines done")

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
