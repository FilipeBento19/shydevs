"""Posts Activity events to a Discord channel via webhook, as rich embeds.

No-op if DISCORD_WEBHOOK_URL isn't set, and the actual HTTP call is fired
from a background thread so a slow/unreachable Discord never delays the API
response that triggered it.
"""
import os
import threading

import requests

COLORS = {
    'task_created': 0x3fcf8e,
    'task_assigned': 0x7c6fff,
    'task_status': 0xffc26b,
    'task_completed': 0x3fcf8e,
    'task_updated': 0x9a97b8,
    'checklist': 0xb3aaff,
    'comment': 0x6fb3ff,
    'overdue': 0xff4d5e,
}
EMOJI = {
    'task_created': '📋',
    'task_assigned': '🔁',
    'task_status': '🔄',
    'task_completed': '✅',
    'task_updated': '✏️',
    'checklist': '☑️',
    'comment': '💬',
    'overdue': '⏰',
}
NOTIFY_EVENT_TYPES = set(COLORS)


def _task_url(task):
    base = (os.environ.get('FRONTEND_URL') or '').rstrip('/')
    return f'{base}/tasks/{task.id}' if base and task else None


def _flatten(value):
    if isinstance(value, dict):
        return ' → '.join(str(v) for v in value.values())
    return str(value)


def build_embed(activity):
    event_type = activity.event_type
    task = activity.task
    embed = {
        'title': f'{EMOJI.get(event_type, "🔔")} {activity.message}'[:256],
        'color': COLORS.get(event_type, 0x9a97b8),
        'timestamp': activity.created_at.isoformat(),
        'footer': {'text': task.project.name if task and task.project_id else 'ShyDevs'},
    }

    fields = []
    if task:
        fields.append({'name': 'Tarefa', 'value': f'{task.code} · {task.title}'[:1024]})
    for key, value in list((activity.details or {}).items())[:6]:
        label = str(key)[:1].upper() + str(key)[1:]
        fields.append({'name': label[:256], 'value': _flatten(value)[:1024], 'inline': True})
    if fields:
        embed['fields'] = fields

    url = _task_url(task)
    if url:
        embed['url'] = url
    return embed


def _post(webhook_url, payload):
    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except requests.RequestException:
        pass  # best-effort — a Discord hiccup should never break the app


def notify(activity):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url or activity.event_type not in NOTIFY_EVENT_TYPES:
        return
    payload = {'username': 'ShyDevs', 'embeds': [build_embed(activity)]}
    threading.Thread(target=_post, args=(webhook_url, payload), daemon=True).start()
