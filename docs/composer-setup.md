# Composer setup (optional / advanced)

By default this project uses **Google Gemini** for extraction, market research, and scoring (`GEMINI_API_KEY` in `.env`). Use this guide only if you want **`ANALYSIS_BACKEND=composer`**, which routes those steps through **Composer** via a **local OpenAI-compatible HTTP API** on your machine (default `http://127.0.0.1:8787/v1`).

Cursor does **not** publish a simple “paste this URL into Python” Composer endpoint inside the IDE. You need two pieces:

## 1. Cursor API key (from Cursor)

1. Open **[Cursor Dashboard → API keys](https://cursor.com/dashboard/api)** (same account as the IDE).
2. Under **API & SSH keys** / **User API keys**, click **Create** (or **New API key**).
3. Copy the **full** secret from the creation dialog (starts with `crsr_…`); the table only shows a masked value.
4. Keep it secret — do **not** commit it to git.

That key authenticates **you** to Cursor’s backend. This repo never embeds it in code; you enter it in the local proxy app (below) or in `.env` only if your proxy expects it as the Bearer token.

## 2. Local OpenAI-compatible server (bridge)

The property screener expects something listening on your Mac that implements:

- `GET /v1/models`
- `POST /v1/chat/completions`

with model id **`composer-2.5-fast`** or **`composer-2.5`**.

### Recommended on macOS: “API for Cursor” (local app)

Third-party tooling (not maintained by this repo) that matches what `scripts/composer_llm.py` expects:

- Project: [standardagents/composer-api](https://github.com/standardagents/composer-api) on GitHub  
- Setup notes: [cursor-api.standardagents.ai/setup](https://cursor-api.standardagents.ai/setup.md)

Typical flow:

1. Download/install the **macOS app** from that project’s releases.
2. Paste your **Cursor API key** in the app UI.
3. **Start** the local server (default base URL `http://127.0.0.1:8787/v1`).
4. In this project’s **`.env`**:

```bash
ANALYSIS_BACKEND=composer
COMPOSER_API_BASE_URL=http://127.0.0.1:8787/v1
COMPOSER_API_KEY=local
COMPOSER_MODEL=composer-2.5-fast
```

(`COMPOSER_API_KEY=local` is fine when the app holds the real Cursor key; some setups use `crsr_…` as the Bearer token instead.)

5. Verify:

```bash
python3 scripts/check_composer.py
```

6. Ingest queued listings:

```bash
python3 scripts/ingest_pending_listings.py
```

### Official Cursor automation (different shape)

For **agents in TypeScript** or the terminal, Cursor documents the **[Cursor Agent SDK](https://cursor.com/docs/sdk/typescript)** and **`cursor-agent` CLI**. Those run the **full Cursor agent harness**, not the minimal JSON HTTP API this Python app uses. Wiring that in would be a separate integration.

## Intel Mac (x86_64)

The signed **API for Cursor** DMG is **Apple Silicon only**. It does not run on Intel Macs.

Ways to still use **Composer** with this property screener:

1. **Run the bridge on an Apple Silicon Mac** (your other machine, work Mac, etc.)
   - Install API for Cursor there, start the server on port **8787**.
   - On the Intel Mac, set in `.env`:
     `COMPOSER_API_BASE_URL=http://<silicon-mac-LAN-ip>:8787/v1`
   - Allow incoming connections on the Silicon Mac (firewall) and only do this on a trusted network.

2. **Use Gemini with billing** on the Intel Mac (`ANALYSIS_BACKEND=gemini`) — supported without any bridge.

3. **Build from source** ([composer-api](https://github.com/standardagents/composer-api)) with Node.js — advanced; local `npm run dev` targets Cloudflare Workers/containers and is not the same as the one-click macOS app. Expect extra setup (Wrangler, D1, optional Docker).

This repo expects **`POST /v1/chat/completions`** on the base URL. There is no first-party Intel installer from Cursor for that endpoint.

## Troubleshooting

| Symptom | What to do |
|--------|------------|
| `Connection refused` on `127.0.0.1:8787` | Local bridge app not running, or wrong port in `COMPOSER_API_BASE_URL`. |
| `check_composer.py` OK but ingest fails | Model name mismatch — try `COMPOSER_MODEL=composer-2.5`. |
| `pip: command not found` | Use `python3 -m pip install -r requirements.txt`. |
