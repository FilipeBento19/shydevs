"""Keeps a copy of the media people DM to the bot.

Discord's CDN links expire, so the backend downloads each file into its own
storage. If a download fails the attachment is still recorded with the
original link, which keeps working for a while.
"""
import mimetypes
import os
from urllib.parse import urlparse

import requests
from django.core.files.base import ContentFile

from .models import DiscordAttachment
from .storages import kind_for_name

# Only fetch from Discord itself and the GIF providers its link previews use.
ALLOWED_HOST_SUFFIXES = ('discordapp.com', 'discordapp.net', 'tenor.com', 'giphy.com')
MAX_BYTES = 25 * 1024 * 1024
MAX_FILES = 10


def _allowed(url):
    parts = urlparse(url)
    host = (parts.hostname or '').lower()
    return parts.scheme == 'https' and any(host == s or host.endswith('.' + s) for s in ALLOWED_HOST_SUFFIXES)


def _download(url):
    with requests.get(url, stream=True, timeout=20) as resp:
        resp.raise_for_status()
        chunks, size = [], 0
        for chunk in resp.iter_content(64 * 1024):
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError('arquivo grande demais')
            chunks.append(chunk)
        return b''.join(chunks), resp.headers.get('Content-Type', '').split(';')[0].strip()


def save_attachments(message, items):
    """Store each `{url, filename, content_type, gif}` from the bot on `message`."""
    for item in (items or [])[:MAX_FILES]:
        url = (item.get('url') or '').strip()
        if not _allowed(url):
            continue
        name = os.path.basename(item.get('filename') or urlparse(url).path) or 'arquivo'
        content_type = item.get('content_type') or ''
        data = None
        try:
            data, fetched_type = _download(url)
            content_type = content_type or fetched_type
        except (requests.RequestException, ValueError):
            pass
        if not os.path.splitext(name)[1] and content_type:
            name += mimetypes.guess_extension(content_type) or ''
        kind = kind_for_name(name)
        if kind == 'file' and content_type.startswith(('image/', 'video/')):
            kind = content_type.split('/')[0]
        attachment = DiscordAttachment(
            message=message, source_url=url, name=name[:255], kind=kind, is_gif=bool(item.get('gif')),
        )
        if data is not None:
            attachment.file.save(name, ContentFile(data), save=False)
        attachment.save()
