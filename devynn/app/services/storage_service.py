"""
S3 audio storage via aioboto3.
Failures are logged but never break the request.
"""

from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


async def upload_audio(
    file_bytes: bytes,
    session_id: str,
    turn_num: int,
) -> str:
    """Upload WAV bytes to S3 and return the object key.

    Returns the S3 key on success, or an empty string on failure.
    """
    import aioboto3

    key = f"audio/{session_id}/{turn_num}.wav"

    try:
        s3_session = aioboto3.Session()
        async with s3_session.client(
            "s3", region_name=settings.AWS_REGION
        ) as s3:
            await s3.put_object(
                Bucket=settings.S3_BUCKET_AUDIO,
                Key=key,
                Body=file_bytes,
                ContentType="audio/wav",
            )
        logger.info("Uploaded %s to s3://%s", key, settings.S3_BUCKET_AUDIO)
        return key
    except Exception:
        logger.exception("S3 upload failed for key=%s — continuing", key)
        return ""
