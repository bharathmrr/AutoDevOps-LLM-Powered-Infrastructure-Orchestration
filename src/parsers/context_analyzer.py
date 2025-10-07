"""Analyze conversation context for better understanding"""

from typing import List, Dict, Any, Optional
from loguru import logger


class ContextAnalyzer:
    """Analyze and maintain conversation context"""
    
    def __init__(self, max_history: int = 10):
        """Initialize context analyzer
        
        Args:
            max_history: Maximum conversation history to maintain
        """
        self.max_history = max_history
        self.conversation_history: List[Dict[str, Any]] = []
        self.context_state: Dict[str, Any] = {}
        
        logger.info("Context analyzer initialized")
    
    def add_turn(
        self,
        user_input: str,
        intent: Dict[str, Any],
        parameters: Dict[str, Any],
        response: Optional[str] = None
    ):
        """Add a conversation turn to history
        
        Args:
            user_input: User's input
            intent: Parsed intent
            parameters: Extracted parameters
            response: System response
        """
        turn = {
            "user_input": user_input,
            "intent": intent,
            "parameters": parameters,
            "response": response,
        }
        
        self.conversation_history.append(turn)
        
        # Maintain max history
        if len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)
        
        # Update context state
        self._update_context_state(turn)
    
    def _update_context_state(self, turn: Dict[str, Any]):
        """Update context state based on new turn
        
        Args:
            turn: Conversation turn
        """
        intent = turn["intent"]
        parameters = turn["parameters"]
        
        # Update provider if specified
        if intent.get("provider"):
            self.context_state["provider"] = intent["provider"]
        
        # Update IaC type if specified
        if intent.get("iac_type"):
            self.context_state["iac_type"] = intent["iac_type"]
        
        # Accumulate resources
        if intent.get("resources"):
            if "resources" not in self.context_state:
                self.context_state["resources"] = []
            self.context_state["resources"].extend(intent["resources"])
            self.context_state["resources"] = list(set(self.context_state["resources"]))
        
        # Update parameters (merge with existing)
        if "parameters" not in self.context_state:
            self.context_state["parameters"] = {}
        
        for category, params in parameters.items():
            if category not in self.context_state["parameters"]:
                self.context_state["parameters"][category] = {}
            self.context_state["parameters"][category].update(params)
    
    def get_context(self) -> Dict[str, Any]:
        """Get current context state
        
        Returns:
            Current context dictionary
        """
        return self.context_state.copy()
    
    def get_history(self, n: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation history
        
        Args:
            n: Number of recent turns to return (None for all)
            
        Returns:
            List of conversation turns
        """
        if n is None:
            return self.conversation_history.copy()
        return self.conversation_history[-n:]
    
    def infer_missing_parameters(
        self,
        current_intent: Dict[str, Any],
        current_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Infer missing parameters from context
        
        Args:
            current_intent: Current parsed intent
            current_parameters: Current extracted parameters
            
        Returns:
            Enhanced parameters with inferred values
        """
        enhanced = current_parameters.copy()
        
        # Infer provider from context if not specified
        if not current_intent.get("provider") and self.context_state.get("provider"):
            logger.info(f"Inferring provider from context: {self.context_state['provider']}")
            current_intent["provider"] = self.context_state["provider"]
        
        # Infer IaC type from context if not specified
        if not current_intent.get("iac_type") and self.context_state.get("iac_type"):
            logger.info(f"Inferring IaC type from context: {self.context_state['iac_type']}")
            current_intent["iac_type"] = self.context_state["iac_type"]
        
        # Merge parameters from context if categories are missing
        if "parameters" in self.context_state:
            for category, params in self.context_state["parameters"].items():
                if category not in enhanced or not enhanced[category]:
                    enhanced[category] = params.copy()
                    logger.info(f"Using {category} parameters from context")
        
        return enhanced
    
    def detect_follow_up(self, current_input: str) -> bool:
        """Detect if current input is a follow-up to previous conversation
        
        Args:
            current_input: Current user input
            
        Returns:
            True if this is a follow-up
        """
        if not self.conversation_history:
            return False
        
        follow_up_indicators = [
            "also", "additionally", "and", "plus", "furthermore",
            "modify", "change", "update", "add", "remove",
            "it", "that", "this", "them", "those"
        ]
        
        input_lower = current_input.lower()
        return any(indicator in input_lower for indicator in follow_up_indicators)
    
    def get_related_resources(self) -> List[str]:
        """Get list of resources mentioned in conversation
        
        Returns:
            List of resource types
        """
        return self.context_state.get("resources", [])
    
    def clear_context(self):
        """Clear conversation history and context"""
        self.conversation_history.clear()
        self.context_state.clear()
        logger.info("Context cleared")
    
    def summarize_context(self) -> str:
        """Generate a summary of current context
        
        Returns:
            Context summary string
        """
        summary_parts = []
        
        if self.context_state.get("provider"):
            summary_parts.append(f"Provider: {self.context_state['provider']}")
        
        if self.context_state.get("iac_type"):
            summary_parts.append(f"IaC Type: {self.context_state['iac_type']}")
        
        if self.context_state.get("resources"):
            resources = ", ".join(self.context_state["resources"][:5])
            summary_parts.append(f"Resources: {resources}")
        
        if not summary_parts:
            return "No context available"
        
        return " | ".join(summary_parts)
