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
import traceback
from datetime import datetime, timezone

import discord
import requests

TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
# Where to forward DMs people send the bot, so they show up in the app's
# Bot tab. Both must be set for forwarding to happen at all.
BACKEND_URL = (os.environ.get('BACKEND_URL') or '').rstrip('/')
INCOMING_SECRET = os.environ.get('DISCORD_INCOMING_SECRET')

intents = discord.Intents.default()
intents.message_content = True  # needed to read message.content, even for DMs
# CustomActivity shows the exact text with no "Playing/Watching" prefix —
# unlike Game/Streaming/Listening/Competing, which are fixed, translated
# prefixes the client controls.
activity = discord.CustomActivity(name='estou de olho em você')
client = discord.Client(intents=intents, activity=activity)
gateway_state = {'status': 'starting', 'error': None}
forward_state = {
    'status': 'waiting_for_dm',
    'http_status': None,
    'backend_detail': None,
    'last_attempt_at': None,
}
bot_thread = None
bot_thread_lock = threading.Lock()


@client.event
async def on_ready():
    gateway_state['status'] = 'ready'
    gateway_state['error'] = None
    print(f'Conectado ao Gateway como {client.user} (id {client.user.id}).')


@client.event
async def on_disconnect():
    gateway_state['status'] = 'disconnected'


@client.event
async def on_resumed():
    gateway_state['status'] = 'ready'
    gateway_state['error'] = None


def _forward_incoming(discord_id, content):
    forward_state['status'] = 'sending'
    forward_state['http_status'] = None
    forward_state['backend_detail'] = None
    forward_state['last_attempt_at'] = datetime.now(timezone.utc).isoformat()
    try:
        response = requests.post(
            f'{BACKEND_URL}/api/discord/incoming/',
            json={'secret': INCOMING_SECRET, 'discord_id': discord_id, 'content': content},
            timeout=10,
        )
        forward_state['http_status'] = response.status_code
        try:
            detail = response.json().get('detail')
        except (ValueError, AttributeError):
            detail = None
        forward_state['backend_detail'] = str(detail)[:240] if detail else None
        forward_state['status'] = 'delivered' if response.ok else 'rejected'
        print(
            f'DM encaminhada ao backend: HTTP {response.status_code}'
            + (f' · {detail}' if detail else ''),
            flush=True,
        )
    except requests.RequestException as exc:
        forward_state['status'] = 'network_error'
        forward_state['backend_detail'] = f'{type(exc).__name__}: {str(exc)[:200]}'
        print(f'Falha ao encaminhar DM: {forward_state["backend_detail"]}', flush=True)


@client.event
async def on_message(message):
    if message.author.bot or message.guild is not None:
        return  # only forward DMs from real people, not server messages
    if not BACKEND_URL or not INCOMING_SECRET:
        return
    # requests is blocking — offload so it doesn't stall the event loop.
    await asyncio.to_thread(_forward_incoming, str(message.author.id), message.content)


def run_bot():
    if not TOKEN:
        gateway_state['status'] = 'configuration_error'
        gateway_state['error'] = 'DISCORD_BOT_TOKEN não configurado.'
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
    except Exception as exc:
        gateway_state['status'] = 'failed'
        gateway_state['error'] = f'{type(exc).__name__}: {str(exc)[:240]}'
        traceback.print_exc()
    finally:
        loop.close()


def ensure_bot_thread():
    """Start the Gateway inside the Gunicorn worker, never in its master.

    Import-time threads can be created before Gunicorn finishes its worker
    lifecycle and wind up attached to the process Render is replacing. The
    first health request is guaranteed to execute in the serving worker.
    """
    global bot_thread
    with bot_thread_lock:
        if bot_thread and bot_thread.is_alive():
            return
        gateway_state['status'] = 'starting'
        gateway_state['error'] = None
        bot_thread = threading.Thread(target=run_bot, daemon=True, name='discord-gateway')
        bot_thread.start()


def app(environ, start_response):
    ensure_bot_thread()
    body = json.dumps({
        'status': 'ok',
        'bot_ready': client.is_ready(),
        'gateway_status': gateway_state['status'],
        'gateway_error': gateway_state['error'],
        'configuration': {
            'bot_token': bool(TOKEN),
            'backend_url': bool(BACKEND_URL),
            'incoming_secret': bool(INCOMING_SECRET),
            'incoming_endpoint': f'{BACKEND_URL}/api/discord/incoming/' if BACKEND_URL else None,
        },
        'incoming_forward': forward_state,
    }, ensure_ascii=False).encode('utf-8')
    start_response('200 OK', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
    return [body]
