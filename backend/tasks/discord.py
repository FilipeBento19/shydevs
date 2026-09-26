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
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

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
BRASILIA = ZoneInfo('America/Sao_Paulo')
DEFAULT_FRONTEND_URL = 'https://shydevs.vercel.app'


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
    base = (os.environ.get('FRONTEND_URL') or DEFAULT_FRONTEND_URL).rstrip('/')
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


def _standard_footer(project_name='Slayer Reborn', moment=None, note=None):
    moment = (moment or datetime.now(timezone.utc)).astimezone(BRASILIA)
    site_url = (os.environ.get('FRONTEND_URL') or DEFAULT_FRONTEND_URL).rstrip('/')
    first_line = f'-# {project_name or "Slayer Reborn"} · {moment.strftime("%d/%m %H:%M")}'
    if note:
        first_line += f' · {note}'
    return f'{first_line}\n-# [Acessar o site]({site_url})'


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

    project_name = task.project.name if task and task.project_id else 'Slayer Reborn'

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
    children.append(_text(_standard_footer(project_name, activity.created_at)))

    return {
        'type': CONTAINER,
        'components': children,
    }


def build_reminder_container(heading, lines, footer_note, project_name='Slayer Reborn'):
    """A slightly fancier Components V2 card for the DM-only reminder nudges
    below (nothing goes to the channel for these) — a markdown heading up
    top instead of a plain title line, since it's the only thing standing
    in for a header image here."""
    children = [_text(f'## {heading}'[:4000])]
    if lines:
        children.append(_text('\n'.join(lines)[:4000]))
    children.append({'type': SEPARATOR, 'divider': True, 'spacing': 1})
    children.append(_text(_standard_footer(project_name, note=footer_note)))
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
    project_name = task.project.name if task.project_id else 'Slayer Reborn'
    return build_reminder_container(heading, lines, footer_note, project_name)


def build_digest_container(name, stats, project_name='Slayer Reborn'):
    lines = [
        f'Oi, {name}! Aqui está o seu resumo:',
        '',
        f'**Tarefas abertas:** {stats["open"]}',
        f'**Em andamento:** {stats["in_progress"]}',
        f'**Atrasadas:** {stats["overdue"]}',
        '',
        'Priorize as atrasadas primeiro.' if stats['overdue'] else 'Nada atrasado no momento — bom trabalho.',
    ]
    return build_reminder_container('Seu resumo de tarefas', lines, 'Resumo automático · a cada 2 dias', project_name)


def _log_outgoing(person, discord_id, source, content):
    """Records a DM in the Bot tab's history. Only DMs are logged here —
    the webhook channel notifications are a separate, unlogged system.
    Never lets a logging failure take down the actual send."""
    from .models import DiscordMessage
    if not _dm_allowed(discord_id):
        return  # it wasn't actually sent, so it doesn't belong in the history
    try:
        DiscordMessage.objects.create(
            project=person.project if person else None,
            person=person,
            discord_id=discord_id,
            direction=DiscordMessage.Direction.OUTGOING,
            source=source,
            content=content,
        )
    except Exception:
        pass


def send_task_reminder_dm(task, heading, message, source, footer_note='Lembrete automático', person=None):
    person = person or task.assignee
    if not (person and (person.discord_id or '').strip()):
        return
    if not os.environ.get('DISCORD_BOT_TOKEN'):
        return
    discord_id = person.discord_id.strip()
    payload = {
        'flags': IS_COMPONENTS_V2,
        'components': [build_task_reminder_container(heading, task, message, footer_note)],
    }
    _spawn(_send_dm, (discord_id, payload, None))
    _log_outgoing(person, discord_id, source, f'{heading}\n{message}')


def send_digest_dm(person, stats):
    if not ((person.discord_id or '').strip() and os.environ.get('DISCORD_BOT_TOKEN')):
        return
    discord_id = person.discord_id.strip()
    payload = {
        'flags': IS_COMPONENTS_V2,
        'components': [build_digest_container(person.name, stats, person.project.name)],
    }
    _spawn(_send_dm, (discord_id, payload, None))
    content = f'Abertas: {stats["open"]} · Em andamento: {stats["in_progress"]} · Atrasadas: {stats["overdue"]}'
    _log_outgoing(person, discord_id, 'digest', content)


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


def _dm_allowed(discord_id):
    """Local safety net: when DISCORD_DM_ONLY_IDS (comma-separated Discord IDs)
    is set, the bot DMs only those IDs, so testing never messages the team.
    Unset (production) means everyone."""
    only = [i.strip() for i in os.environ.get('DISCORD_DM_ONLY_IDS', '').split(',') if i.strip()]
    return not only or str(discord_id).strip() in only


def _open_dm_channel(headers, discord_id):
    if not _dm_allowed(discord_id):
        raise requests.ConnectionError('DM bloqueada: DISCORD_DM_ONLY_IDS não inclui este ID')
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


