"""Standalone service whose only job is to keep the ShyDevs bot showing
online on Discord.

It does nothing else — the actual notifications (webhook messages, DMs,
reminders) are sent by the Django backend directly over the REST API and
don't need this service running at all. This exists purely for presence:
Discord only shows a bot as online while it holds a Gateway (WebSocket)
connection open, and the backend's request/response cycle has no place to
keep one alive.

Deployed as its own Render Web Service (free tier requires something
listening on an HTTP port, hence the tiny Flask health check) kept awake
by an external pinger like UptimeRobot hitting /health every few minutes.
"""
import os
import threading

import discord
from flask import Flask, jsonify

TOKEN = os.environ.get('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f'Conectado ao Gateway como {client.user} (id {client.user.id}).')


def run_bot():
    if not TOKEN:
        print('DISCORD_BOT_TOKEN nao configurado — o bot nao vai conectar.')
        return
    # Reconnects automatically on drops; blocks this thread forever.
    client.run(TOKEN)


threading.Thread(target=run_bot, daemon=True).start()

app = Flask(__name__)


@app.get('/')
@app.get('/health')
def health():
    return jsonify({'status': 'ok', 'bot_ready': client.is_ready()})
