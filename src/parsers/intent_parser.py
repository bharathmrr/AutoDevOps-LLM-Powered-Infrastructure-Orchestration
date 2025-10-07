"""Parse user intent from natural language"""

import re
from typing import Dict, Any, Optional, List
from loguru import logger


class IntentParser:
    """Parse and classify user intent"""
    
    # Keywords for different intents
    INTENT_KEYWORDS = {
        "create": ["create", "deploy", "setup", "provision", "build", "launch", "spin up", "make"],
        "modify": ["modify", "update", "change", "edit", "alter", "adjust", "reconfigure"],
        "delete": ["delete", "remove", "destroy", "terminate", "tear down", "decommission"],
        "scale": ["scale", "resize", "increase", "decrease", "expand", "shrink"],
        "query": ["show", "list", "get", "describe", "what", "how", "explain"],
        "validate": ["validate", "check", "verify", "test", "lint"],
    }
    
    # Keywords for IaC types
    IAC_KEYWORDS = {
        "terraform": ["terraform", "tf", "hcl"],
        "kubernetes": ["kubernetes", "k8s", "kubectl", "deployment", "pod", "service"],
        "ansible": ["ansible", "playbook", "role"],
        "docker": ["docker", "dockerfile", "container", "image"],
    }
    
    # Keywords for cloud providers
    PROVIDER_KEYWORDS = {
        "aws": ["aws", "amazon", "ec2", "s3", "rds", "lambda", "cloudformation"],
        "azure": ["azure", "microsoft", "vm", "blob", "cosmos"],
        "gcp": ["gcp", "google cloud", "gce", "gcs", "bigquery"],
        "kubernetes": ["kubernetes", "k8s"],
        "docker": ["docker"],
    }
    
    def __init__(self):
        """Initialize intent parser"""
        logger.info("Intent parser initialized")
    
    def parse(self, user_input: str) -> Dict[str, Any]:
        """Parse user input and extract intent
        
        Args:
            user_input: Natural language input from user
            
        Returns:
            Dictionary containing parsed intent information
        """
        user_input_lower = user_input.lower()
        
        intent = {
            "original_input": user_input,
            "action": self._detect_action(user_input_lower),
            "iac_type": self._detect_iac_type(user_input_lower),
            "provider": self._detect_provider(user_input_lower),
            "resources": self._extract_resources(user_input_lower),
            "confidence": 0.0
        }
        
        # Calculate confidence score
        intent["confidence"] = self._calculate_confidence(intent)
        
        logger.info(f"Parsed intent: action={intent['action']}, iac_type={intent['iac_type']}, provider={intent['provider']}")
        
        return intent
    
    def _detect_action(self, text: str) -> str:
        """Detect the primary action/intent
        
        Args:
            text: Lowercase user input
            
        Returns:
            Detected action
        """
        for action, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return action
        
        # Default to create if no specific action detected
        return "create"
    
    def _detect_iac_type(self, text: str) -> Optional[str]:
        """Detect Infrastructure-as-Code type
        
        Args:
            text: Lowercase user input
            
        Returns:
            Detected IaC type or None
        """
        scores = {}
        
        for iac_type, keywords in self.IAC_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[iac_type] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        # Try to infer from context
        if any(word in text for word in ["manifest", "yaml", "pod", "deployment"]):
            return "kubernetes"
        elif any(word in text for word in ["playbook", "role", "task"]):
            return "ansible"
        elif any(word in text for word in ["container", "image"]):
            return "docker"
        
        # Default to terraform for infrastructure
        return "terraform"
    
    def _detect_provider(self, text: str) -> Optional[str]:
        """Detect cloud provider
        
        Args:
            text: Lowercase user input
            
        Returns:
            Detected provider or None
        """
        scores = {}
        
        for provider, keywords in self.PROVIDER_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[provider] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return None
    
    def _extract_resources(self, text: str) -> List[str]:
        """Extract infrastructure resources mentioned
        
        Args:
            text: Lowercase user input
            
        Returns:
            List of detected resources
        """
        resources = []
        
        # Common infrastructure resources
        resource_patterns = [
            r'\b(ec2|instance|vm|virtual machine)s?\b',
            r'\b(s3|bucket|storage)s?\b',
            r'\b(rds|database|db)s?\b',
            r'\b(vpc|network)s?\b',
            r'\b(load balancer|alb|elb|lb)s?\b',
            r'\b(lambda|function)s?\b',
            r'\b(container|pod)s?\b',
            r'\b(service)s?\b',
            r'\b(deployment)s?\b',
            r'\b(volume|disk)s?\b',
        ]
        
        for pattern in resource_patterns:
            matches = re.findall(pattern, text)
            resources.extend(matches)
        
        return list(set(resources))
    
    def _calculate_confidence(self, intent: Dict[str, Any]) -> float:
        """Calculate confidence score for parsed intent
        
        Args:
            intent: Parsed intent dictionary
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        score = 0.0
        
        # Action detected
        if intent["action"]:
            score += 0.3
        
        # IaC type detected
        if intent["iac_type"]:
            score += 0.3
        
        # Provider detected
        if intent["provider"]:
            score += 0.2
        
        # Resources detected
        if intent["resources"]:
            score += 0.2
        
        return min(score, 1.0)
    
    def is_valid_intent(self, intent: Dict[str, Any], min_confidence: float = 0.5) -> bool:
        """Check if intent is valid and actionable
        
        Args:
            intent: Parsed intent dictionary
            min_confidence: Minimum confidence threshold
            
        Returns:
            True if intent is valid
        """
        return intent["confidence"] >= min_confidence
