"""Fail-closed technical gate for individual scene image files."""
from pathlib import Path
from PIL import Image

def validate_scene_image(path, expected_size=(1080, 1080)):
    p = Path(path)
    errors = []
    if not p.is_file():
        return {'status': 'BLOCKED', 'errors': ['image_missing'], 'manual_review_required': True}
    try:
        with Image.open(p) as im:
            im.verify()
        with Image.open(p) as im:
            size = im.size
            if size != expected_size:
                errors.append(f'wrong_dimensions:{size[0]}x{size[1]}')
            if im.format not in ('PNG', 'JPEG', 'WEBP'):
                errors.append('unsupported_format')
    except Exception:
        errors.append('unreadable_image')
    return {'status': 'BLOCKED' if errors else 'TECHNICALLY_VALID_PENDING_VISUAL_REVIEW',
            'errors': errors, 'manual_review_required': True}
