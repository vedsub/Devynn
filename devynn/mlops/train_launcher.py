import os
from datetime import datetime, timezone
import boto3

def launch_training_job(validated_s3_key: str, instance_type="ml.g4dn.xlarge") -> str:
    sm = boto3.client("sagemaker", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    bucket = os.environ.get("S3_BUCKET_MODELS", os.environ.get("S3_BUCKET_AUDIO", ""))
    job_name = f"devynn-finetune-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    
    sm.create_training_job(
        TrainingJobName=job_name,
        AlgorithmSpecification={
            "TrainingImage": os.environ.get("TRAINING_IMAGE_URI", "<account-id>.dkr.ecr.us-east-1.amazonaws.com/devynn-training:latest"), 
            "TrainingInputMode": "File"
        },
        RoleArn=os.environ.get("SAGEMAKER_ROLE_ARN", "arn:aws:iam::123456789012:role/SageMakerExecutionRole"),
        InputDataConfig=[{
            "ChannelName": "training",
            "DataSource": {
                "S3DataSource": {
                    "S3DataType": "S3Prefix",
                    "S3Uri": f"s3://{bucket}/{validated_s3_key}",
                    "S3DataDistributionType": "FullyReplicated"
                }
            }
        }],
        OutputDataConfig={
            "S3OutputPath": f"s3://{bucket}/model-artifacts/"
        },
        ResourceConfig={
            "InstanceType": instance_type,
            "InstanceCount": 1,
            "VolumeSizeInGB": 50
        },
        HyperParameters={
            "base_model": "mistralai/Mistral-7B-Instruct-v0.2",
            "lora_r": "16",
            "lora_alpha": "32",
            "lora_target_modules": "q_proj,v_proj,k_proj,o_proj",
            "num_epochs": "3",
            "batch_size": "4",
            "learning_rate": "2e-4",
            "bnb_4bit_quant_type": "nf4",
            "use_double_quant": "true"
        },
        StoppingCondition={
            "MaxRuntimeInSeconds": 18000
        },
    )
    return job_name
