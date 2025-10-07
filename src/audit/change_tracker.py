"""Track infrastructure changes"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger


class ChangeTracker:
    """Track all infrastructure changes"""
    
    def __init__(self, tracking_file: str = "./logs/changes.json"):
        """Initialize change tracker
        
        Args:
            tracking_file: Path to tracking file
        """
        self.tracking_file = Path(tracking_file)
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.changes = self._load_changes()
        
        logger.info(f"Change tracker initialized: {self.tracking_file}")
    
    def _load_changes(self) -> List[Dict[str, Any]]:
        """Load existing changes from file"""
        if not self.tracking_file.exists():
            return []
        
        try:
            with open(self.tracking_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading changes: {e}")
            return []
    
    def _save_changes(self):
        """Save changes to file"""
        try:
            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(self.changes, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving changes: {e}")
    
    def track_change(
        self,
        change_type: str,
        resource_type: str,
        resource_name: str,
        details: Dict[str, Any],
        file_path: Optional[str] = None
    ) -> str:
        """Track a change
        
        Args:
            change_type: Type of change (create, update, delete)
            resource_type: Type of resource
            resource_name: Name of resource
            details: Change details
            file_path: Path to file
            
        Returns:
            Change ID
        """
        change_id = f"{change_type}_{resource_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        change = {
            "id": change_id,
            "timestamp": datetime.now().isoformat(),
            "change_type": change_type,
            "resource_type": resource_type,
            "resource_name": resource_name,
            "details": details,
            "file_path": file_path,
            "status": "pending"
        }
        
        self.changes.append(change)
        self._save_changes()
        
        logger.info(f"Tracked change: {change_id}")
        return change_id
    
    def update_change_status(self, change_id: str, status: str, result: Optional[Dict[str, Any]] = None):
        """Update status of a tracked change
        
        Args:
            change_id: Change ID
            status: New status (pending, applied, failed, rolled_back)
            result: Optional result details
        """
        for change in self.changes:
            if change["id"] == change_id:
                change["status"] = status
                change["updated_at"] = datetime.now().isoformat()
                if result:
                    change["result"] = result
                break
        
        self._save_changes()
        logger.info(f"Updated change {change_id} status to {status}")
    
    def get_changes(
        self,
        status: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get tracked changes
        
        Args:
            status: Filter by status
            resource_type: Filter by resource type
            limit: Maximum number of changes to return
            
        Returns:
            List of changes
        """
        filtered = self.changes
        
        if status:
            filtered = [c for c in filtered if c.get("status") == status]
        
        if resource_type:
            filtered = [c for c in filtered if c.get("resource_type") == resource_type]
        
        return filtered[-limit:]
    
    def get_change_summary(self) -> Dict[str, Any]:
        """Get summary of all changes
        
        Returns:
            Summary dictionary
        """
        summary = {
            "total_changes": len(self.changes),
            "by_status": {},
            "by_type": {},
            "by_resource_type": {}
        }
        
        for change in self.changes:
            # Count by status
            status = change.get("status", "unknown")
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
            
            # Count by change type
            change_type = change.get("change_type", "unknown")
            summary["by_type"][change_type] = summary["by_type"].get(change_type, 0) + 1
            
            # Count by resource type
            resource_type = change.get("resource_type", "unknown")
            summary["by_resource_type"][resource_type] = summary["by_resource_type"].get(resource_type, 0) + 1
        
        return summary
