import sys
import json
import re

sys.path.insert(0, __file__.rsplit("/src/", 1)[0])
import config

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM = """You are a senior geopolitical analyst writing a daily briefing for an informed audience.
You will be given a list of news articles in JSON format.
Your task:
1. Select the {n} most significant articles based on geopolitical importance.
2. Write a "Today's Overview" (~200 words) summarizing the overall global situation.
3. For each selected article write:
   - "summary": ~150 words covering what happened and the key facts
   - "why_it_matters": 2-3 sentences on significance and what to watch

STRICT RULES:
- Only use articles from the provided list. Do NOT invent titles, sources, or URLs.
- Preserve the original "url" field exactly as given.
- Return ONLY valid JSON with no markdown fences, no extra text before or after.
- Output structure must match exactly:
{{
  "overview": "...",
  "articles": [
    {{
      "title": "...",
      "source": "...",
      "url": "...",
      "summary": "...",
      "why_it_matters": "..."
    }}
  ]
}}""".format(n=config.ARTICLES_TO_SELECT)

_USER_TMPL = """Here are today's articles (JSON array). Select the {n} most important and return the briefing JSON.

{articles_json}"""


def _build_prompt(articles: list[dict]) -> str:
    slim = [
        {
            "title": a["title"],
            "source": a["source"],
            "url": a["url"],
            "description": a["description"],
        }
        for a in articles
    ]
    return _USER_TMPL.format(
        n=config.ARTICLES_TO_SELECT,
        articles_json=json.dumps(slim, ensure_ascii=True, indent=2),
    )


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_response(raw: str) -> dict:
    cleaned = _strip_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print("[summarizer] JSON parse failed. Raw AI output:")
        print("---")
        print(raw)
        print("---")
        raise RuntimeError(f"Failed to parse AI response as JSON: {e}") from e


# ---------------------------------------------------------------------------
# Provider clients
# ---------------------------------------------------------------------------

def _call_claude(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=4096,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _call_openai_compat(prompt: str, base_url: str, api_key: str, model: str) -> str:
    import openai
    client = openai.OpenAI(base_url=base_url, api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
        max_tokens=4096,
        temperature=0.3,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def summarize(articles: list[dict]) -> dict:
    prompt = _build_prompt(articles)
    provider = config.AI_MODEL

    print(f"[summarizer] Calling {provider} ({_model_name(provider)}) with {len(articles)} articles...")

    if provider == "claude":
        raw = _call_claude(prompt)
    elif provider == "deepseek":
        raw = _call_openai_compat(
            prompt,
            base_url="https://api.deepseek.com",
            api_key=config.DEEPSEEK_API_KEY,
            model=config.DEEPSEEK_MODEL,
        )
    elif provider == "glm":
        raw = _call_openai_compat(
            prompt,
            base_url="https://open.bigmodel.cn/api/paas/v4/",
            api_key=config.GLM_API_KEY,
            model=config.GLM_MODEL,
        )
    else:
        raise ValueError(f"Unknown AI_MODEL: '{provider}'. Must be claude, deepseek, or glm.")

    result = _parse_response(raw)
    selected = len(result.get("articles", []))
    print(f"[summarizer] Done — {selected} articles selected")
    return result


def _model_name(provider: str) -> str:
    return {
        "claude": config.ANTHROPIC_MODEL,
        "deepseek": config.DEEPSEEK_MODEL,
        "glm": config.GLM_MODEL,
    }.get(provider, "unknown")
