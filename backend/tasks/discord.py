"""Posts Activity events to Discord — a channel via webhook, and for a
handful of "it's your move" events, also a personal DM via bot token —
using Components V2 (Discord's newer message-layout API: colored
containers, formatted text blocks, separators, image galleries — instead
of the classic embed object).

Both are no-ops if their respective env var isn't set (DISCORD_WEBHOOK_URL,
DISCORD_BOT_TOKEN), and every HTTP call is fired from a background thread
so a slow/unreachable Discord never delays the API response that
triggered it. Short-lived processes (a `manage.py` command, a script) must
call flush() before exiting — daemon threads are killed outright when the
process exits, which can silently cut a DM off mid-request (opening the
DM channel and posting the message are two round-trips) even though the
caller saw no error.
"""
import json
import os
import threading
from pathlib import Path

import requests
from django.conf import settings

_pending_threads = []
_pending_lock = threading.Lock()


def _spawn(target, args):
    t = threading.Thread(target=target, args=args, daemon=True)
    with _pending_lock:
        _pending_threads.append(t)
    t.start()
    return t


def flush(timeout=15):
    """Waits for every Discord HTTP call fired so far to finish (or time
    out). Call this at the end of a management command's handle() — the
    request/response-cycle code paths (views, signals from an HTTP
    request) don't need it, since the server process stays alive long
    after the response is sent."""
    with _pending_lock:
        threads = list(_pending_threads)
        _pending_threads.clear()
    for t in threads:
        t.join(timeout=timeout)

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


def build_reminder_container(heading, lines, footer_note):
    """A slightly fancier Components V2 card for the DM-only reminder nudges
    below (nothing goes to the channel for these) — a markdown heading up
    top instead of a plain title line, since it's the only thing standing
    in for a header image here."""
    children = [_text(f'## {heading}'[:4000])]
    if lines:
        children.append(_text('\n'.join(lines)[:4000]))
    children.append({'type': SEPARATOR, 'divider': True, 'spacing': 1})
    children.append(_text(f'-# {footer_note}'))
    return {'type': CONTAINER, 'components': children}


def build_task_reminder_container(heading, task, message, footer_note='Lembrete automático'):
    url = _task_url(task)
    task_line = f'**Tarefa:** {task.code} · {task.title}'
    if url:
        task_line = f'**Tarefa:** [{task.code} · {task.title}]({url})'
    lines = [task_line]
    if task.due_date:
        lines.append(f'**Prazo:** {task.due_date.strftime("%d/%m")}')
    lines.append('')
    lines.append(message)
    return build_reminder_container(heading, lines, footer_note)


def build_digest_container(name, stats):
    lines = [
        f'Oi, {name}! Aqui está o seu resumo:',
        '',
        f'**Tarefas abertas:** {stats["open"]}',
        f'**Em andamento:** {stats["in_progress"]}',
        f'**Atrasadas:** {stats["overdue"]}',
        '',
        'Priorize as atrasadas primeiro.' if stats['overdue'] else 'Nada atrasado no momento — bom trabalho.',
    ]
    return build_reminder_container('Seu resumo de tarefas', lines, 'Resumo automático · a cada 2 dias')


def send_task_reminder_dm(task, heading, message, footer_note='Lembrete automático'):
    if not (task.assignee_id and (task.assignee.discord_id or '').strip()):
        return
    if not os.environ.get('DISCORD_BOT_TOKEN'):
        return
    payload = {
        'flags': IS_COMPONENTS_V2,
        'components': [build_task_reminder_container(heading, task, message, footer_note)],
    }
    _spawn(_send_dm, (task.assignee.discord_id.strip(), payload, None))


def send_digest_dm(person, stats):
    if not ((person.discord_id or '').strip() and os.environ.get('DISCORD_BOT_TOKEN')):
        return
    payload = {'flags': IS_COMPONENTS_V2, 'components': [build_digest_container(person.name, stats)]}
    _spawn(_send_dm, (person.discord_id.strip(), payload, None))


