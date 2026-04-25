output "rds_endpoint" {
  value = aws_db_instance.postgres.endpoint
}

output "redis_endpoint" {
  value = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "data_bucket" {
  value = aws_s3_bucket.data.id
}

output "models_bucket" {
  value = aws_s3_bucket.models.id
}

output "model_registry_table" {
  value = aws_dynamodb_table.model_registry.name
}
