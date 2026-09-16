# ShyDevs Discord Bot (presence + incoming DMs)

Keeps the ShyDevs bot showing **online** on Discord, and forwards any DM
someone sends the bot back to the Django backend so it shows up in the
app's Bot tab. Everything else — the actual outgoing notifications
(webhook messages, DMs, reminders) — is sent directly by the backend over
the REST API and works whether or not this service is running. Presence
needs this service purely because Discord only shows a bot as online
while it holds a Gateway (WebSocket) connection open, which the backend's
request/response cycle has no place to do.

Requires the **Message Content Intent** enabled in the Discord Developer
Portal (Bot page → Privileged Gateway Intents) — without it the bot can't
read what people DM it and fails to connect at all.

## Local test

Gunicorn doesn't run on Windows, so test with Python's built-in WSGI server
instead — production still uses Gunicorn (see the Render setup below).

```bash
cd discord-bot
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
set DISCORD_BOT_TOKEN=your-bot-token-here
set BACKEND_URL=http://localhost:8000
set DISCORD_INCOMING_SECRET=same-value-as-the-backend-env-var
python -c "from wsgiref.simple_server import make_server; import app; make_server('', 5001, app.app).serve_forever()"
```

Watch for `Conectado ao Gateway como ShyDevs Bot (...)` in the console,
check the bot shows online in your Discord server, and confirm
`http://localhost:5001/health` returns `{"status": "ok", "bot_ready": true}`.

## Deploying on Render (separate service from the main backend)

This repo already hosts the Django backend as its own Render Web Service
with **Root Directory** set to `backend`. Create a **second, independent**
Web Service pointed at this same GitHub repo, so a push here doesn't touch
the backend's deploy and vice versa:

1. Render dashboard → **New → Web Service** → pick this repo again
2. **Root Directory**: `discord-bot`
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `gunicorn app:app --workers 1 --bind 0.0.0.0:$PORT`
   - `--workers 1` matters: each Gunicorn worker is a separate process, and
     each one would open its own Gateway connection for the same bot if
     there were more than one. One worker is enough — the health check is
     nearly free to serve, and the Gateway thread inside it doesn't need
     more.
   - `--bind 0.0.0.0:$PORT` matters too: Render tells the app which port
     to listen on via the `$PORT` env var it injects, and won't consider
     the service live without an explicit bind to it — Gunicorn's default
     port doesn't match, so Render's port scan just times out forever even
     though Gunicorn's own logs claim to be listening.
   - No `--threads`: the sync worker (Gunicorn's default) keeps this to
     exactly two threads in the whole process — its own accept loop and
     the bot's Gateway connection — which turned out to matter. The
     `gthread` worker's own thread pool sharing the process with the bot's
     asyncio loop reliably made Render's port scan never find an open port
     at all, even though Gunicorn's own log claimed to be listening.
5. **Environment → Add Environment Variable** (three of them):
   - `DISCORD_BOT_TOKEN` = the same bot token already set on the backend
   - `BACKEND_URL` = the backend service's URL, e.g.
     `https://shydevs-backend.onrender.com` (no trailing slash)
   - `DISCORD_INCOMING_SECRET` = the same value as the backend's own
     `DISCORD_INCOMING_SECRET` env var — this authenticates this service's
     calls to the backend's `/api/discord/incoming/` endpoint, so it isn't
     wide open to anyone who finds the URL
6. Free plan is fine — deploy

Render's free web services spin down after ~15 minutes with no HTTP
traffic, which would also kill the Gateway connection running inside. Add
this new service's URL (the one Render gives you, e.g.
`https://shydevs-bot.onrender.com/health`) to UptimeRobot (or any free
pinger) on a schedule shorter than 15 minutes — the same way the backend
itself is presumably already kept awake — and the process never sleeps,
so the bot stays connected and shows online continuously.
