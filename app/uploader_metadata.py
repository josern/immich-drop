"""Uploader-name settings and EXIF Photographer metadata."""

import io
import logging
from typing import Optional

import piexif

from . import db

logger = logging.getLogger("immich_drop.uploader_metadata")


def get_uploader_name_settings() -> dict:
    """Return persisted uploader-name settings with safe defaults."""
    return {
        "enabled": db.get_setting("uploader_name_enabled", "1") == "1",
        "prefix": db.get_setting("uploader_name_prefix", "Photo taken by "),
    }


def get_invite_uploader_name_settings(invite_token: Optional[str]) -> dict:
    """Return uploader-name settings for a local invite, or legacy defaults."""
    if invite_token:
        conn = db.connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT uploader_name_enabled, uploader_name_prefix FROM invites WHERE token = ?",
                (invite_token,),
            )
            row = cur.fetchone()
        finally:
            conn.close()
        if row:
            defaults = get_uploader_name_settings()
            return {
                "enabled": bool(row[0]) if row[0] is not None else defaults["enabled"],
                "prefix": row[1] if row[1] is not None else defaults["prefix"],
            }
    return get_uploader_name_settings()


def format_uploader_photographer(
    name: Optional[str],
    enabled: Optional[bool] = None,
) -> Optional[str]:
    """Return the name alone for EXIF Artist."""
    uploader_name = (name or "").strip()
    use_name = get_uploader_name_settings()["enabled"] if enabled is None else enabled
    if not use_name or not uploader_name:
        return None
    return uploader_name


def format_uploader_description(photographer: Optional[str], prefix: str) -> Optional[str]:
    """Add the configured prefix for Immich's description only."""
    return f"{prefix}{photographer}" if photographer else None


def write_photographer_exif(
    file_bytes: bytes,
    photographer: Optional[str],
) -> tuple[bytes, Optional[str]]:
    """Set EXIF Artist on a JPEG without recompressing its image data."""
    if not photographer:
        return file_bytes, None
    if not file_bytes.startswith(b"\xff\xd8"):
        return file_bytes, "Photographer EXIF is only supported for JPEG images"
    try:
        exif_data = piexif.load(file_bytes)
        exif_data["0th"][piexif.ImageIFD.Artist] = photographer.encode("utf-8")
        exif_bytes = piexif.dump(exif_data)
        output = io.BytesIO()
        piexif.insert(exif_bytes, file_bytes, output)
        return output.getvalue(), None
    except Exception as error:
        logger.exception("Could not write Photographer EXIF metadata")
        return file_bytes, f"Photographer EXIF could not be written: {error}"
