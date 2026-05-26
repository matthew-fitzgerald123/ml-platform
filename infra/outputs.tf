output "rds_endpoint" {
  description = "RDS Postgres connection endpoint"
  value       = aws_db_instance.postgres.endpoint
}

output "rds_port" {
  description = "RDS Postgres port"
  value       = aws_db_instance.postgres.port
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "redis_port" {
  description = "ElastiCache Redis port"
  value       = aws_elasticache_cluster.redis.port
}

output "database_url" {
  description = "SQLAlchemy DATABASE_URL (paste password manually)"
  value       = "postgresql://${var.db_username}:<password>@${aws_db_instance.postgres.endpoint}/${var.db_name}"
  sensitive   = false
}

output "redis_url" {
  description = "Redis URL for the application"
  value       = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:${aws_elasticache_cluster.redis.port}"
}
