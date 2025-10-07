"""Check compliance with organizational policies"""

from typing import List, Dict, Any, Optional
from loguru import logger
import re


class ComplianceChecker:
    """Check Infrastructure-as-Code compliance with policies"""
    
    def __init__(self, policy_file: Optional[str] = None):
        """Initialize compliance checker
        
        Args:
            policy_file: Path to policy configuration file
        """
        self.policy_file = policy_file
        self.policies = self._load_default_policies()
        logger.info("Compliance checker initialized")
    
    def _load_default_policies(self) -> Dict[str, Any]:
        """Load default compliance policies"""
        return {
            "tagging": {
                "enabled": True,
                "required_tags": ["Environment", "Owner", "Project", "CostCenter"],
                "severity": "MEDIUM"
            },
            "encryption": {
                "enabled": True,
                "require_encryption_at_rest": True,
                "require_encryption_in_transit": True,
                "severity": "HIGH"
            },
            "backup": {
                "enabled": True,
                "require_backup_enabled": True,
                "minimum_retention_days": 7,
                "severity": "MEDIUM"
            },
            "networking": {
                "enabled": True,
                "prohibit_default_vpc": True,
                "require_private_subnets": True,
                "severity": "HIGH"
            },
            "access_control": {
                "enabled": True,
                "prohibit_public_access": False,
                "require_mfa": True,
                "severity": "HIGH"
            },
            "logging": {
                "enabled": True,
                "require_audit_logging": True,
                "require_access_logging": True,
                "severity": "MEDIUM"
            }
        }
    
    def check(
        self,
        code: str,
        iac_type: str,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check compliance with policies
        
        Args:
            code: IaC code to check
            iac_type: Type of IaC
            provider: Cloud provider
            
        Returns:
            Compliance check result
        """
        logger.info(f"Checking {iac_type} compliance")
        
        results = {
            "compliant": True,
            "violations": [],
            "summary": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }
        }
        
        # Run policy checks
        if self.policies["tagging"]["enabled"]:
            violations = self._check_tagging_policy(code, iac_type, provider)
            results["violations"].extend(violations)
        
        if self.policies["encryption"]["enabled"]:
            violations = self._check_encryption_policy(code, iac_type, provider)
            results["violations"].extend(violations)
        
        if self.policies["backup"]["enabled"]:
            violations = self._check_backup_policy(code, iac_type, provider)
            results["violations"].extend(violations)
        
        if self.policies["networking"]["enabled"]:
            violations = self._check_networking_policy(code, iac_type, provider)
            results["violations"].extend(violations)
        
        if self.policies["logging"]["enabled"]:
            violations = self._check_logging_policy(code, iac_type, provider)
            results["violations"].extend(violations)
        
        # Update summary
        for violation in results["violations"]:
            severity = violation.get("severity", "LOW").lower()
            if severity in results["summary"]:
                results["summary"][severity] += 1
        
        # Determine compliance
        results["compliant"] = (
            results["summary"]["critical"] == 0 and
            results["summary"]["high"] == 0
        )
        
        return results
    
    def _check_tagging_policy(
        self,
        code: str,
        iac_type: str,
        provider: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Check tagging policy compliance"""
        violations = []
        required_tags = self.policies["tagging"]["required_tags"]
        
        if iac_type.lower() == "terraform" and provider == "aws":
            # Check for resources without tags
            resource_pattern = r'resource\s+"aws_\w+"\s+"(\w+)"\s*\{'
            resources = re.finditer(resource_pattern, code)
            
            for match in resources:
                resource_name = match.group(1)
                resource_block = self._extract_resource_block(code, match.start())
                
                if 'tags' not in resource_block:
                    violations.append({
                        "policy": "tagging",
                        "severity": self.policies["tagging"]["severity"],
                        "resource": resource_name,
                        "description": f"Resource '{resource_name}' is missing tags",
                        "recommendation": f"Add tags: {', '.join(required_tags)}"
                    })
                else:
                    # Check for required tags
                    missing_tags = []
                    for tag in required_tags:
                        if tag not in resource_block:
                            missing_tags.append(tag)
                    
                    if missing_tags:
                        violations.append({
                            "policy": "tagging",
                            "severity": "LOW",
                            "resource": resource_name,
                            "description": f"Resource '{resource_name}' is missing required tags: {', '.join(missing_tags)}",
                            "recommendation": f"Add missing tags: {', '.join(missing_tags)}"
                        })
        
        elif iac_type.lower() == "kubernetes":
            # Check for missing labels
            if 'labels:' not in code:
                violations.append({
                    "policy": "tagging",
                    "severity": "LOW",
                    "description": "Kubernetes resources should have labels",
                    "recommendation": "Add labels for better resource management"
                })
        
        return violations
    
    def _check_encryption_policy(
        self,
        code: str,
        iac_type: str,
        provider: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Check encryption policy compliance"""
        violations = []
        
        if iac_type.lower() == "terraform":
            # Check S3 bucket encryption
            if 'aws_s3_bucket' in code:
                if not re.search(r'server_side_encryption_configuration', code):
                    violations.append({
                        "policy": "encryption",
                        "severity": self.policies["encryption"]["severity"],
                        "description": "S3 bucket must have server-side encryption enabled",
                        "recommendation": "Add server_side_encryption_configuration block"
                    })
            
            # Check RDS encryption
            if 'aws_db_instance' in code:
                if not re.search(r'storage_encrypted\s*=\s*true', code):
                    violations.append({
                        "policy": "encryption",
                        "severity": self.policies["encryption"]["severity"],
                        "description": "RDS instance must have storage encryption enabled",
                        "recommendation": "Set storage_encrypted = true"
                    })
            
            # Check EBS encryption
            if 'aws_ebs_volume' in code or 'aws_instance' in code:
                if not re.search(r'encrypted\s*=\s*true', code):
                    violations.append({
                        "policy": "encryption",
                        "severity": "MEDIUM",
                        "description": "EBS volumes should be encrypted",
                        "recommendation": "Enable EBS encryption"
                    })
        
        return violations
    
    def _check_backup_policy(
        self,
        code: str,
        iac_type: str,
        provider: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Check backup policy compliance"""
        violations = []
        min_retention = self.policies["backup"]["minimum_retention_days"]
        
        if iac_type.lower() == "terraform":
            # Check RDS backup
            if 'aws_db_instance' in code:
                if not re.search(r'backup_retention_period', code):
                    violations.append({
                        "policy": "backup",
                        "severity": self.policies["backup"]["severity"],
                        "description": "RDS instance must have backup retention configured",
                        "recommendation": f"Set backup_retention_period >= {min_retention}"
                    })
                else:
                    # Check retention period
                    match = re.search(r'backup_retention_period\s*=\s*(\d+)', code)
                    if match and int(match.group(1)) < min_retention:
                        violations.append({
                            "policy": "backup",
                            "severity": "LOW",
                            "description": f"RDS backup retention period is less than {min_retention} days",
                            "recommendation": f"Increase backup_retention_period to at least {min_retention}"
                        })
            
            # Check S3 versioning
            if 'aws_s3_bucket' in code:
                if not re.search(r'versioning.*Enabled', code, re.DOTALL):
                    violations.append({
                        "policy": "backup",
                        "severity": "LOW",
                        "description": "S3 bucket should have versioning enabled",
                        "recommendation": "Enable versioning for data protection"
                    })
        
        return violations
    
    def _check_networking_policy(
        self,
        code: str,
        iac_type: str,
        provider: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Check networking policy compliance"""
        violations = []
        
        if iac_type.lower() == "terraform":
            # Check for default VPC usage
            if self.policies["networking"]["prohibit_default_vpc"]:
                if 'default_vpc' in code.lower() or 'default-vpc' in code.lower():
                    violations.append({
                        "policy": "networking",
                        "severity": self.policies["networking"]["severity"],
                        "description": "Using default VPC is prohibited",
                        "recommendation": "Create a custom VPC with proper network segmentation"
                    })
            
            # Check for overly permissive security groups
            if re.search(r'cidr_blocks\s*=\s*\["0\.0\.0\.0/0"\]', code):
                if 'ingress' in code:
                    violations.append({
                        "policy": "networking",
                        "severity": "HIGH",
                        "description": "Security group allows ingress from 0.0.0.0/0",
                        "recommendation": "Restrict ingress to specific IP ranges"
                    })
        
        elif iac_type.lower() == "kubernetes":
            # Check for host network usage
            if 'hostNetwork: true' in code:
                violations.append({
                    "policy": "networking",
                    "severity": "HIGH",
                    "description": "Pod is using host network",
                    "recommendation": "Avoid hostNetwork unless absolutely necessary"
                })
        
        return violations
    
    def _check_logging_policy(
        self,
        code: str,
        iac_type: str,
        provider: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Check logging policy compliance"""
        violations = []
        
        if iac_type.lower() == "terraform":
            # Check S3 access logging
            if 'aws_s3_bucket' in code:
                if not re.search(r'logging\s*\{', code):
                    violations.append({
                        "policy": "logging",
                        "severity": self.policies["logging"]["severity"],
                        "description": "S3 bucket should have access logging enabled",
                        "recommendation": "Enable S3 access logging"
                    })
            
            # Check CloudTrail
            if 'aws_' in code and 'aws_cloudtrail' not in code:
                violations.append({
                    "policy": "logging",
                    "severity": "LOW",
                    "description": "Consider enabling CloudTrail for audit logging",
                    "recommendation": "Add CloudTrail configuration"
                })
            
            # Check RDS logging
            if 'aws_db_instance' in code:
                if not re.search(r'enabled_cloudwatch_logs_exports', code):
                    violations.append({
                        "policy": "logging",
                        "severity": "MEDIUM",
                        "description": "RDS instance should export logs to CloudWatch",
                        "recommendation": "Enable CloudWatch log exports"
                    })
        
        return violations
    
    def _extract_resource_block(self, code: str, start_pos: int) -> str:
        """Extract resource block from code"""
        # Simple extraction - find matching braces
        brace_count = 0
        in_block = False
        block = []
        
        for i, char in enumerate(code[start_pos:], start_pos):
            if char == '{':
                brace_count += 1
                in_block = True
            elif char == '}':
                brace_count -= 1
            
            if in_block:
                block.append(char)
            
            if in_block and brace_count == 0:
                break
        
        return ''.join(block)
    
    def add_custom_policy(
        self,
        policy_name: str,
        policy_config: Dict[str, Any]
    ):
        """Add a custom compliance policy
        
        Args:
            policy_name: Name of the policy
            policy_config: Policy configuration
        """
        self.policies[policy_name] = policy_config
        logger.info(f"Added custom policy: {policy_name}")
