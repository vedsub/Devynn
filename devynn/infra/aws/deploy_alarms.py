import os
import boto3

def deploy_alarms():
    cw = boto3.client("cloudwatch", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    sns_arn = os.environ.get("SNS_ALERT_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:devynn-alerts")

    # 1. HighAPILatency: RequestLatencyMs p99 > 5000ms for 3 consecutive periods
    cw.put_metric_alarm(
        AlarmName="HighAPILatency",
        MetricName="RequestLatencyMs",
        Namespace="Devynn/API",
        Statistic="Average",
        ExtendedStatistic="p99",
        Period=60,
        EvaluationPeriods=3,
        Threshold=5000,
        ComparisonOperator="GreaterThanThreshold",
        AlarmActions=[sns_arn]
    )

    # 2. HighLLMLatency: LLMLatencyMs p99 > 15000ms for 2 periods
    cw.put_metric_alarm(
        AlarmName="HighLLMLatency",
        MetricName="LLMLatencyMs",
        Namespace="Devynn/API",
        Statistic="Average",
        ExtendedStatistic="p99",
        Period=60,
        EvaluationPeriods=2,
        Threshold=15000,
        ComparisonOperator="GreaterThanThreshold",
        AlarmActions=[sns_arn]
    )

    # 3. LowCacheHitRate: CacheHit average < 0.2 for 5 periods
    cw.put_metric_alarm(
        AlarmName="LowCacheHitRate",
        MetricName="CacheHit",
        Namespace="Devynn/API",
        Statistic="Average",
        Period=300,
        EvaluationPeriods=5,
        Threshold=0.2,
        ComparisonOperator="LessThanThreshold",
        AlarmActions=[sns_arn]
    )

    # 4. TrainingDataDry: Devynn/MLOps training_skipped > 3 for 3 consecutive weeks
    cw.put_metric_alarm(
        AlarmName="TrainingDataDry",
        MetricName="TrainingSkipped",
        Namespace="Devynn/MLOps",
        Statistic="SampleCount",
        Period=604800,  # 1 week in seconds
        EvaluationPeriods=3,
        Threshold=3,
        ComparisonOperator="GreaterThanThreshold",
        AlarmActions=[sns_arn]
    )
    
    print("Alarms successfully deployed.")

if __name__ == "__main__":
    deploy_alarms()
