"""Storage for task references, which — unlike the plain MediaCloudinaryStorage
used everywhere else — has to accept images, videos AND arbitrary files.

Cloudinary keeps three separate resource types ("image", "video", "raw") and
a file only ever resolves under the type it was uploaded as. The stock
MediaCloudinaryStorage uploads everything as one fixed type, so a video or a
zip either fails to upload or can't be found again at its URL. This one picks
the type from the file extension, and keeps the extension on the stored name
(Cloudinary drops it from image/video public IDs) so the same extension check
can pick the right type again when building the URL or deleting the file.

Local development has no Cloudinary and just uses the regular default storage.
"""
import os

from django.conf import settings
from django.core.files.storage import default_storage

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.avif'}
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.m4v', '.mkv', '.avi', '.ogv'}


def kind_for_name(name):
    """'image' | 'video' | 'file', judged by extension alone."""
    ext = os.path.splitext(str(name).split('?')[0])[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return 'image'
    if ext in VIDEO_EXTENSIONS:
        return 'video'
    return 'file'


def _cloudinary_resource_type(name):
    return {'image': 'image', 'video': 'video'}.get(kind_for_name(name), 'raw')


def _build_cloudinary_storage():
    import cloudinary.uploader
    from cloudinary_storage.storage import MediaCloudinaryStorage

    class ReferenceCloudinaryStorage(MediaCloudinaryStorage):
        def _get_resource_type(self, name):
            return _cloudinary_resource_type(name)

        def _save(self, name, content):
            public_id = super()._save(name, content)
            if _cloudinary_resource_type(name) == 'raw':
                return public_id  # raw public IDs already include the extension
            return public_id + os.path.splitext(name)[1].lower()

        def delete(self, name):
            resource_type = _cloudinary_resource_type(name)
            public_id = name if resource_type == 'raw' else os.path.splitext(name)[0]
            response = cloudinary.uploader.destroy(public_id, invalidate=True, resource_type=resource_type)
            return response['result'] == 'ok'

    return ReferenceCloudinaryStorage()


_cloudinary_storage = None


def get_reference_storage():
    """Callable storage for Reference.file (evaluated lazily, so the Cloudinary
    imports only happen — and only need to work — when it's actually enabled)."""
    global _cloudinary_storage
    if not getattr(settings, 'USE_CLOUDINARY', False):
        return default_storage
    if _cloudinary_storage is None:
        _cloudinary_storage = _build_cloudinary_storage()
    return _cloudinary_storage
