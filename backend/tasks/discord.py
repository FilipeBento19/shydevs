"""Posts Activity events to a Discord channel via webhook, using Components V2
(Discord's newer message-layout API — colored containers, formatted text
blocks, separators — instead of the classic embed object).

No-op if DISCORD_WEBHOOK_URL isn't set, and the actual HTTP call is fired
from a background thread so a slow/unreachable Discord never delays the API
response that triggered it.
"""
import json
import os
import threading
from pathlib import Path

import requests
from django.conf import settings

# Components V2 component type IDs (Discord message components API).
CONTAINER = 17
TEXT_DISPLAY = 10
SEPARATOR = 14
MEDIA_GALLERY = 12

# A message built from components (instead of content/embeds) must carry
# this flag, and in exchange cannot also set `content` or `embeds`.
IS_COMPONENTS_V2 = 1 << 15

# One banner image per event type, named after it — drop a PNG in here to
# have it show up automatically, no code change needed.
BANNERS_DIR = Path(settings.BASE_DIR) / 'static' / 'webhook_banners'


def _banner_path(event_type):
    path = BANNERS_DIR / f'{event_type}.png'
    return path if path.is_file() else None

# Checklist toggles/additions are intentionally excluded — teams check items
# off constantly, and pinging Discord for every single one would flood the
# channel. They still show up in the app's own Histórico either way.
NOTIFY_EVENT_TYPES = {
    'task_created',
    'task_assigned',
    'task_status',
    'task_completed',
    'task_updated',
    'comment',
    'overdue',
}
# Events worth @mentioning the assignee for — the ones where it's genuinely
# their move next. Status updates/comments/checklist stay silent pings.
MENTION_EVENT_TYPES = {'task_created', 'task_assigned', 'overdue'}


def _task_url(task):
    base = (os.environ.get('FRONTEND_URL') or '').rstrip('/')
    return f'{base}/tasks/{task.id}' if base and task else None


FIELD_LABELS = {
    'título': 'Título',
    'descrição': 'Descrição',
    'cargo': 'Cargo',
    'prazo': 'Prazo',
    'prioridade': 'Prioridade',
    'responsável': 'Responsável',
    'status': 'Status',
    'etapa': 'Etapa',
    'nota de conclusão': 'Nota de Conclusão',
    'marcação': 'Marcado como concluída',
    'comentário': 'Comentário',
}


def _label(key):
    key = str(key)
    return FIELD_LABELS.get(key, key[:1].upper() + key[1:])


def _format_scalar(value):
    if isinstance(value, bool):
        return 'Sim' if value else 'Não'
    if value in ('True', 'False'):
        return 'Sim' if value == 'True' else 'Não'
    return str(value)


# Quoted-value fields: the interesting part is the free-text content itself,
# not a before/after transition, so show it as a quote instead of an arrow.
QUOTED_FIELDS = {'nota de conclusão', 'comentário'}


def _detail_lines(activity):
    """Turns activity.details into readable "**Label:** value" lines. The
    shape of `details` varies by event_type — see signals.py/views.py for
    where each one is built — so this reads by event_type rather than
    guessing from the raw structure."""
    details = activity.details or {}
    event_type = activity.event_type

    if event_type in ('task_status', 'task_completed', 'task_assigned'):
        # {'antes': ..., 'depois': ...} — only the resulting value matters.
        label = 'Responsável' if event_type == 'task_assigned' else 'Status'
        depois = details.get('depois')
        return [f'**{label}:** {_format_scalar(depois)}'] if depois is not None else []

    if event_type == 'task_updated':
        # {'alterações': {'campo': {'antes': ..., 'depois': ...}, ...}}
        lines = []
        for field_key, change in (details.get('alterações') or {}).items():
            depois = change.get('depois') if isinstance(change, dict) else change
            if field_key in QUOTED_FIELDS:
                lines.append(f'**{_label(field_key)}:** "{depois}"')
            else:
                lines.append(f'**{_label(field_key)}:** {_format_scalar(depois)}')
        return lines

    lines = []
    for key, value in list(details.items())[:6]:
        if str(key) in QUOTED_FIELDS:
            lines.append(f'**{_label(key)}:** "{value}"')
        else:
            lines.append(f'**{_label(key)}:** {_format_scalar(value)}')
    return lines


def _text(content):
    return {'type': TEXT_DISPLAY, 'content': content}


def build_container(activity, mention_line=None, banner_filename=None):
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
    lines.extend(_detail_lines(activity))

    project_name = task.project.name if task and task.project_id else 'ShyDevs'

    children = []
    if banner_filename:
        children.append({
            'type': MEDIA_GALLERY,
            'items': [{'media': {'url': f'attachment://{banner_filename}'}}],
        })
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


def _post(webhook_url, payload, banner_path=None):
    try:
        # Discord's incoming-webhook endpoint silently rejects a Components V2
        # payload ("Cannot send an empty message") unless this query param is
        # present — distinct from the flag on the payload itself.
        url = f'{webhook_url}?with_components=true'
        if banner_path:
            with open(banner_path, 'rb') as f:
                requests.post(
                    url,
                    data={'payload_json': json.dumps(payload)},
                    files={'files[0]': (banner_path.name, f, 'image/png')},
                    timeout=10,
                )
        else:
            requests.post(url, json=payload, timeout=5)
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

    banner_path = _banner_path(activity.event_type)
    payload = {
        'username': 'ShyDevs',
        'flags': IS_COMPONENTS_V2,
        'components': [build_container(activity, mention_line, banner_path and banner_path.name)],
        'allowed_mentions': allowed_mentions,
    }
    if banner_path:
        payload['attachments'] = [{'id': 0, 'filename': banner_path.name}]

    threading.Thread(target=_post, args=(webhook_url, payload, banner_path), daemon=True).start()
