import sys
import json

sys.path.insert(0, __file__.rsplit("/src/", 1)[0])
import config

LANGUAGES = {
    "nl": "Dutch",
    "zh": "Chinese (Simplified)",
}

_SYSTEM = """You are a professional financial translator specializing in commodity markets, trading, and supply chain content.
Translate the given JSON accurately and naturally into {language}.
- Preserve all JSON field names exactly (do not translate keys)
- Preserve all URLs exactly as-is
- Translate all string values: overview, title, summary, market_impact, second_order_effect, watch_next, item, detail
- Keep commodity names, futures contract names, and proper nouns natural in {language}
- Return ONLY valid JSON, no markdown fences, no extra text"""

_USER = """Translate all string values in this JSON into {language}. Return the same JSON structure with translated values.

{data_json}"""


def translate_data(data: dict, lang_code: str) -> dict:
    """Translate a summarizer data dict into the target language using DeepSeek."""
    language = LANGUAGES.get(lang_code)
    if not language:
        raise ValueError(f"Unsupported language code: {lang_code}")

    import openai
    client = openai.OpenAI(
        base_url="https://api.deepseek.com",
        api_key=config.DEEPSEEK_API_KEY,
    )

    translatable = {
        "overview": data.get("overview", ""),
        "articles": [
            {
                "title": a.get("title", ""),
                "summary": a.get("summary", ""),
                "market_impact": a.get("market_impact", ""),
                "second_order_effect": a.get("second_order_effect", ""),
                "watch_next": a.get("watch_next", ""),
                "source": a.get("source", ""),
                "url": a.get("url", ""),
            }
            for a in data.get("articles", [])
        ],
        "watch_this_week": data.get("watch_this_week", []),
    }

    response = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM.format(language=language)},
            {"role": "user", "content": _USER.format(
                language=language,
                data_json=json.dumps(translatable, ensure_ascii=False, indent=2),
            )},
        ],
        max_tokens=8192,
        temperature=0.1,
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
    translated = json.loads(raw)

    result = {**data, **translated}
    if "episode_title" in data:
        result["episode_title"] = data["episode_title"]
    return result
