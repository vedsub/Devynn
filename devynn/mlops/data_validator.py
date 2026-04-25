import json
import boto3
import os
from datetime import datetime, timezone

def validate_candidates(s3_key: str) -> dict:
    bucket = os.environ.get("S3_BUCKET_MODELS", os.environ.get("S3_BUCKET_AUDIO", ""))
    s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    
    try:
        obj = s3.get_object(Bucket=bucket, Key=s3_key)
        raw_data = obj["Body"].read().decode("utf-8")
    except Exception as e:
        return {"valid": 0, "invalid": 0, "validated_key": "", "error": str(e)}

    valid = []
    invalid_count = 0
    domains = {"SDE", "DS", "PM"}

    for line in raw_data.strip().split("\n"):
        if not line:
            continue
        record = json.loads(line)
        ans = record.get("answer", "")
        resp = record.get("ai_response", "")
        wps = record.get("wps", 0)
        domain = record.get("job_position", "")

        if len(ans) >= 10 and len(resp) >= 20 and wps > 0 and domain in domains:
            valid.append(record)
        else:
            invalid_count += 1
            
    if not valid:
        return {"valid": 0, "invalid": invalid_count, "validated_key": ""}

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    validated_key = f"training-data/validated/{date_str}/candidates.jsonl"
    
    output_body = "\n".join([json.dumps(v) for v in valid]) + "\n"
    s3.put_object(
        Bucket=bucket,
        Key=validated_key,
        Body=output_body.encode("utf-8")
    )

    return {
        "valid": len(valid),
        "invalid": invalid_count,
        "validated_key": validated_key
    }
