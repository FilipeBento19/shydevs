"""Posts Activity events to a Discord channel via webhook, using Components V2
(Discord's newer message-layout API — colored containers, formatted text
blocks, separators — instead of the classic embed object).

No-op if DISCORD_WEBHOOK_URL isn't set, and the actual HTTP call is fired
from a background thread so a slow/unreachable Discord never delays the API
response that triggered it.
"""
import os
import threading

import requests

# Components V2 component type IDs (Discord message components API).
CONTAINER = 17
TEXT_DISPLAY = 10
SEPARATOR = 14

# A message built from components (instead of content/embeds) must carry
# this flag, and in exchange cannot also set `content` or `embeds`.
IS_COMPONENTS_V2 = 1 << 15

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
NOTIFY_EVENT_TYPES = set(COLORS)
# Events worth @mentioning the assignee for — the ones where it's genuinely
# their move next. Status updates/comments/checklist stay silent pings.
MENTION_EVENT_TYPES = {'task_created', 'task_assigned', 'overdue'}


def _task_url(task):
    base = (os.environ.get('FRONTEND_URL') or '').rstrip('/')
    return f'{base}/tasks/{task.id}' if base and task else None


def _flatten(value):
    if isinstance(value, dict):
        return ' → '.join(str(v) for v in value.values())
    return str(value)


def _text(content):
    return {'type': TEXT_DISPLAY, 'content': content}


def build_container(activity, mention_line=None):
    """A Components V2 Container: a card holding text blocks — the
    Components V2 equivalent of an embed's title + fields."""
    task = activity.task

    title = f'**{activity.message}**'[:4000]
    url = _task_url(task)
    if url and task:
        title = f'**[{activity.message}]({url})**'[:4000]

    lines = []
    if task:
        lines.append(f'**Tarefa:** {task.code} · {task.title}')
    for key, value in list((activity.details or {}).items())[:6]:
        label = str(key)[:1].upper() + str(key)[1:]
        lines.append(f'**{label}:** {_flatten(value)}')

    project_name = task.project.name if task and task.project_id else 'ShyDevs'

    children = []
    if mention_line:
        children.append(_text(mention_line))
    children.append(_text(title))
    if lines:
        children.append(_text('\n'.join(lines)[:4000]))
    children.append({'type': SEPARATOR, 'divider': True, 'spacing': 1})
    children.append(_text(f'-# {project_name} · {activity.created_at.strftime("%d/%m %H:%M")}'))

    return {
        'type': CONTAINER,
        'components': children,
    }


def _post(webhook_url, payload):
    try:
        # Discord's incoming-webhook endpoint silently rejects a Components V2
        # payload ("Cannot send an empty message") unless this query param is
        # present — distinct from the flag on the payload itself.
        requests.post(f'{webhook_url}?with_components=true', json=payload, timeout=5)
    except requests.RequestException:
        pass  # best-effort — a Discord hiccup should never break the app


def notify(activity):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url or activity.event_type not in NOTIFY_EVENT_TYPES:
        return

    task = activity.task
    discord_id = None
    if activity.event_type in MENTION_EVENT_TYPES and task and task.assignee_id:
        discord_id = (task.assignee.discord_id or '').strip()

    # Components V2 messages can't use the top-level `content` field, so a
    # mention that should actually ping goes in its own text block instead —
    # Discord still parses/notifies mentions found inside component text.
    mention_line = f'<@{discord_id}>' if discord_id else None
    allowed_mentions = {'parse': [], 'users': [discord_id]} if discord_id else {'parse': []}

    payload = {
        'username': 'ShyDevs',
        'flags': IS_COMPONENTS_V2,
        'components': [build_container(activity, mention_line)],
        'allowed_mentions': allowed_mentions,
    }

    threading.Thread(target=_post, args=(webhook_url, payload), daemon=True).start()
