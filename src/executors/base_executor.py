"""Base class for all executors"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger


class BaseExecutor(ABC):
    """Abstract base class for infrastructure executors"""
    
    def __init__(self, working_dir: str = "./infrastructure"):
        """Initialize executor
        
        Args:
            working_dir: Working directory for execution
        """
        self.working_dir = Path(working_dir)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"{self.__class__.__name__} initialized with working dir: {working_dir}")
    
    @abstractmethod
    def plan(self, file_path: str) -> Dict[str, Any]:
        """Plan infrastructure changes
        
        Args:
            file_path: Path to IaC file
            
        Returns:
            Plan result dictionary
        """
        pass
    
    @abstractmethod
    def apply(self, file_path: str, auto_approve: bool = False) -> Dict[str, Any]:
        """Apply infrastructure changes
        
        Args:
            file_path: Path to IaC file
            auto_approve: Auto-approve changes
            
        Returns:
            Apply result dictionary
        """
        pass
    
    @abstractmethod
    def destroy(self, file_path: str, auto_approve: bool = False) -> Dict[str, Any]:
        """Destroy infrastructure
        
        Args:
            file_path: Path to IaC file
            auto_approve: Auto-approve destruction
            
        Returns:
            Destroy result dictionary
        """
        pass
    
    def validate_file(self, file_path: str) -> bool:
        """Validate that file exists
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file exists
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return False
        return True
