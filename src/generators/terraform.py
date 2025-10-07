"""Terraform code generator"""

from typing import Dict, Any, Optional, List
from loguru import logger

from .base_generator import BaseGenerator


class TerraformGenerator(BaseGenerator):
    """Generate Terraform configurations"""
    
    def __init__(self, output_dir: str = "./infrastructure/terraform"):
        """Initialize Terraform generator"""
        super().__init__(output_dir)
    
    def get_file_extension(self) -> str:
        """Get Terraform file extension"""
        return ".tf"
    
    def generate(
        self,
        intent: Dict[str, Any],
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate Terraform configuration
        
        Args:
            intent: Parsed user intent
            parameters: Extracted parameters
            context: Additional context
            
        Returns:
            Generated Terraform code
        """
        provider = intent.get("provider", "aws").lower()
        action = intent.get("action", "create")
        
        logger.info(f"Generating Terraform for {provider} - action: {action}")
        
        # Generate provider configuration
        provider_config = self._generate_provider_config(provider)
        
        # Generate resources based on intent
        resources = self._generate_resources(intent, parameters, provider)
        
        # Generate variables
        variables = self._generate_variables(parameters)
        
        # Generate outputs
        outputs = self._generate_outputs(intent, parameters)
        
        # Combine all sections
        code_sections = [
            provider_config,
            variables,
            resources,
            outputs,
        ]
        
        code = "\n\n".join(section for section in code_sections if section)
        
        return self.format_code(code)
    
    def _generate_provider_config(self, provider: str) -> str:
        """Generate provider configuration"""
        if provider == "aws":
            return '''terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      ManagedBy   = "AutoDevOps"
      Environment = var.environment
    }
  }
}'''
        
        elif provider == "azure":
            return '''terraform {
  required_version = ">= 1.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}'''
        
        elif provider == "gcp":
            return '''terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}'''
        
        return ""
    
    def _generate_resources(
        self,
        intent: Dict[str, Any],
        parameters: Dict[str, Any],
        provider: str
    ) -> str:
        """Generate resource blocks"""
        resources = intent.get("resources", [])
        
        if not resources:
            # Try to infer from parameters
            if "compute" in parameters:
                resources.append("instance")
            if "storage" in parameters:
                resources.append("storage")
        
        resource_blocks = []
        
        for resource in resources:
            if "instance" in resource or "ec2" in resource or "vm" in resource:
                resource_blocks.append(self._generate_compute_resource(parameters, provider))
            
            if "storage" in resource or "s3" in resource or "bucket" in resource:
                resource_blocks.append(self._generate_storage_resource(parameters, provider))
            
            if "database" in resource or "rds" in resource or "db" in resource:
                resource_blocks.append(self._generate_database_resource(parameters, provider))
            
            if "load balancer" in resource or "lb" in resource:
                resource_blocks.append(self._generate_load_balancer_resource(parameters, provider))
        
        return "\n\n".join(block for block in resource_blocks if block)
    
    def _generate_compute_resource(self, parameters: Dict[str, Any], provider: str) -> str:
        """Generate compute resource"""
        compute_params = parameters.get("compute", {})
        scaling_params = parameters.get("scaling", {})
        
        if provider == "aws":
            instance_type = compute_params.get("instance_type", "t3.micro")
            
            if scaling_params.get("auto_scaling") or scaling_params.get("count", 1) > 1:
                # Generate Auto Scaling Group
                return f'''# Launch Template
resource "aws_launch_template" "main" {{
  name_prefix   = "${{var.name_prefix}}-"
  image_id      = data.aws_ami.ubuntu.id
  instance_type = "{instance_type}"
  
  vpc_security_group_ids = [aws_security_group.main.id]
  
  user_data = base64encode(templatefile("${{path.module}}/user_data.sh", {{}}))
  
  tag_specifications {{
    resource_type = "instance"
    tags = {{
      Name = "${{var.name_prefix}}-instance"
    }}
  }}
}}

# Auto Scaling Group
resource "aws_autoscaling_group" "main" {{
  name                = "${{var.name_prefix}}-asg"
  vpc_zone_identifier = var.subnet_ids
  target_group_arns   = [aws_lb_target_group.main.arn]
  health_check_type   = "ELB"
  
  min_size         = {scaling_params.get("min_size", 1)}
  max_size         = {scaling_params.get("max_size", 3)}
  desired_capacity = {scaling_params.get("count", 2)}
  
  launch_template {{
    id      = aws_launch_template.main.id
    version = "$Latest"
  }}
  
  tag {{
    key                 = "Name"
    value               = "${{var.name_prefix}}-instance"
    propagate_at_launch = true
  }}
}}'''
            else:
                # Generate single EC2 instance
                return f'''# EC2 Instance
resource "aws_instance" "main" {{
  ami           = data.aws_ami.ubuntu.id
  instance_type = "{instance_type}"
  
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.main.id]
  
  tags = {{
    Name = "${{var.name_prefix}}-instance"
  }}
}}

# Security Group
resource "aws_security_group" "main" {{
  name        = "${{var.name_prefix}}-sg"
  description = "Security group for ${{var.name_prefix}}"
  vpc_id      = var.vpc_id
  
  ingress {{
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }}
  
  ingress {{
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }}
  
  egress {{
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }}
  
  tags = {{
    Name = "${{var.name_prefix}}-sg"
  }}
}}

# Data source for Ubuntu AMI
data "aws_ami" "ubuntu" {{
  most_recent = true
  owners      = ["099720109477"] # Canonical
  
  filter {{
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }}
}}'''
        
        return ""
    
    def _generate_storage_resource(self, parameters: Dict[str, Any], provider: str) -> str:
        """Generate storage resource"""
        storage_params = parameters.get("storage", {})
        
        if provider == "aws":
            versioning = storage_params.get("versioning_enabled", False)
            encryption = storage_params.get("encryption_enabled", True)
            
            return f'''# S3 Bucket
resource "aws_s3_bucket" "main" {{
  bucket = "${{var.name_prefix}}-bucket"
  
  tags = {{
    Name = "${{var.name_prefix}}-bucket"
  }}
}}

resource "aws_s3_bucket_versioning" "main" {{
  bucket = aws_s3_bucket.main.id
  
  versioning_configuration {{
    status = "{"Enabled" if versioning else "Disabled"}"
  }}
}}

{"resource \"aws_s3_bucket_server_side_encryption_configuration\" \"main\" {" if encryption else ""}
{"  bucket = aws_s3_bucket.main.id" if encryption else ""}
{"  " if encryption else ""}
{"  rule {" if encryption else ""}
{"    apply_server_side_encryption_by_default {" if encryption else ""}
{"      sse_algorithm = \"AES256\"" if encryption else ""}
{"    }" if encryption else ""}
{"  }" if encryption else ""}
{"}" if encryption else ""}

resource "aws_s3_bucket_public_access_block" "main" {{
  bucket = aws_s3_bucket.main.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}}'''
        
        return ""
    
    def _generate_database_resource(self, parameters: Dict[str, Any], provider: str) -> str:
        """Generate database resource"""
        if provider == "aws":
            scaling_params = parameters.get("scaling", {})
            multi_az = scaling_params.get("multi_az", False)
            
            return f'''# RDS Database
resource "aws_db_instance" "main" {{
  identifier     = "${{var.name_prefix}}-db"
  engine         = "postgres"
  engine_version = "15.3"
  instance_class = "db.t3.micro"
  
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_encrypted     = true
  
  db_name  = var.database_name
  username = var.database_username
  password = var.database_password
  
  multi_az               = {str(multi_az).lower()}
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"
  
  skip_final_snapshot = false
  final_snapshot_identifier = "${{var.name_prefix}}-db-final-snapshot"
  
  tags = {{
    Name = "${{var.name_prefix}}-db"
  }}
}}

resource "aws_db_subnet_group" "main" {{
  name       = "${{var.name_prefix}}-db-subnet-group"
  subnet_ids = var.database_subnet_ids
  
  tags = {{
    Name = "${{var.name_prefix}}-db-subnet-group"
  }}
}}

resource "aws_security_group" "db" {{
  name        = "${{var.name_prefix}}-db-sg"
  description = "Security group for database"
  vpc_id      = var.vpc_id
  
  ingress {{
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.main.id]
  }}
  
  tags = {{
    Name = "${{var.name_prefix}}-db-sg"
  }}
}}'''
        
        return ""
    
    def _generate_load_balancer_resource(self, parameters: Dict[str, Any], provider: str) -> str:
        """Generate load balancer resource"""
        if provider == "aws":
            return '''# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
  
  enable_deletion_protection = false
  
  tags = {
    Name = "${var.name_prefix}-alb"
  }
}

resource "aws_lb_target_group" "main" {
  name     = "${var.name_prefix}-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }
  
  tags = {
    Name = "${var.name_prefix}-tg"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }
}

resource "aws_security_group" "alb" {
  name        = "${var.name_prefix}-alb-sg"
  description = "Security group for ALB"
  vpc_id      = var.vpc_id
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${var.name_prefix}-alb-sg"
  }
}'''
        
        return ""
    
    def _generate_variables(self, parameters: Dict[str, Any]) -> str:
        """Generate variable definitions"""
        general_params = parameters.get("general", {})
        
        variables = [
            ('name_prefix', 'string', 'Prefix for resource names', '"autodevops"'),
            ('environment', 'string', 'Environment name', f'"{general_params.get("environment", "production")}"'),
            ('aws_region', 'string', 'AWS region', f'"{general_params.get("region", "us-east-1")}"'),
        ]
        
        var_blocks = []
        for name, var_type, description, default in variables:
            var_blocks.append(f'''variable "{name}" {{
  description = "{description}"
  type        = {var_type}
  default     = {default}
}}''')
        
        return "\n\n".join(var_blocks)
    
    def _generate_outputs(self, intent: Dict[str, Any], parameters: Dict[str, Any]) -> str:
        """Generate output definitions"""
        resources = intent.get("resources", [])
        
        outputs = []
        
        if any("instance" in r or "ec2" in r for r in resources):
            outputs.append('''output "instance_id" {
  description = "ID of the EC2 instance"
  value       = try(aws_instance.main.id, null)
}''')
        
        if any("storage" in r or "s3" in r for r in resources):
            outputs.append('''output "bucket_name" {
  description = "Name of the S3 bucket"
  value       = try(aws_s3_bucket.main.id, null)
}''')
        
        if any("database" in r or "rds" in r for r in resources):
            outputs.append('''output "database_endpoint" {
  description = "Database connection endpoint"
  value       = try(aws_db_instance.main.endpoint, null)
}''')
        
        if any("load balancer" in r or "lb" in r for r in resources):
            outputs.append('''output "load_balancer_dns" {
  description = "DNS name of the load balancer"
  value       = try(aws_lb.main.dns_name, null)
}''')
        
        return "\n\n".join(outputs) if outputs else ""
