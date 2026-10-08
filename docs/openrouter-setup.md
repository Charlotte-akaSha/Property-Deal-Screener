# OpenRouter setup

Use **OpenRouter** when you want cloud models on any Mac (including Intel) without Google Gemini quotas or a local Cursor bridge.

1. Create an API key at [openrouter.ai/keys](https://openrouter.ai/keys) and add credits.
2. Pick a **vision** model on [openrouter.ai/models](https://openrouter.ai/models) (filter: image input).
3. In **`.env`**:

```bash
ANALYSIS_BACKEND=openrouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=google/gemini-2.5-flash
COMPOSER_FALLBACK_TO_GEMINI=false
```

Optional:

```bash
OPENROUTER_FAST_MODEL=google/gemini-2.5-flash
OPENROUTER_MAX_TOKENS=8192
OPENROUTER_HTTP_REFERER=http://localhost
OPENROUTER_APP_TITLE=Property Screener
```

If you see **HTTP 402** (“can only afford N tokens”), add credits at [openrouter.ai/settings/credits](https://openrouter.ai/settings/credits) or lower `OPENROUTER_MAX_TOKENS` (default **8192**).

4. Verify:

```bash
python3 scripts/check_composer.py
```

5. Run Streamlit or `python3 scripts/ingest_pending_listings.py`.

`GEMINI_API_KEY` is not used for analysis when `ANALYSIS_BACKEND=openrouter`. Google Maps and Sheets env vars are still required for transit and Sheet upsert.
