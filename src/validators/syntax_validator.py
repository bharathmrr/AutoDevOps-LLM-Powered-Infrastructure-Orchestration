"""Validate IaC syntax"""

import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
import yaml
import json


class SyntaxValidator:
    """Validate syntax of Infrastructure-as-Code"""
    
    def __init__(self):
        """Initialize syntax validator"""
        logger.info("Syntax validator initialized")
    
    def validate(
        self,
        code: str,
        iac_type: str,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate IaC syntax
        
        Args:
            code: IaC code to validate
            iac_type: Type of IaC (terraform, kubernetes, ansible, docker)
            provider: Cloud provider (optional)
            
        Returns:
            Validation result dictionary
        """
        logger.info(f"Validating {iac_type} syntax")
        
        if iac_type.lower() == "terraform":
            return self._validate_terraform(code)
        elif iac_type.lower() == "kubernetes":
            return self._validate_kubernetes(code)
        elif iac_type.lower() == "ansible":
            return self._validate_ansible(code)
        elif iac_type.lower() == "docker":
            return self._validate_docker(code)
        else:
            return {
                "valid": False,
                "errors": [f"Unsupported IaC type: {iac_type}"],
                "warnings": []
            }
    
    def _validate_terraform(self, code: str) -> Dict[str, Any]:
        """Validate Terraform syntax"""
        errors = []
        warnings = []
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            temp_path = Path(temp_file)
            temp_dir = temp_path.parent
            
            try:
                # Run terraform fmt to check formatting
                result = subprocess.run(
                    ['terraform', 'fmt', '-check', temp_file],
                    capture_output=True,
                    text=True,
                    cwd=temp_dir
                )
                
                if result.returncode != 0:
                    warnings.append("Code formatting issues detected")
                
                # Run terraform validate (requires init first)
                # Note: This is a basic check, full validation requires init
                result = subprocess.run(
                    ['terraform', 'validate', '-json'],
                    capture_output=True,
                    text=True,
                    cwd=temp_dir
                )
                
                if result.returncode != 0:
                    try:
                        validation_result = json.loads(result.stdout)
                        if 'diagnostics' in validation_result:
                            for diag in validation_result['diagnostics']:
                                if diag.get('severity') == 'error':
                                    errors.append(diag.get('summary', 'Unknown error'))
                                else:
                                    warnings.append(diag.get('summary', 'Unknown warning'))
                    except:
                        errors.append("Terraform validation failed")
            
            except FileNotFoundError:
                warnings.append("Terraform CLI not found - skipping validation")
            
            finally:
                # Cleanup
                temp_path.unlink(missing_ok=True)
        
        except Exception as e:
            logger.error(f"Error validating Terraform: {e}")
            errors.append(f"Validation error: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_kubernetes(self, code: str) -> Dict[str, Any]:
        """Validate Kubernetes YAML syntax"""
        errors = []
        warnings = []
        
        try:
            # Parse YAML
            documents = list(yaml.safe_load_all(code))
            
            for i, doc in enumerate(documents):
                if not doc:
                    continue
                
                # Check required fields
                if 'apiVersion' not in doc:
                    errors.append(f"Document {i+1}: Missing 'apiVersion' field")
                
                if 'kind' not in doc:
                    errors.append(f"Document {i+1}: Missing 'kind' field")
                
                if 'metadata' not in doc:
                    errors.append(f"Document {i+1}: Missing 'metadata' field")
                elif 'name' not in doc.get('metadata', {}):
                    errors.append(f"Document {i+1}: Missing 'metadata.name' field")
                
                # Validate specific resource types
                kind = doc.get('kind', '')
                
                if kind == 'Deployment':
                    self._validate_deployment(doc, i+1, errors, warnings)
                elif kind == 'Service':
                    self._validate_service(doc, i+1, errors, warnings)
            
            # Try kubectl validation if available
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write(code)
                    temp_file = f.name
                
                result = subprocess.run(
                    ['kubectl', 'apply', '--dry-run=client', '-f', temp_file],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    errors.append(f"kubectl validation failed: {result.stderr}")
                
                Path(temp_file).unlink(missing_ok=True)
            
            except FileNotFoundError:
                warnings.append("kubectl not found - skipping advanced validation")
        
        except yaml.YAMLError as e:
            errors.append(f"YAML parsing error: {str(e)}")
        except Exception as e:
            logger.error(f"Error validating Kubernetes: {e}")
            errors.append(f"Validation error: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_deployment(
        self,
        doc: Dict[str, Any],
        doc_num: int,
        errors: List[str],
        warnings: List[str]
    ):
        """Validate Kubernetes Deployment"""
        spec = doc.get('spec', {})
        
        if 'selector' not in spec:
            errors.append(f"Document {doc_num}: Deployment missing 'spec.selector'")
        
        if 'template' not in spec:
            errors.append(f"Document {doc_num}: Deployment missing 'spec.template'")
        else:
            template = spec['template']
            if 'spec' not in template:
                errors.append(f"Document {doc_num}: Deployment template missing 'spec'")
            else:
                containers = template['spec'].get('containers', [])
                if not containers:
                    errors.append(f"Document {doc_num}: No containers defined")
                
                for container in containers:
                    if 'name' not in container:
                        errors.append(f"Document {doc_num}: Container missing 'name'")
                    if 'image' not in container:
                        errors.append(f"Document {doc_num}: Container missing 'image'")
                    
                    # Check for resource limits
                    if 'resources' not in container:
                        warnings.append(f"Document {doc_num}: Container '{container.get('name', 'unknown')}' has no resource limits")
    
    def _validate_service(
        self,
        doc: Dict[str, Any],
        doc_num: int,
        errors: List[str],
        warnings: List[str]
    ):
        """Validate Kubernetes Service"""
        spec = doc.get('spec', {})
        
        if 'selector' not in spec:
            errors.append(f"Document {doc_num}: Service missing 'spec.selector'")
        
        if 'ports' not in spec:
            errors.append(f"Document {doc_num}: Service missing 'spec.ports'")
    
    def _validate_ansible(self, code: str) -> Dict[str, Any]:
        """Validate Ansible YAML syntax"""
        errors = []
        warnings = []
        
        try:
            # Parse YAML
            playbooks = yaml.safe_load(code)
            
            if not isinstance(playbooks, list):
                errors.append("Ansible playbook must be a list")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            for i, playbook in enumerate(playbooks):
                if not isinstance(playbook, dict):
                    errors.append(f"Playbook {i+1}: Must be a dictionary")
                    continue
                
                # Check required fields
                if 'hosts' not in playbook:
                    errors.append(f"Playbook {i+1}: Missing 'hosts' field")
                
                if 'tasks' not in playbook and 'roles' not in playbook:
                    warnings.append(f"Playbook {i+1}: No 'tasks' or 'roles' defined")
                
                # Validate tasks
                tasks = playbook.get('tasks', [])
                for j, task in enumerate(tasks):
                    if not isinstance(task, dict):
                        errors.append(f"Playbook {i+1}, Task {j+1}: Must be a dictionary")
                        continue
                    
                    if 'name' not in task:
                        warnings.append(f"Playbook {i+1}, Task {j+1}: Missing 'name' field")
            
            # Try ansible-playbook syntax check if available
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                    f.write(code)
                    temp_file = f.name
                
                result = subprocess.run(
                    ['ansible-playbook', '--syntax-check', temp_file],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    errors.append(f"Ansible syntax check failed: {result.stderr}")
                
                Path(temp_file).unlink(missing_ok=True)
            
            except FileNotFoundError:
                warnings.append("ansible-playbook not found - skipping advanced validation")
        
        except yaml.YAMLError as e:
            errors.append(f"YAML parsing error: {str(e)}")
        except Exception as e:
            logger.error(f"Error validating Ansible: {e}")
            errors.append(f"Validation error: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_docker(self, code: str) -> Dict[str, Any]:
        """Validate Dockerfile or docker-compose syntax"""
        errors = []
        warnings = []
        
        try:
            # Check if it's docker-compose
            if code.strip().startswith('version:') or 'services:' in code:
                return self._validate_docker_compose(code)
            
            # Validate Dockerfile
            lines = code.split('\n')
            valid_instructions = {
                'FROM', 'RUN', 'CMD', 'LABEL', 'EXPOSE', 'ENV', 'ADD', 'COPY',
                'ENTRYPOINT', 'VOLUME', 'USER', 'WORKDIR', 'ARG', 'ONBUILD',
                'STOPSIGNAL', 'HEALTHCHECK', 'SHELL'
            }
            
            has_from = False
            
            for i, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Get instruction
                instruction = line.split()[0].upper()
                
                if instruction not in valid_instructions:
                    errors.append(f"Line {i}: Invalid instruction '{instruction}'")
                
                if instruction == 'FROM':
                    has_from = True
            
            if not has_from:
                errors.append("Dockerfile must have at least one FROM instruction")
            
            # Check for common issues
            if 'apt-get update' in code and 'apt-get install' in code:
                if '&&' not in code:
                    warnings.append("Consider combining apt-get update and install in single RUN")
            
            if 'COPY . .' in code or 'ADD . .' in code:
                warnings.append("Consider using .dockerignore to exclude unnecessary files")
        
        except Exception as e:
            logger.error(f"Error validating Docker: {e}")
            errors.append(f"Validation error: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_docker_compose(self, code: str) -> Dict[str, Any]:
        """Validate docker-compose.yml syntax"""
        errors = []
        warnings = []
        
        try:
            compose = yaml.safe_load(code)
            
            if not isinstance(compose, dict):
                errors.append("docker-compose file must be a dictionary")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Check version
            if 'version' not in compose:
                warnings.append("Missing 'version' field")
            
            # Check services
            if 'services' not in compose:
                errors.append("Missing 'services' section")
            else:
                services = compose['services']
                for service_name, service in services.items():
                    if not isinstance(service, dict):
                        errors.append(f"Service '{service_name}' must be a dictionary")
                        continue
                    
                    # Check for image or build
                    if 'image' not in service and 'build' not in service:
                        errors.append(f"Service '{service_name}' must have 'image' or 'build'")
        
        except yaml.YAMLError as e:
            errors.append(f"YAML parsing error: {str(e)}")
        except Exception as e:
            logger.error(f"Error validating docker-compose: {e}")
            errors.append(f"Validation error: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
