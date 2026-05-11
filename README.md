# Commodity Frontier News

Daily AI-curated market intelligence across grains, oilseeds, coffee, cocoa, energy, weather, and supply chains. Delivered as a newsletter (Buttondown) and podcast (Spotify).

---

## Product Overview

- **Newsletter**: 5 deep-analysis stories with market impact, second-order effects, and trade signals
- **Podcast**: AI-generated dual-voice dialogue (Sarah & James) with commodity market narrative
- **Website**: [geopolitical-newsletter-three.vercel.app](https://geopolitical-newsletter-three.vercel.app)
- **Spotify**: [Commodity Frontier](https://open.spotify.com/show/033dFGpcN8nVTjTjR3uOuE)
- **Schedule**: Daily via cron-job.org → GitHub Actions

---

## Architecture

```
cron-job.org (daily trigger)
  → GitHub Actions
    → RSS fetch (18 commodity sources)
    → Real-time price fetch (yfinance: Brent, WTI, Cocoa, Coffee, Wheat…)
    → DeepSeek: summarize → 5 deep articles + What to Watch This Week
    → Buttondown: create draft / send newsletter
    → DeepSeek: generate podcast dialogue script
    → Volcengine / OpenAI TTS: render dual-voice audio
    → GitHub Releases: host mp3
    → podcast.xml: update RSS feed → Spotify
  → Vercel: website + /api/subscribe + /api/prices
```

---

## Quick Start (local)

```bash
pip install -r requirements.txt

export DEEPSEEK_API_KEY=sk-...
export BUTTONDOWN_API_KEY=...
export AI_MODEL=deepseek
export DRY_RUN=true
export SEND_MODE=draft

python src/main.py
```

---

## Environment Variables

### Required
| Variable | Description |
|----------|-------------|
| `BUTTONDOWN_API_KEY` | Buttondown API key |
| `DEEPSEEK_API_KEY` | DeepSeek API key (summary + dialogue + episode title) |

### AI Provider
| Variable | Default | Description |
|----------|---------|-------------|
| `AI_MODEL` | `claude` | `claude` / `deepseek` / `glm` |
| `ANTHROPIC_API_KEY` | — | Required if AI_MODEL=claude |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Anthropic model |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | DeepSeek model |
| `GLM_API_KEY` | — | Required if AI_MODEL=glm |
| `GLM_MODEL` | `glm-4.7-flash` | Zhipu model |

### Newsletter
| Variable | Default | Description |
|----------|---------|-------------|
| `SEND_MODE` | `draft` | `draft` = save draft; `send` = send to subscribers |
| `DRY_RUN` | `false` | `true` = skip Buttondown entirely |
| `PUBLISH_LANGUAGES` | `en` | Comma-separated: `en,nl,zh` |

### Podcast
| Variable | Default | Description |
|----------|---------|-------------|
| `PODCAST_ENABLED` | `false` | `true` = generate podcast |
| `PODCAST_DRY_RUN` | `true` | `true` = skip GitHub Release upload |
| `VOLC_API_KEY` | — | Volcengine TTS (primary) |
| `VOLC_VOICE_A` | `en_female_dacey_uranus_bigtts` | Host A (Sarah) |
| `VOLC_VOICE_B` | `en_male_tim_uranus_bigtts` | Host B (James) |
| `OPENAI_API_KEY` | — | OpenAI TTS fallback |
| `GITHUB_TOKEN` | — | Upload mp3 to GitHub Releases |
| `GITHUB_REPO` | `simywang/geopolitical-newsletter` | Target repo |

---

## DRY_RUN vs SEND_MODE

| | Fetches news | Calls AI | Creates draft | Sends to subscribers |
|-|:-:|:-:|:-:|:-:|
| `DRY_RUN=true` | ✅ | ✅ | ❌ | ❌ |
| `DRY_RUN=false, SEND_MODE=draft` | ✅ | ✅ | ✅ | ❌ |
| `DRY_RUN=false, SEND_MODE=send` | ✅ | ✅ | ✅ | ✅ |

---

## GitHub Actions Setup

1. Add **Secrets** (Settings → Secrets and variables → Actions → Secrets):
   - `DEEPSEEK_API_KEY`
   - `BUTTONDOWN_API_KEY`
   - `VOLC_API_KEY` *(optional)*
   - `OPENAI_API_KEY` *(optional, TTS fallback)*

2. Add **Variables** (same page → Variables tab):
   - `AI_MODEL` = `deepseek`
   - `SEND_MODE` = `send`
   - `PODCAST_ENABLED` = `true`
   - `PUBLISH_LANGUAGES` = `en`

3. Manual trigger: Actions → **Daily Geopolitical Briefing** → Run workflow

| Input | Description |
|-------|-------------|
| `dry_run` | `true` to skip Buttondown |
| `send_mode` | `draft` or `send` |
| `podcast_enabled` | `true` to generate podcast |
| `podcast_dry_run` | `true` to skip mp3 upload |

---

## Schedule

Triggered daily by **cron-job.org** at UTC 06:00 (Amsterdam 08:00 CEST).

---

## Project Structure

```
├── config.py                    # All config & env vars
├── src/
│   ├── fetcher.py               # RSS fetch (18 sources), filter, dedup
│   ├── summarizer.py            # AI summarization (5 deep articles)
│   ├── market_data.py           # Real-time commodity prices (yfinance)
│   ├── publisher.py             # HTML render + Buttondown API
│   ├── translator.py            # DeepSeek translation (nl, zh)
│   ├── podcast.py               # Dialogue script + TTS + RSS update
│   └── main.py                  # Pipeline entry point
├── api/
│   ├── subscribe.js             # Vercel: newsletter signup
│   └── prices.js                # Vercel: live commodity price ticker
├── podcast.xml                  # Spotify RSS feed
├── index.html                   # Landing page (Vercel)
├── .github/workflows/daily.yml  # GitHub Actions
└── requirements.txt
```

---

## Newsletter Content Structure

Each issue:
- **Market Intelligence Brief** — overview paragraph
- **5 Deep Articles**, each with:
  - Summary (220–300 words)
  - Market Impact (region → commodity → futures direction)
  - Second-Order Effect (downstream effects 4–12 weeks out)
  - Watch Next (one specific indicator to monitor)
- **What to Watch This Week** — 3–5 upcoming market events

---

## RSS Sources (18 feeds)

Reuters, BBC, OilPrice.com, EIA, Agrimoney, ICCO, Daily Coffee News, Perfect Daily Grind, NOAA Drought Monitor, WMO, and targeted Google News searches for cocoa, oil, wheat, LNG, coffee, soybeans, and EUDR.
