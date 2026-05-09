import sys
import json
import re

sys.path.insert(0, __file__.rsplit("/src/", 1)[0])
import config

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM = """You are a senior commodity markets analyst writing a daily intelligence briefing for trading desks, procurement teams, and supply chain professionals.

You will be given a list of news articles in JSON format.

Your task:
1. Group duplicate or overlapping stories into one market theme. If multiple sources cover the same event, synthesize them into a single richer entry — do NOT select them separately.
2. Select the {n} most market-relevant themes after deduplication.
3. Write a "Market Intelligence Brief" overview (~200 words) focused on which commodities and supply chains are under pressure today and why.
4. For each selected theme write:
   - "summary": 220-300 words — what happened, which producing regions/shipping routes are affected, key facts
   - "market_impact": the price chain reasoning — affected region → commodity → supply/demand shift → which futures contract moves and in which direction
   - "second_order_effect": downstream consequences 4-12 weeks out (e.g. higher input costs for manufacturers, freight rate pressure, substitution effects)
   - "watch_next": one specific data point, report, or event to monitor as a leading indicator

5. Generate a "watch_this_week" list of 3-5 items: upcoming data releases, weather windows, or market events that traders should monitor in the next 5-7 days based on today's news context. Draw from: USDA WASDE, EIA inventory reports, OPEC meetings, Brazil/Argentina crop weather windows, West Africa cocoa arrivals, Vietnam robusta export flow, EUDR deadlines, Black Sea/Red Sea/Panama Canal logistics.

Commodity knowledge to apply:
- Brazil: ~40% of global soy exports, largest arabica coffee producer. Mato Grosso harvest window is Jan-Mar; delays tighten Jul CBOT soy spread. El Niño = Brazilian drought = arabica supply risk.
- West Africa (Ivory Coast + Ghana): ~80% of global cocoa. Flowering Oct-Dec; dry harmattan wind = lower mid-crop. La Niña = excess rain = pod disease risk.
- Black Sea (Ukraine + Russia): ~30% of global wheat exports. Any port disruption or conflict escalation tightens CBOT/MATIF wheat.
- Strait of Hormuz: ~20% of global oil + LNG. Military tension → Brent spike + LNG rerouting via Cape of Good Hope (+9-12 days, higher spot premiums).
- OPEC+ cuts vs. US shale: marginal price setter for Brent. Watch weekly EIA inventory draws.
- Oil → fertilizer (natural gas → ammonia → urea) → grain production cost with ~6 month lag.

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
      "market_impact": "...",
      "second_order_effect": "...",
      "watch_next": "..."
    }}
  ],
  "watch_this_week": [
    {{
      "item": "Short label (e.g. USDA WASDE, EIA inventory, Brazil harvest)",
      "detail": "One sentence: what to watch for and why it matters to prices"
    }}
  ]
}}""".format(n=config.ARTICLES_TO_SELECT)

_USER_TMPL = """Here are today's articles (JSON array). Select the {n} most important and return the briefing JSON.
{price_context}
{articles_json}"""


def _build_prompt(articles: list[dict], price_context: str = "") -> str:
    slim = [
        {
            "title": a["title"],
            "source": a["source"],
            "url": a["url"],
            "description": a["description"],
        }
        for a in articles
    ]
    ctx = f"\n{price_context}\n" if price_context else ""
    return _USER_TMPL.format(
        n=config.ARTICLES_TO_SELECT,
        price_context=ctx,
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
        max_tokens=8192,
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
        max_tokens=8192,
        temperature=0.3,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def summarize(articles: list[dict], price_context: str = "") -> dict:
    prompt = _build_prompt(articles, price_context)
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
