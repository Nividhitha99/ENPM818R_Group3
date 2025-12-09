# AWS Secrets Manager for Application Secrets
# Stores sensitive data like JWT secrets, API keys, etc.

# JWT Secret for Auth Service
resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

resource "aws_secretsmanager_secret" "jwt_secret" {
  name        = "video-analytics/jwt-secret"
  description = "JWT secret for authentication service"

  tags = {
    Name    = "video-analytics-jwt-secret"
    Project = "ENPM818R_Group3"
  }
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id = aws_secretsmanager_secret.jwt_secret.id
  secret_string = jsonencode({
    jwt_secret = random_password.jwt_secret.result
  })
}

# Outputs
output "jwt_secret_arn" {
  value       = aws_secretsmanager_secret.jwt_secret.arn
  description = "Secrets Manager ARN for JWT secret"
  sensitive   = true
}
