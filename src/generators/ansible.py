"""Ansible playbook generator"""

from typing import Dict, Any, Optional, List
from loguru import logger
import yaml

from .base_generator import BaseGenerator


class AnsibleGenerator(BaseGenerator):
    """Generate Ansible playbooks"""
    
    def __init__(self, output_dir: str = "./infrastructure/ansible"):
        """Initialize Ansible generator"""
        super().__init__(output_dir)
    
    def get_file_extension(self) -> str:
        """Get Ansible file extension"""
        return ".yml"
    
    def generate(
        self,
        intent: Dict[str, Any],
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate Ansible playbook
        
        Args:
            intent: Parsed user intent
            parameters: Extracted parameters
            context: Additional context
            
        Returns:
            Generated Ansible YAML
        """
        action = intent.get("action", "create")
        resources = intent.get("resources", [])
        
        logger.info(f"Generating Ansible playbook - action: {action}")
        
        # Build playbook structure
        playbook = [{
            "name": "AutoDevOps Generated Playbook",
            "hosts": "all",
            "become": True,
            "vars": self._generate_variables(parameters),
            "tasks": self._generate_tasks(intent, parameters)
        }]
        
        return yaml.dump(playbook, default_flow_style=False, sort_keys=False)
    
    def _generate_variables(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate playbook variables"""
        general_params = parameters.get("general", {})
        
        variables = {
            "app_name": general_params.get("name", "app"),
            "environment": general_params.get("environment", "production"),
            "app_user": "appuser",
            "app_dir": "/opt/app"
        }
        
        return variables
    
    def _generate_tasks(
        self,
        intent: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate playbook tasks"""
        resources = intent.get("resources", [])
        tasks = []
        
        # System setup tasks
        tasks.extend(self._generate_system_tasks(parameters))
        
        # Application tasks
        if any(r in str(resources) for r in ["app", "application", "service"]):
            tasks.extend(self._generate_application_tasks(parameters))
        
        # Database tasks
        if any(r in str(resources) for r in ["database", "db", "postgres", "mysql"]):
            tasks.extend(self._generate_database_tasks(parameters))
        
        # Web server tasks
        if any(r in str(resources) for r in ["nginx", "apache", "web"]):
            tasks.extend(self._generate_webserver_tasks(parameters))
        
        return tasks
    
    def _generate_system_tasks(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate system setup tasks"""
        tasks = [
            {
                "name": "Update apt cache",
                "apt": {
                    "update_cache": True,
                    "cache_valid_time": 3600
                },
                "when": "ansible_os_family == 'Debian'"
            },
            {
                "name": "Install required packages",
                "apt": {
                    "name": [
                        "curl",
                        "git",
                        "build-essential",
                        "python3",
                        "python3-pip"
                    ],
                    "state": "present"
                },
                "when": "ansible_os_family == 'Debian'"
            },
            {
                "name": "Create application user",
                "user": {
                    "name": "{{ app_user }}",
                    "state": "present",
                    "shell": "/bin/bash",
                    "create_home": True
                }
            },
            {
                "name": "Create application directory",
                "file": {
                    "path": "{{ app_dir }}",
                    "state": "directory",
                    "owner": "{{ app_user }}",
                    "group": "{{ app_user }}",
                    "mode": "0755"
                }
            }
        ]
        
        return tasks
    
    def _generate_application_tasks(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate application deployment tasks"""
        tasks = [
            {
                "name": "Clone application repository",
                "git": {
                    "repo": "https://github.com/example/app.git",
                    "dest": "{{ app_dir }}/source",
                    "version": "main"
                },
                "become_user": "{{ app_user }}"
            },
            {
                "name": "Install application dependencies",
                "pip": {
                    "requirements": "{{ app_dir }}/source/requirements.txt",
                    "virtualenv": "{{ app_dir }}/venv",
                    "virtualenv_python": "python3"
                },
                "become_user": "{{ app_user }}"
            },
            {
                "name": "Copy application configuration",
                "template": {
                    "src": "app.conf.j2",
                    "dest": "{{ app_dir }}/config/app.conf",
                    "owner": "{{ app_user }}",
                    "group": "{{ app_user }}",
                    "mode": "0644"
                }
            },
            {
                "name": "Create systemd service",
                "template": {
                    "src": "app.service.j2",
                    "dest": "/etc/systemd/system/{{ app_name }}.service",
                    "mode": "0644"
                },
                "notify": "Restart application"
            },
            {
                "name": "Enable and start application service",
                "systemd": {
                    "name": "{{ app_name }}",
                    "enabled": True,
                    "state": "started",
                    "daemon_reload": True
                }
            }
        ]
        
        return tasks
    
    def _generate_database_tasks(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate database setup tasks"""
        tasks = [
            {
                "name": "Install PostgreSQL",
                "apt": {
                    "name": [
                        "postgresql",
                        "postgresql-contrib",
                        "python3-psycopg2"
                    ],
                    "state": "present"
                }
            },
            {
                "name": "Ensure PostgreSQL is running",
                "systemd": {
                    "name": "postgresql",
                    "state": "started",
                    "enabled": True
                }
            },
            {
                "name": "Create database",
                "postgresql_db": {
                    "name": "{{ app_name }}_db",
                    "state": "present"
                },
                "become_user": "postgres"
            },
            {
                "name": "Create database user",
                "postgresql_user": {
                    "name": "{{ app_name }}_user",
                    "password": "{{ db_password }}",
                    "db": "{{ app_name }}_db",
                    "priv": "ALL",
                    "state": "present"
                },
                "become_user": "postgres"
            },
            {
                "name": "Configure PostgreSQL authentication",
                "lineinfile": {
                    "path": "/etc/postgresql/*/main/pg_hba.conf",
                    "line": "host    {{ app_name }}_db    {{ app_name }}_user    127.0.0.1/32    md5",
                    "state": "present"
                },
                "notify": "Restart PostgreSQL"
            }
        ]
        
        return tasks
    
    def _generate_webserver_tasks(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate web server setup tasks"""
        network_params = parameters.get("network", {})
        security_params = parameters.get("security", {})
        
        tasks = [
            {
                "name": "Install Nginx",
                "apt": {
                    "name": "nginx",
                    "state": "present"
                }
            },
            {
                "name": "Remove default Nginx site",
                "file": {
                    "path": "/etc/nginx/sites-enabled/default",
                    "state": "absent"
                }
            },
            {
                "name": "Copy Nginx configuration",
                "template": {
                    "src": "nginx.conf.j2",
                    "dest": "/etc/nginx/sites-available/{{ app_name }}",
                    "mode": "0644"
                },
                "notify": "Reload Nginx"
            },
            {
                "name": "Enable Nginx site",
                "file": {
                    "src": "/etc/nginx/sites-available/{{ app_name }}",
                    "dest": "/etc/nginx/sites-enabled/{{ app_name }}",
                    "state": "link"
                }
            },
            {
                "name": "Ensure Nginx is running",
                "systemd": {
                    "name": "nginx",
                    "state": "started",
                    "enabled": True
                }
            }
        ]
        
        # Add SSL tasks if enabled
        if security_params.get("ssl_enabled"):
            tasks.extend([
                {
                    "name": "Install Certbot",
                    "apt": {
                        "name": [
                            "certbot",
                            "python3-certbot-nginx"
                        ],
                        "state": "present"
                    }
                },
                {
                    "name": "Obtain SSL certificate",
                    "command": "certbot --nginx -d {{ app_name }}.example.com --non-interactive --agree-tos -m admin@example.com",
                    "args": {
                        "creates": "/etc/letsencrypt/live/{{ app_name }}.example.com/fullchain.pem"
                    }
                }
            ])
        
        return tasks
