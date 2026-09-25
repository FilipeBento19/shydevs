"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import mimetypes
import os
import re

from django.conf import settings
from django.contrib import admin
from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.urls import include, path, re_path
from django.utils._os import safe_join
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('tasks.urls')),
]


def _read_slice(f, remaining, chunk=64 * 1024):
    try:
        while remaining > 0:
            data = f.read(min(chunk, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data
    finally:
        f.close()


def serve_media(request, path):
    """Dev-only media server with Range support.

    django.views.static.serve ignores Range, so browsers can't seek: dragging
    a video's progress bar restarts it from 0:00. Production media lives on
    Cloudinary, which supports Range natively.
    """
    m = re.match(r'bytes=(\d*)-(\d*)$', request.headers.get('Range', ''))
    if not m or not (m.group(1) or m.group(2)):
        return serve(request, path, document_root=settings.MEDIA_ROOT)
    try:
        full = safe_join(settings.MEDIA_ROOT, path)
    except ValueError:
        raise Http404
    if not os.path.isfile(full):
        raise Http404
    size = os.path.getsize(full)
    if m.group(1):
        start = int(m.group(1))
        end = min(int(m.group(2)) if m.group(2) else size - 1, size - 1)
    else:  # suffix range: the last N bytes
        start, end = max(size - int(m.group(2)), 0), size - 1
    if start > end:
        resp = HttpResponse(status=416)
        resp['Content-Range'] = f'bytes */{size}'
        return resp
    f = open(full, 'rb')
    f.seek(start)
    resp = StreamingHttpResponse(
        _read_slice(f, end - start + 1), status=206,
        content_type=mimetypes.guess_type(full)[0] or 'application/octet-stream',
    )
    resp['Content-Length'] = str(end - start + 1)
    resp['Content-Range'] = f'bytes {start}-{end}/{size}'
    resp['Accept-Ranges'] = 'bytes'
    return resp


if settings.DEBUG:
    urlpatterns += [re_path(r'^%s(?P<path>.*)$' % re.escape(settings.MEDIA_URL.lstrip('/')), serve_media)]
