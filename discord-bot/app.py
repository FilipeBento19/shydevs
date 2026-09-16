"""Standalone service whose only job is to keep the ShyDevs bot showing
online on Discord.

It does nothing else — the actual notifications (webhook messages, DMs,
reminders) are sent by the Django backend directly over the REST API and
don't need this service running at all. This exists purely for presence:
Discord only shows a bot as online while it holds a Gateway (WebSocket)
connection open, and the backend's request/response cycle has no place to
keep one alive.

Deployed as its own Render Web Service (free tier requires something
listening on an HTTP port, hence the tiny health check below) kept awake
by an external pinger like UptimeRobot hitting /health every few minutes.

The health check is a raw WSGI callable rather than Flask/Werkzeug — that
routing layer hit a `LookupError: unknown encoding: idna` under Gunicorn's
threaded worker on Render's Python 3.14 image (a codec-registration race
between the bot's own background imports and the first request), and a
one-route health check doesn't need routing machinery that can fail like
that anyway.
"""
import asyncio
import json
import os
import threading

import discord

TOKEN = os.environ.get('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
# CustomActivity shows the exact text with no "Playing/Watching" prefix —
# unlike Game/Streaming/Listening/Competing, which are fixed, translated
# prefixes the client controls.
activity = discord.CustomActivity(name='estou de olho em você')
client = discord.Client(intents=intents, activity=activity)


@client.event
async def on_ready():
    print(f'Conectado ao Gateway como {client.user} (id {client.user.id}).')


def run_bot():
    if not TOKEN:
        print('DISCORD_BOT_TOKEN nao configurado — o bot nao vai conectar.')
        return
    # client.run() is only safe on the main thread — it tries to register
    # SIGINT/SIGTERM handlers via loop.add_signal_handler, which raises
    # (or silently misbehaves, depending on platform) anywhere else. This
    # is client.run()'s own internals minus that signal-handling wrapper,
    # which is exactly what discord.py's own docs recommend for running a
    # client outside the main thread. Reconnects automatically on drops;
    # blocks this thread forever.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(client.start(TOKEN))
    finally:
        loop.close()


threading.Thread(target=run_bot, daemon=True).start()


def app(environ, start_response):
    body = json.dumps({'status': 'ok', 'bot_ready': client.is_ready()}).encode('utf-8')
    start_response('200 OK', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
    return [body]
