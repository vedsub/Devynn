import os
import boto3
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    MIN_EXAMPLES = int(os.environ.get("MIN_TRAINING_EXAMPLES", "200"))
    bucket = os.environ.get("S3_BUCKET_MODELS", os.environ.get("S3_BUCKET_AUDIO", ""))
    s3 = boto3.client("s3")
    
    total_valid = 0
    now = datetime.now(timezone.utc)
    
    # We want candidates.jsonl from the last 7 days
    for i in range(7):
        target_date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        key = f"training-data/raw/{target_date}/candidates.jsonl"
        
        try:
            # We will use the existing validate_candidates
            from devynn.mlops.data_validator import validate_candidates
            result = validate_candidates(key)
            total_valid += result.get("valid", 0)
        except Exception as e:
            logger.warning(f"Failed parsing/validating for {key}: {e}")
            
    cloudwatch = boto3.client("cloudwatch", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    
    if total_valid < MIN_EXAMPLES:
        logger.info(f"Skipping training, total_valid ({total_valid}) < {MIN_EXAMPLES}")
        cloudwatch.put_metric_data(
            Namespace="Devynn/MLOps",
            MetricData=[{
                "MetricName": "TrainingSkipped",
                "Value": 1
            }]
        )
        return {"status": "skipped", "valid_count": total_valid}
        
    logger.info(f"Launching training with {total_valid} valid examples")
    
    try:
        from devynn.mlops.train_launcher import launch_training_job
        # We'd likely pass a folder path (validated S3 prefix covering last week)
        start_date = (now - timedelta(days=6)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        # For simplicity, telling train launcher to use the validated prefix
        s3_prefix = f"training-data/validated/"
        
        job_name = launch_training_job(s3_prefix)
        cloudwatch.put_metric_data(
            Namespace="Devynn/MLOps",
            MetricData=[{
                "MetricName": "TrainingLaunched",
                "Value": 1
            }]
        )
        return {"status": "launched", "job_name": job_name, "valid_count": total_valid}
    except Exception as e:
        logger.error(f"Failed to launch training: {e}")
        raise e
