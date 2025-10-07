"""Audit logging system"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger as log


class AuditLogger:
    """Audit logger for tracking all infrastructure changes"""
    
    def __init__(self, log_dir: str = "./logs"):
        """Initialize audit logger
        
        Args:
            log_dir: Directory for audit logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.audit_file = self.log_dir / "audit.jsonl"
        
        log.info(f"Audit logger initialized: {self.audit_file}")
    
    def log_event(
        self,
        event_type: str,
        action: str,
        details: Dict[str, Any],
        user: Optional[str] = None,
        success: bool = True
    ):
        """Log an audit event
        
        Args:
            event_type: Type of event (generate, validate, execute, etc.)
            action: Action performed
            details: Event details
            user: User who performed the action
            success: Whether the action was successful
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "action": action,
            "details": details,
            "user": user or "system",
            "success": success
        }
        
        try:
            with open(self.audit_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event) + '\n')
            
            log.info(f"Audit event logged: {event_type}.{action}")
        
        except Exception as e:
            log.error(f"Error logging audit event: {e}")
    
    def log_generation(
        self,
        iac_type: str,
        provider: str,
        file_path: str,
        intent: Dict[str, Any],
        success: bool = True
    ):
        """Log code generation event
        
        Args:
            iac_type: Type of IaC
            provider: Cloud provider
            file_path: Path to generated file
            intent: User intent
            success: Whether generation was successful
        """
        self.log_event(
            event_type="generation",
            action="generate_code",
            details={
                "iac_type": iac_type,
                "provider": provider,
                "file_path": file_path,
                "intent": intent
            },
            success=success
        )
    
    def log_validation(
        self,
        iac_type: str,
        file_path: str,
        validation_results: Dict[str, Any],
        success: bool = True
    ):
        """Log validation event
        
        Args:
            iac_type: Type of IaC
            file_path: Path to validated file
            validation_results: Validation results
            success: Whether validation passed
        """
        self.log_event(
            event_type="validation",
            action="validate_code",
            details={
                "iac_type": iac_type,
                "file_path": file_path,
                "results": validation_results
            },
            success=success
        )
    
    def log_execution(
        self,
        iac_type: str,
        action: str,
        file_path: str,
        result: Dict[str, Any],
        success: bool = True
    ):
        """Log execution event
        
        Args:
            iac_type: Type of IaC
            action: Execution action (plan, apply, destroy)
            file_path: Path to executed file
            result: Execution result
            success: Whether execution was successful
        """
        self.log_event(
            event_type="execution",
            action=f"execute_{action}",
            details={
                "iac_type": iac_type,
                "file_path": file_path,
                "result": result
            },
            success=success
        )
    
    def get_recent_events(self, count: int = 100) -> list:
        """Get recent audit events
        
        Args:
            count: Number of events to retrieve
            
        Returns:
            List of recent events
        """
        if not self.audit_file.exists():
            return []
        
        try:
            events = []
            with open(self.audit_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-count:]:
                    events.append(json.loads(line))
            
            return events
        
        except Exception as e:
            log.error(f"Error reading audit events: {e}")
            return []
