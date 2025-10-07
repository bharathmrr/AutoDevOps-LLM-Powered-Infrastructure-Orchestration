"""Extract infrastructure parameters from natural language"""

import re
from typing import Dict, Any, List, Optional
from loguru import logger


class ParameterExtractor:
    """Extract infrastructure parameters from user input"""
    
    def __init__(self):
        """Initialize parameter extractor"""
        logger.info("Parameter extractor initialized")
    
    def extract(self, user_input: str, intent: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extract parameters from user input
        
        Args:
            user_input: Natural language input
            intent: Optional parsed intent for context
            
        Returns:
            Dictionary of extracted parameters
        """
        params = {
            "compute": self._extract_compute_params(user_input),
            "storage": self._extract_storage_params(user_input),
            "network": self._extract_network_params(user_input),
            "scaling": self._extract_scaling_params(user_input),
            "security": self._extract_security_params(user_input),
            "general": self._extract_general_params(user_input),
        }
        
        # Remove empty sections
        params = {k: v for k, v in params.items() if v}
        
        logger.info(f"Extracted parameters: {list(params.keys())}")
        return params
    
    def _extract_compute_params(self, text: str) -> Dict[str, Any]:
        """Extract compute-related parameters"""
        params = {}
        text_lower = text.lower()
        
        # Instance type/size
        instance_patterns = [
            r't2\.(micro|small|medium|large)',
            r't3\.(micro|small|medium|large)',
            r'm5\.(large|xlarge|2xlarge)',
            r'(small|medium|large|xlarge) instance',
        ]
        
        for pattern in instance_patterns:
            match = re.search(pattern, text_lower)
            if match:
                params["instance_type"] = match.group(0)
                break
        
        # CPU/Memory
        cpu_match = re.search(r'(\d+)\s*(cpu|core|vcpu)s?', text_lower)
        if cpu_match:
            params["cpu"] = int(cpu_match.group(1))
        
        memory_match = re.search(r'(\d+)\s*(gb|gib|mb|mib)\s*(ram|memory)', text_lower)
        if memory_match:
            params["memory"] = f"{memory_match.group(1)}{memory_match.group(2)}"
        
        # Operating System
        os_keywords = {
            "ubuntu": "ubuntu",
            "amazon linux": "amazon-linux",
            "centos": "centos",
            "windows": "windows",
            "debian": "debian",
        }
        
        for keyword, os_name in os_keywords.items():
            if keyword in text_lower:
                params["os"] = os_name
                break
        
        return params
    
    def _extract_storage_params(self, text: str) -> Dict[str, Any]:
        """Extract storage-related parameters"""
        params = {}
        text_lower = text.lower()
        
        # Storage size
        size_match = re.search(r'(\d+)\s*(gb|tb|gib|tib)', text_lower)
        if size_match:
            params["size"] = f"{size_match.group(1)}{size_match.group(2)}"
        
        # Storage type
        if "ssd" in text_lower or "gp3" in text_lower or "gp2" in text_lower:
            params["type"] = "ssd"
        elif "magnetic" in text_lower or "standard" in text_lower:
            params["type"] = "standard"
        
        # Backup/Versioning
        if "backup" in text_lower or "snapshot" in text_lower:
            params["backup_enabled"] = True
        
        if "versioning" in text_lower or "version" in text_lower:
            params["versioning_enabled"] = True
        
        # Encryption
        if "encrypt" in text_lower or "encryption" in text_lower:
            params["encryption_enabled"] = True
        
        return params
    
    def _extract_network_params(self, text: str) -> Dict[str, Any]:
        """Extract network-related parameters"""
        params = {}
        text_lower = text.lower()
        
        # Ports
        port_matches = re.findall(r'port\s+(\d+)', text_lower)
        if port_matches:
            params["ports"] = [int(port) for port in port_matches]
        
        # Common port keywords
        if "http" in text_lower and "ports" not in params:
            params["ports"] = [80]
        if "https" in text_lower:
            if "ports" in params:
                params["ports"].append(443)
            else:
                params["ports"] = [443]
        
        # Load balancer
        if "load balancer" in text_lower or "lb" in text_lower:
            params["load_balancer"] = True
        
        # Public/Private
        if "public" in text_lower:
            params["public_access"] = True
        elif "private" in text_lower:
            params["public_access"] = False
        
        # VPC/Subnet
        vpc_match = re.search(r'vpc[- ]?(\w+)', text_lower)
        if vpc_match:
            params["vpc"] = vpc_match.group(1)
        
        return params
    
    def _extract_scaling_params(self, text: str) -> Dict[str, Any]:
        """Extract scaling-related parameters"""
        params = {}
        text_lower = text.lower()
        
        # Number of instances/replicas
        count_patterns = [
            r'(\d+)\s*(instance|replica|node|server)s?',
            r'(instance|replica|node|server)s?\s+of\s+(\d+)',
        ]
        
        for pattern in count_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    params["count"] = int(match.group(1) if match.group(1).isdigit() else match.group(2))
                    break
                except:
                    pass
        
        # Min/Max for auto-scaling
        min_match = re.search(r'min(?:imum)?\s+(?:of\s+)?(\d+)', text_lower)
        if min_match:
            params["min_size"] = int(min_match.group(1))
        
        max_match = re.search(r'max(?:imum)?\s+(?:of\s+)?(\d+)', text_lower)
        if max_match:
            params["max_size"] = int(max_match.group(1))
        
        # Auto-scaling
        if "auto" in text_lower and "scal" in text_lower:
            params["auto_scaling"] = True
        
        # High availability
        if "high availability" in text_lower or "ha" in text_lower or "highly available" in text_lower:
            params["high_availability"] = True
        
        # Multi-AZ
        if "multi-az" in text_lower or "multi az" in text_lower:
            params["multi_az"] = True
        
        return params
    
    def _extract_security_params(self, text: str) -> Dict[str, Any]:
        """Extract security-related parameters"""
        params = {}
        text_lower = text.lower()
        
        # SSL/TLS
        if "ssl" in text_lower or "tls" in text_lower or "https" in text_lower:
            params["ssl_enabled"] = True
        
        # Authentication
        if "auth" in text_lower or "authentication" in text_lower:
            params["authentication_required"] = True
        
        # Firewall/Security groups
        if "firewall" in text_lower or "security group" in text_lower:
            params["firewall_enabled"] = True
        
        # IAM/RBAC
        if "iam" in text_lower or "rbac" in text_lower or "role" in text_lower:
            params["rbac_enabled"] = True
        
        return params
    
    def _extract_general_params(self, text: str) -> Dict[str, Any]:
        """Extract general parameters"""
        params = {}
        text_lower = text.lower()
        
        # Region
        region_patterns = [
            r'(us-east-1|us-west-1|us-west-2|eu-west-1|eu-central-1|ap-southeast-1)',
            r'in\s+(us|eu|asia|europe|america)',
        ]
        
        for pattern in region_patterns:
            match = re.search(pattern, text_lower)
            if match:
                params["region"] = match.group(1)
                break
        
        # Environment
        env_keywords = ["production", "staging", "development", "test", "dev", "prod"]
        for env in env_keywords:
            if env in text_lower:
                params["environment"] = env
                break
        
        # Tags/Labels
        name_match = re.search(r'named?\s+["\']?(\w+)["\']?', text_lower)
        if name_match:
            params["name"] = name_match.group(1)
        
        # Monitoring
        if "monitor" in text_lower or "logging" in text_lower or "cloudwatch" in text_lower:
            params["monitoring_enabled"] = True
        
        return params
    
    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        """Validate extracted parameters
        
        Args:
            params: Extracted parameters
            
        Returns:
            List of validation warnings
        """
        warnings = []
        
        # Check for conflicting parameters
        if "scaling" in params:
            scaling = params["scaling"]
            if "count" in scaling and "auto_scaling" in scaling:
                if scaling.get("auto_scaling") and "min_size" not in scaling:
                    warnings.append("Auto-scaling enabled but min_size not specified")
        
        # Check for security best practices
        if "network" in params:
            network = params["network"]
            if network.get("public_access") and "security" not in params:
                warnings.append("Public access enabled without explicit security configuration")
        
        return warnings
