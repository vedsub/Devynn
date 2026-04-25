provider "aws" {
  region = var.aws_region
}

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_db_instance" "postgres" {
  identifier                  = "${var.project}-postgres"
  engine                      = "postgres"
  engine_version              = "16"
  instance_class              = "db.t3.micro"
  allocated_storage           = 20
  storage_type                = "gp3"
  db_name                     = "devynn"
  username                    = var.db_username
  password                    = random_password.db.result
  skip_final_snapshot         = false
  final_snapshot_identifier   = "${var.project}-final"
  backup_retention_period     = 7
  deletion_protection         = true

  tags = {
    project = var.project
  }
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${var.project}-redis"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
}

resource "aws_s3_bucket" "data" {
  bucket = "${var.project}-audio-${var.aws_region}"
}

resource "aws_s3_bucket_lifecycle_configuration" "audio_archive" {
  bucket = aws_s3_bucket.data.id

  rule {
    id     = "glacier-90d"
    status = "Enabled"

    filter {
      prefix = "audio/"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

resource "aws_s3_bucket" "models" {
  bucket = "${var.project}-models-${var.aws_region}"
}

resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_dynamodb_table" "model_registry" {
  name           = "devynn-model-registry"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "version"
  range_key      = "created_at"

  attribute {
    name = "version"
    type = "S"
  }
  attribute {
    name = "created_at"
    type = "S"
  }
}

resource "aws_secretsmanager_secret" "db_pw" {
  name = "${var.project}/db-password"
}

resource "aws_secretsmanager_secret_version" "db_pw" {
  secret_id     = aws_secretsmanager_secret.db_pw.id
  secret_string = random_password.db.result
}
