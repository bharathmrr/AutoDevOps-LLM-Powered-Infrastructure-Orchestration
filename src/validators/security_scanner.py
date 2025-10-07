"""Security vulnerability scanning for IaC"""

import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
import re


class SecurityScanner:
    """Scan Infrastructure-as-Code for security vulnerabilities"""
    
    def __init__(self):
        """Initialize security scanner"""
        logger.info("Security scanner initialized")
        self.severity_levels = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    
    def scan(
        self,
        code: str,
        iac_type: str,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """Scan IaC for security issues
        
        Args:
            code: IaC code to scan
            iac_type: Type of IaC
            provider: Cloud provider
            
        Returns:
            Scan result dictionary
        """
        logger.info(f"Scanning {iac_type} for security issues")
        
        results = {
            "passed": True,
            "issues": [],
            "summary": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0
            }
        }
        
        # Run built-in security checks
        issues = self._run_builtin_checks(code, iac_type, provider)
        results["issues"].extend(issues)
        
        # Try to run external security tools
        if iac_type.lower() == "terraform":
            external_issues = self._scan_with_checkov(code)
            results["issues"].extend(external_issues)
        
        # Update summary
        for issue in results["issues"]:
            severity = issue.get("severity", "INFO").lower()
            if severity in results["summary"]:
                results["summary"][severity] += 1
        
        # Determine if passed
        results["passed"] = (
            results["summary"]["critical"] == 0 and
            results["summary"]["high"] == 0
        )
        
        return results
    
    def _run_builtin_checks(
        self,
        code: str,
        iac_type: str,
        provider: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Run built-in security checks"""
        issues = []
        
        # Common security checks
        issues.extend(self._check_hardcoded_secrets(code))
        issues.extend(self._check_public_access(code))
        issues.extend(self._check_encryption(code))
        
        # IaC-specific checks
        if iac_type.lower() == "terraform":
            issues.extend(self._check_terraform_security(code, provider))
        elif iac_type.lower() == "kubernetes":
            issues.extend(self._check_kubernetes_security(code))
        elif iac_type.lower() == "docker":
            issues.extend(self._check_docker_security(code))
        
        return issues
    
    def _check_hardcoded_secrets(self, code: str) -> List[Dict[str, Any]]:
        """Check for hardcoded secrets"""
        issues = []
        
        # Patterns for common secrets
        secret_patterns = [
            (r'password\s*=\s*["\'](?!var\.|data\.)([^"\']+)["\']', "Hardcoded password"),
            (r'api[_-]?key\s*=\s*["\'](?!var\.|data\.)([^"\']+)["\']', "Hardcoded API key"),
            (r'secret[_-]?key\s*=\s*["\'](?!var\.|data\.)([^"\']+)["\']', "Hardcoded secret key"),
            (r'access[_-]?key\s*=\s*["\'](?!var\.|data\.)([^"\']+)["\']', "Hardcoded access key"),
            (r'token\s*=\s*["\'](?!var\.|data\.)([^"\']+)["\']', "Hardcoded token"),
        ]
        
        for pattern, description in secret_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                issues.append({
                    "severity": "CRITICAL",
                    "title": description,
                    "description": f"Found {description.lower()} in code. Use variables or secret management instead.",
                    "line": code[:match.start()].count('\n') + 1,
                    "code_snippet": match.group(0)
                })
        
        return issues
    
    def _check_public_access(self, code: str) -> List[Dict[str, Any]]:
        """Check for overly permissive public access"""
        issues = []
        
        # Check for 0.0.0.0/0 CIDR blocks
        if re.search(r'0\.0\.0\.0/0', code):
            # Check if it's in ingress rules
            if re.search(r'ingress.*0\.0\.0\.0/0', code, re.DOTALL):
                issues.append({
                    "severity": "HIGH",
                    "title": "Overly permissive ingress rule",
                    "description": "Security group allows ingress from 0.0.0.0/0. Consider restricting access.",
                    "recommendation": "Limit ingress to specific IP ranges or security groups"
                })
        
        # Check for public S3 buckets
        if re.search(r'acl\s*=\s*["\']public', code, re.IGNORECASE):
            issues.append({
                "severity": "HIGH",
                "title": "Public S3 bucket",
                "description": "S3 bucket configured with public ACL",
                "recommendation": "Use private ACL and configure bucket policies carefully"
            })
        
        # Check for Kubernetes services exposed publicly
        if 'type: LoadBalancer' in code or 'type: NodePort' in code:
            issues.append({
                "severity": "MEDIUM",
                "title": "Service exposed externally",
                "description": "Service is exposed externally. Ensure this is intentional.",
                "recommendation": "Consider using Ingress with authentication"
            })
        
        return issues
    
    def _check_encryption(self, code: str) -> List[Dict[str, Any]]:
        """Check for encryption settings"""
        issues = []
        
        # Check for unencrypted storage
        if 'aws_s3_bucket' in code:
            if not re.search(r'server_side_encryption', code):
                issues.append({
                    "severity": "HIGH",
                    "title": "S3 bucket without encryption",
                    "description": "S3 bucket does not have server-side encryption configured",
                    "recommendation": "Enable server-side encryption (SSE-S3 or SSE-KMS)"
                })
        
        if 'aws_db_instance' in code or 'aws_rds' in code:
            if not re.search(r'storage_encrypted\s*=\s*true', code):
                issues.append({
                    "severity": "HIGH",
                    "title": "Unencrypted database",
                    "description": "RDS instance does not have encryption enabled",
                    "recommendation": "Enable storage_encrypted = true"
                })
        
        # Check for unencrypted EBS volumes
        if 'aws_ebs_volume' in code:
            if not re.search(r'encrypted\s*=\s*true', code):
                issues.append({
                    "severity": "MEDIUM",
                    "title": "Unencrypted EBS volume",
                    "description": "EBS volume is not encrypted",
                    "recommendation": "Enable encryption for EBS volumes"
                })
        
        return issues
    
    def _check_terraform_security(
        self,
        code: str,
        provider: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Terraform-specific security checks"""
        issues = []
        
        # Check for missing tags
        if provider == "aws":
            if 'aws_instance' in code and 'tags' not in code:
                issues.append({
                    "severity": "LOW",
                    "title": "Missing resource tags",
                    "description": "Resources should be tagged for better management",
                    "recommendation": "Add tags for tracking and cost allocation"
                })
        
        # Check for default VPC usage
        if 'default_vpc' in code.lower():
            issues.append({
                "severity": "MEDIUM",
                "title": "Using default VPC",
                "description": "Using default VPC is not recommended for production",
                "recommendation": "Create a custom VPC with proper network segmentation"
            })
        
        return issues
    
    def _check_kubernetes_security(self, code: str) -> List[Dict[str, Any]]:
        """Kubernetes-specific security checks"""
        issues = []
        
        # Check for privileged containers
        if 'privileged: true' in code:
            issues.append({
                "severity": "CRITICAL",
                "title": "Privileged container",
                "description": "Container is running in privileged mode",
                "recommendation": "Avoid privileged mode unless absolutely necessary"
            })
        
        # Check for root user
        if not re.search(r'runAsNonRoot:\s*true', code):
            issues.append({
                "severity": "HIGH",
                "title": "Container may run as root",
                "description": "Container does not explicitly run as non-root user",
                "recommendation": "Set securityContext.runAsNonRoot: true"
            })
        
        # Check for missing resource limits
        if 'containers:' in code and not re.search(r'resources:\s*\n\s*limits:', code):
            issues.append({
                "severity": "MEDIUM",
                "title": "Missing resource limits",
                "description": "Container does not have resource limits defined",
                "recommendation": "Define CPU and memory limits"
            })
        
        # Check for host network
        if 'hostNetwork: true' in code:
            issues.append({
                "severity": "HIGH",
                "title": "Host network enabled",
                "description": "Pod is using host network",
                "recommendation": "Avoid hostNetwork unless required"
            })
        
        return issues
    
    def _check_docker_security(self, code: str) -> List[Dict[str, Any]]:
        """Docker-specific security checks"""
        issues = []
        
        # Check for running as root
        if 'USER root' in code or not re.search(r'USER\s+\w+', code):
            issues.append({
                "severity": "HIGH",
                "title": "Container runs as root",
                "description": "Dockerfile does not specify a non-root user",
                "recommendation": "Add USER instruction to run as non-root"
            })
        
        # Check for latest tag
        if re.search(r'FROM\s+\w+:latest', code):
            issues.append({
                "severity": "MEDIUM",
                "title": "Using 'latest' tag",
                "description": "Base image uses 'latest' tag",
                "recommendation": "Use specific version tags for reproducibility"
            })
        
        # Check for COPY/ADD with broad patterns
        if re.search(r'(COPY|ADD)\s+\.\s+', code):
            issues.append({
                "severity": "LOW",
                "title": "Broad COPY/ADD pattern",
                "description": "Using '.' in COPY/ADD may include unnecessary files",
                "recommendation": "Use .dockerignore or be more specific with paths"
            })
        
        return issues
    
    def _scan_with_checkov(self, code: str) -> List[Dict[str, Any]]:
        """Scan Terraform with Checkov"""
        issues = []
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['checkov', '-f', temp_file, '--output', 'json'],
                capture_output=True,
                text=True
            )
            
            # Parse Checkov output
            # Note: This is a simplified version
            if result.returncode != 0 and 'failed' in result.stdout.lower():
                issues.append({
                    "severity": "HIGH",
                    "title": "Checkov security check failed",
                    "description": "External security scan found issues",
                    "tool": "checkov"
                })
            
            Path(temp_file).unlink(missing_ok=True)
        
        except FileNotFoundError:
            logger.debug("Checkov not found - skipping external scan")
        except Exception as e:
            logger.error(f"Error running Checkov: {e}")
        
        return issues
