# ShyDevs Discord Bot (presence-only)

Keeps the ShyDevs bot showing **online** on Discord. Nothing else — every
actual notification (webhook messages, DMs, reminders) is sent directly by
the Django backend over the REST API and works whether or not this service
is running. This exists purely so the bot doesn't sit there looking
offline in the member list, since that requires holding open a Gateway
(WebSocket) connection, which the backend's request/response cycle has no
place to do.

## Local test

Gunicorn doesn't run on Windows, so test with Python's built-in WSGI server
instead — production still uses Gunicorn (see the Render setup below).

```bash
cd discord-bot
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
set DISCORD_BOT_TOKEN=your-bot-token-here
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
4. **Start Command**: `gunicorn app:app --workers 1 --threads 4`
   - `--workers 1` matters: each Gunicorn worker is a separate process, and
     each one would open its own Gateway connection for the same bot if
     there were more than one. One worker is enough — the health check is
     nearly free to serve, and the Gateway thread inside it doesn't need
     more.
5. **Environment → Add Environment Variable**: `DISCORD_BOT_TOKEN` = the
   same bot token already set on the backend service
6. Free plan is fine — deploy

Render's free web services spin down after ~15 minutes with no HTTP
traffic, which would also kill the Gateway connection running inside. Add
this new service's URL (the one Render gives you, e.g.
`https://shydevs-bot.onrender.com/health`) to UptimeRobot (or any free
pinger) on a schedule shorter than 15 minutes — the same way the backend
itself is presumably already kept awake — and the process never sleeps,
so the bot stays connected and shows online continuously.
