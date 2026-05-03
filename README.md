# Geopolitical Briefing — Daily Newsletter

Automated daily geopolitical newsletter. Fetches news from 13 RSS sources → AI summarizes → sends via Buttondown.

---

## Quick Start (local)

```bash
pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...
export BUTTONDOWN_API_KEY=...
export AI_MODEL=claude
export DRY_RUN=true        # safe: won't call Buttondown
export SEND_MODE=draft

python src/main.py
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | If using Claude | — | Anthropic API key |
| `DEEPSEEK_API_KEY` | If using DeepSeek | — | DeepSeek API key |
| `GLM_API_KEY` | If using GLM | — | Zhipu AI API key |
| `BUTTONDOWN_API_KEY` | Yes | — | Buttondown API key |
| `AI_MODEL` | No | `claude` | Provider: `claude` / `deepseek` / `glm` |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-20250514` | Anthropic model ID |
| `DEEPSEEK_MODEL` | No | `deepseek-v4-flash` | DeepSeek model ID |
| `GLM_MODEL` | No | `glm-4.7-flash` | Zhipu model ID |
| `SEND_MODE` | No | `draft` | `draft` = save draft only; `send` = queue for delivery |
| `DRY_RUN` | No | `false` | `true` = skip Buttondown entirely, print HTML preview |

---

## Switching AI Provider

```bash
# Use DeepSeek
export AI_MODEL=deepseek
export DEEPSEEK_API_KEY=sk-...

# Use Zhipu GLM
export AI_MODEL=glm
export GLM_API_KEY=...
```

---

## DRY_RUN vs SEND_MODE

| | Fetches news | Calls AI | Creates Buttondown draft | Sends to subscribers |
|-|:-:|:-:|:-:|:-:|
| `DRY_RUN=true` | ✅ | ✅ | ❌ | ❌ |
| `DRY_RUN=false, SEND_MODE=draft` | ✅ | ✅ | ✅ | ❌ |
| `DRY_RUN=false, SEND_MODE=send` | ✅ | ✅ | ✅ | ✅ |

**Recommended workflow:**
1. First run: `DRY_RUN=true` — confirm the pipeline works
2. Second run: `SEND_MODE=draft` — inspect the draft in Buttondown
3. Production: `SEND_MODE=send` in GitHub Actions

---

## GitHub Actions Setup

1. Create a GitHub repository and push this code.

2. Add **Secrets** (Settings → Secrets and variables → Actions → Secrets):
   - `ANTHROPIC_API_KEY`
   - `DEEPSEEK_API_KEY` *(optional)*
   - `GLM_API_KEY` *(optional)*
   - `BUTTONDOWN_API_KEY`

3. Add **Variables** (same page → Variables tab):
   - `AI_MODEL` = `claude`
   - `SEND_MODE` = `send`
   - `ANTHROPIC_MODEL` = `claude-sonnet-4-20250514` *(optional)*

4. The workflow runs automatically **Monday–Friday at UTC 06:00**.
   You can also trigger it manually via Actions → "Daily Geopolitical Briefing" → Run workflow.

---

## Timezone Note

The cron is set to `0 6 * * 1-5` (UTC 06:00).

| Season | Amsterdam time | UTC cron |
|--------|---------------|----------|
| Summer (CEST, UTC+2) | 08:00 | `0 6 * * 1-5` |
| Winter (CET, UTC+1) | 08:00 | `0 7 * * 1-5` |

Update `.github/workflows/daily.yml` when clocks change.

---

## Project Structure

```
├── config.py                    # All config & env vars
├── src/
│   ├── fetcher.py               # RSS fetch, filter, dedup
│   ├── summarizer.py            # AI selection & summarization
│   ├── publisher.py             # HTML render + Buttondown API
│   └── main.py                  # Pipeline entry point
├── .github/workflows/daily.yml  # GitHub Actions cron
└── requirements.txt
```
