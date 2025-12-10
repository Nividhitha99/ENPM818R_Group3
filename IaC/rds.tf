# RDS PostgreSQL Database for Video Analytics
# Stores video metadata, views, and likes data

# Security Group for RDS
resource "aws_security_group" "rds" {
  name        = "video-analytics-rds-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "PostgreSQL from EKS pods"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.cluster_security_group_id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "video-analytics-rds-sg"
    Project = "ENPM818R_Group3"
  }
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "video-analytics-db-subnet"
  subnet_ids = module.vpc.private_subnets

  tags = {
    Name    = "video-analytics-db-subnet"
    Project = "ENPM818R_Group3"
  }
}

# Random password for RDS master user
resource "random_password" "rds_password" {
  length  = 16
  special = true
}

# Store RDS password in Secrets Manager
resource "aws_secretsmanager_secret" "rds_password" {
  name        = "video-analytics/rds-password"
  description = "RDS PostgreSQL master password"

  tags = {
    Name    = "video-analytics-rds-password"
    Project = "ENPM818R_Group3"
  }
}

resource "aws_secretsmanager_secret_version" "rds_password" {
  secret_id = aws_secretsmanager_secret.rds_password.id
  secret_string = jsonencode({
    username = "videoadmin"
    password = random_password.rds_password.result
    engine   = "postgres"
    host     = aws_db_instance.main.address
    port     = 5432
    dbname   = "video_analytics"
  })
}

# RDS PostgreSQL Instance
resource "aws_db_instance" "main" {
  identifier     = "video-analytics-db"
  engine         = "postgres"
  engine_version = "16.3"
  instance_class = "db.t3.micro"

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "video_analytics"
  username = "videoadmin"
  password = random_password.rds_password.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "mon:04:00-mon:05:00"

  skip_final_snapshot       = true
  final_snapshot_identifier = "video-analytics-db-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  tags = {
    Name    = "video-analytics-db"
    Project = "ENPM818R_Group3"
  }
}

# Outputs
output "rds_endpoint" {
  value       = aws_db_instance.main.endpoint
  description = "RDS PostgreSQL endpoint"
}

output "rds_secret_arn" {
  value       = aws_secretsmanager_secret.rds_password.arn
  description = "Secrets Manager ARN for RDS credentials"
}