def send_plain_dm(discord_id, text, person=None):
    """Blocking, and returns whether it actually worked — used by the
    admin's "send a Discord message" feature on the Team screen, where the
    caller wants per-recipient success/failure to show back in the UI
    rather than firing and forgetting like the automated notifications."""
    headers = _bot_headers()
    if not headers:
        return False
    try:
        channel_id = _open_dm_channel(headers, discord_id)
        resp = requests.post(
            f'{BOT_API_BASE}/channels/{channel_id}/messages', headers=headers,
            json={'content': text, 'allowed_mentions': {'parse': []}}, timeout=10,
        )
        resp.raise_for_status()
        _log_outgoing(person, discord_id, 'admin', text)
        return True
    except requests.RequestException:
        return False


def send_verification_confirmation_dm(discord_id, person=None):
    """Confirms the handshake using Discord's modern Components V2 layout."""
    headers = _bot_headers()
    if not headers:
        return False
    name = person.name if person else 'Usuário ShyDevs'
    project_name = person.project.name if person and person.project_id else 'Slayer Reborn'
    payload = {
        'flags': IS_COMPONENTS_V2,
        'components': [{
            'type': CONTAINER,
            'accent_color': 0x7C6FFF,
            'components': [
                _text('## Discord verificado!'),
                _text('Sua conta foi conectada ao **ShyDevs** com sucesso.'),
                {'type': SEPARATOR, 'divider': True, 'spacing': 1},
                _text(
                    f'**Conta conectada**\n{name}\n\n'
                    '**Status**\n🟢 Pronto para receber DMs\n\n'
                    '**O que muda agora?**\n'
                    'Você já pode receber avisos, lembretes e mensagens da equipe diretamente por aqui.'
                ),
                {'type': SEPARATOR, 'divider': True, 'spacing': 1},
                _text(_standard_footer(project_name)),
            ],
        }],
    }
    try:
        channel_id = _open_dm_channel(headers, discord_id)
        resp = requests.post(
            f'{BOT_API_BASE}/channels/{channel_id}/messages',
            headers=headers, json=payload, timeout=10,
        )
        resp.raise_for_status()
        _log_outgoing(person, discord_id, 'admin', 'Discord verificado com sucesso.')
        return True
    except requests.RequestException:
        return False


def send_unverified_webhook(discord_ids, project_name='ShyDevs', test=False):
    """Mentions unverified members using Discord's modern Components V2 card."""
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    discord_ids = list(dict.fromkeys(str(value).strip() for value in discord_ids if str(value).strip()))
    if not webhook_url or not discord_ids:
        return False
    mentions = ' '.join(f'<@{discord_id}>' for discord_id in discord_ids)
    banner_path = BANNERS_DIR / 'discord_unverified.png'
    banner_filename = banner_path.name if banner_path.is_file() else None
    card_components = []
    if banner_filename:
        card_components.append({
            'type': MEDIA_GALLERY,
            'items': [{'media': {'url': f'attachment://{banner_filename}'}}],
        })
    card_components.extend([
        _text('## Verifique no site da ShyDevs'),
        _text(mentions),
        _text('Precisamos confirmar que o bot consegue falar com você por DM.'),
        {'type': SEPARATOR, 'divider': True, 'spacing': 1},
        _text(
            '**Como verificar**\n'
            '1. Entre no site e abra o menu da sua foto.\n'
            '2. Clique em **Verificar Discord**.\n'
            '3. Copie o código `SHY-XXXXXX` e envie na DM do bot.\n\n'
            'Leva menos de um minuto e libera os avisos privados.'
        ),
        {'type': SEPARATOR, 'divider': True, 'spacing': 1},
        _text(_standard_footer(
            project_name,
            note='Lembrete a cada 2 dias' + (' · mensagem de teste' if test else ''),
        )),
    ])
    payload = {
        'username': 'ShyDevs',
        'flags': IS_COMPONENTS_V2,
        'components': [{
            'type': CONTAINER,
            'components': card_components,
        }],
        'allowed_mentions': {'parse': [], 'users': discord_ids},
    }
    if banner_filename:
        payload['attachments'] = [{'id': 0, 'filename': banner_filename}]
    try:
        url = f'{webhook_url}?with_components=true'
        if banner_filename:
            with open(banner_path, 'rb') as banner:
                resp = requests.post(
                    url,
                    data={'payload_json': json.dumps(payload)},
                    files={'files[0]': (banner_filename, banner, 'image/png')},
                    timeout=15,
                )
        else:
            resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException:
        return False


def notify(activity):
    if activity.event_type not in NOTIFY_EVENT_TYPES:
        return

    task = activity.task
    discord_ids = []
    if activity.event_type in MENTION_EVENT_TYPES and task:
        discord_ids = [d for d in ((p.discord_id or '').strip() for p in task.people()) if d]

    banner_path = _banner_path(activity.event_type)
    banner_filename = banner_path.name if banner_path else None

    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if webhook_url:
        # Components V2 messages can't use the top-level `content` field, so
        # a mention that should actually ping goes in its own text block
        # instead — Discord still parses/notifies mentions found there.
        mention_line = ' '.join(f'<@{d}>' for d in discord_ids) or None
        allowed_mentions = {'parse': [], 'users': discord_ids} if discord_ids else {'parse': []}
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
