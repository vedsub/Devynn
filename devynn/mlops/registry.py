import boto3
import os
from boto3.dynamodb.conditions import Attr

def get_latest_approved() -> dict:
    table = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1")).Table("devynn-model-registry")
    items = sorted(
        table.scan(FilterExpression=Attr("approved").eq(True))["Items"],
        key=lambda x: x["created_at"],
        reverse=True
    )
    if not items:
        raise RuntimeError("No approved models")
    return items[0]
