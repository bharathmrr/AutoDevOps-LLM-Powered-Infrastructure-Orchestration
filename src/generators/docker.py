"""Docker configuration generator"""

from typing import Dict, Any, Optional, List
from loguru import logger
import yaml

from .base_generator import BaseGenerator


class DockerGenerator(BaseGenerator):
    """Generate Dockerfiles and docker-compose files"""
    
    def __init__(self, output_dir: str = "./infrastructure/docker"):
        """Initialize Docker generator"""
        super().__init__(output_dir)
    
    def get_file_extension(self) -> str:
        """Get Docker file extension"""
        return ""  # Dockerfile has no extension
    
    def generate(
        self,
        intent: Dict[str, Any],
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate Docker configuration
        
        Args:
            intent: Parsed user intent
            parameters: Extracted parameters
            context: Additional context
            
        Returns:
            Generated Dockerfile or docker-compose.yml
        """
        resources = intent.get("resources", [])
        
        # Determine if we need docker-compose or just Dockerfile
        if any(r in str(resources) for r in ["compose", "multi", "stack"]):
            return self._generate_docker_compose(parameters)
        else:
            return self._generate_dockerfile(parameters)
    
    def _generate_dockerfile(self, parameters: Dict[str, Any]) -> str:
        """Generate Dockerfile"""
        compute_params = parameters.get("compute", {})
        general_params = parameters.get("general", {})
        network_params = parameters.get("network", {})
        
        # Determine base image
        os_type = compute_params.get("os", "ubuntu")
        base_image = self._get_base_image(os_type)
        
        # Get port
        ports = network_params.get("ports", [80])
        
        dockerfile = f'''# Multi-stage build for optimized image size
FROM {base_image} AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    curl \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt package.json ./

# Install application dependencies
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi
RUN if [ -f package.json ]; then npm install --production; fi

# Copy application source
COPY . .

# Build application (if needed)
# RUN npm run build

# Production stage
FROM {base_image}

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy from builder
COPY --from=builder --chown=appuser:appuser /app /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \\
    ca-certificates \\
    && rm -rf /var/lib/apt/lists/*

# Switch to non-root user
USER appuser

# Expose port
EXPOSE {ports[0]}

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \\
    CMD curl -f http://localhost:{ports[0]}/health || exit 1

# Set environment variables
ENV PORT={ports[0]} \\
    NODE_ENV=production \\
    PYTHONUNBUFFERED=1

# Start application
CMD ["python", "app.py"]
# Or for Node.js: CMD ["node", "server.js"]
'''
        
        return dockerfile
    
    def _generate_docker_compose(self, parameters: Dict[str, Any]) -> str:
        """Generate docker-compose.yml"""
        general_params = parameters.get("general", {})
        network_params = parameters.get("network", {})
        storage_params = parameters.get("storage", {})
        scaling_params = parameters.get("scaling", {})
        
        app_name = general_params.get("name", "app")
        ports = network_params.get("ports", [80])
        replicas = scaling_params.get("count", 1)
        
        compose = {
            "version": "3.8",
            "services": {
                app_name: {
                    "build": {
                        "context": ".",
                        "dockerfile": "Dockerfile"
                    },
                    "image": f"{app_name}:latest",
                    "container_name": app_name,
                    "restart": "unless-stopped",
                    "ports": [f"{port}:{port}" for port in ports],
                    "environment": {
                        "NODE_ENV": "production",
                        "DATABASE_URL": "postgresql://user:password@postgres:5432/db"
                    },
                    "volumes": [
                        "./data:/app/data"
                    ],
                    "networks": [
                        "app-network"
                    ],
                    "depends_on": [
                        "postgres",
                        "redis"
                    ],
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", f"http://localhost:{ports[0]}/health"],
                        "interval": "30s",
                        "timeout": "3s",
                        "retries": 3,
                        "start_period": "40s"
                    }
                },
                "postgres": {
                    "image": "postgres:15-alpine",
                    "container_name": f"{app_name}-postgres",
                    "restart": "unless-stopped",
                    "environment": {
                        "POSTGRES_USER": "user",
                        "POSTGRES_PASSWORD": "password",
                        "POSTGRES_DB": "db"
                    },
                    "volumes": [
                        "postgres-data:/var/lib/postgresql/data"
                    ],
                    "networks": [
                        "app-network"
                    ],
                    "healthcheck": {
                        "test": ["CMD-SHELL", "pg_isready -U user"],
                        "interval": "10s",
                        "timeout": "5s",
                        "retries": 5
                    }
                },
                "redis": {
                    "image": "redis:7-alpine",
                    "container_name": f"{app_name}-redis",
                    "restart": "unless-stopped",
                    "volumes": [
                        "redis-data:/data"
                    ],
                    "networks": [
                        "app-network"
                    ],
                    "healthcheck": {
                        "test": ["CMD", "redis-cli", "ping"],
                        "interval": "10s",
                        "timeout": "3s",
                        "retries": 3
                    }
                }
            },
            "networks": {
                "app-network": {
                    "driver": "bridge"
                }
            },
            "volumes": {
                "postgres-data": None,
                "redis-data": None
            }
        }
        
        # Add nginx if load balancer is needed
        if network_params.get("load_balancer"):
            compose["services"]["nginx"] = {
                "image": "nginx:alpine",
                "container_name": f"{app_name}-nginx",
                "restart": "unless-stopped",
                "ports": ["80:80", "443:443"],
                "volumes": [
                    "./nginx.conf:/etc/nginx/nginx.conf:ro"
                ],
                "networks": ["app-network"],
                "depends_on": [app_name]
            }
        
        # Add replicas if scaling is needed
        if replicas > 1:
            compose["services"][app_name]["deploy"] = {
                "replicas": replicas,
                "resources": {
                    "limits": {
                        "cpus": "1",
                        "memory": "512M"
                    },
                    "reservations": {
                        "cpus": "0.5",
                        "memory": "256M"
                    }
                }
            }
        
        return yaml.dump(compose, default_flow_style=False, sort_keys=False)
    
    def _get_base_image(self, os_type: str) -> str:
        """Get appropriate base image"""
        base_images = {
            "ubuntu": "ubuntu:22.04",
            "debian": "debian:bullseye-slim",
            "alpine": "alpine:3.18",
            "python": "python:3.11-slim",
            "node": "node:18-alpine",
        }
        
        return base_images.get(os_type, "ubuntu:22.04")
    
    def generate_dockerignore(self) -> str:
        """Generate .dockerignore file"""
        dockerignore = '''# Git
.git
.gitignore
.gitattributes

# CI/CD
.github
.gitlab-ci.yml
.travis.yml

# Documentation
README.md
CHANGELOG.md
docs/

# Dependencies
node_modules/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
venv/
env/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Testing
.coverage
htmlcov/
.pytest_cache/
.tox/
test/
tests/

# Build artifacts
dist/
build/
*.egg-info/

# Logs
*.log
logs/

# Environment
.env
.env.local
.env.*.local
'''
        return dockerignore
