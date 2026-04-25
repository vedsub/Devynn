"""
Data flywheel service to append raw transcripts to S3.
"""
import json
import logging
from datetime import datetime, timezone

import aioboto3
from app.core.config import settings

logger = logging.getLogger("devynn.flywheel")

async def log_training_candidate(turn, session):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "job_position": session.domain,
        "answer": turn.transcript,
        "ai_response": turn.ai_response,
        "pace_label": turn.pace_label,
        "wps": turn.wps,
        "model_version": turn.model_version,
        "session_id": str(session.id),
    }
    key = f"training-data/raw/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}/candidates.jsonl"
    try:
        session_boto = aioboto3.Session()
        async with session_boto.client("s3", region_name=settings.AWS_REGION) as s3:
            try: 
                obj = await s3.get_object(Bucket=settings.S3_BUCKET_AUDIO, Key=key)  # fallback to AWS audio bucket, ideally S3_BUCKET_MODELS
                existing = (await obj["Body"].read()).decode()
            except Exception:
                existing = ""
                
            await s3.put_object(
                Bucket=settings.S3_BUCKET_AUDIO, 
                Key=key,
                Body=(existing + json.dumps(record) + "\n").encode()
            )
    except Exception as e:
        logger.error(str(e))  # never raise