def _post_webhook(webhook_url, payload, banner_path=None):
    try:
        # Discord's incoming-webhook endpoint silently rejects a Components V2
        # payload ("Cannot send an empty message") unless this query param is
        # present — distinct from the flag on the payload itself. Regular bot
        # channel messages (below) don't need this quirk.
        url = f'{webhook_url}?with_components=true'
        if banner_path:
            with open(banner_path, 'rb') as f:
                resp = requests.post(
                    url,
                    data={'payload_json': json.dumps(payload)},
                    files={'files[0]': (banner_path.name, f, 'image/png')},
                    timeout=10,
                )
        else:
            resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
    except requests.RequestException:
        pass  # best-effort — a Discord hiccup should never break the app


BOT_API_BASE = 'https://discord.com/api/v10'


def _bot_headers():
    token = os.environ.get('DISCORD_BOT_TOKEN')
    return {'Authorization': f'Bot {token}'} if token else None


_dm_channel_cache = {}
_dm_channel_lock = threading.Lock()


def _open_dm_channel(headers, discord_id):
    # Discord's create-DM-channel endpoint is idempotent (repeat calls for
    # the same recipient return the same channel) but errors with a 400
    # under concurrency — several reminders firing for the same person at
    # once each open it in their own thread. Caching sidesteps that
    # entirely instead of trying to out-guess their race condition. The
    # lock spans the whole check-then-fetch so two threads racing on the
    # same not-yet-cached recipient can't both hit the API at once either.
    with _dm_channel_lock:
        cached = _dm_channel_cache.get(discord_id)
        if cached:
            return cached
        resp = requests.post(
            f'{BOT_API_BASE}/users/@me/channels', headers=headers,
            json={'recipient_id': discord_id}, timeout=10,
        )
        resp.raise_for_status()
        channel_id = resp.json()['id']
        _dm_channel_cache[discord_id] = channel_id
        return channel_id


def _send_dm(discord_id, payload, banner_path=None):
    headers = _bot_headers()
    if not headers:
        return
    try:
        channel_id = _open_dm_channel(headers, discord_id)
        url = f'{BOT_API_BASE}/channels/{channel_id}/messages'
        if banner_path:
            with open(banner_path, 'rb') as f:
                resp = requests.post(
                    url, headers=headers,
                    data={'payload_json': json.dumps(payload)},
                    files={'files[0]': (banner_path.name, f, 'image/png')},
                    timeout=10,
                )
        else:
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
    except requests.RequestException:
        pass  # best-effort — a bot hiccup should never break the app


def notify(activity):
    if activity.event_type not in NOTIFY_EVENT_TYPES:
        return

    task = activity.task
    discord_id = None
    if activity.event_type in MENTION_EVENT_TYPES and task and task.assignee_id:
        discord_id = (task.assignee.discord_id or '').strip() or None

    banner_path = _banner_path(activity.event_type)
    banner_filename = banner_path.name if banner_path else None

    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if webhook_url:
        # Components V2 messages can't use the top-level `content` field, so
        # a mention that should actually ping goes in its own text block
        # instead — Discord still parses/notifies mentions found there.
        mention_line = f'<@{discord_id}>' if discord_id else None
        allowed_mentions = {'parse': [], 'users': [discord_id]} if discord_id else {'parse': []}
        payload = {
            'username': 'ShyDevs',
            'flags': IS_COMPONENTS_V2,
            'components': [build_container(activity, mention_line, banner_filename)],
            'allowed_mentions': allowed_mentions,
        }
        if banner_path:
            payload['attachments'] = [{'id': 0, 'filename': banner_filename}]
        _spawn(_post_webhook, (webhook_url, payload, banner_path))

    # These 3 events used to also DM a copy of the same card, but that's now
    # handled by the dedicated DM-only reminders in send_discord_reminders
    # (stale pending/in-progress, due-soon) — the channel @mention is enough
    # here, no need to double up.
