from abc import ABC, abstractmethod
from typing import Any, Dict, List

class StorageInterface(ABC):
    @abstractmethod
    def load_data(self) -> Dict[str, Any]:
        """Load all data (users, tasks, metadata) from storage."""
        pass

    @abstractmethod
    def save_data(self, data:Dict[str, Any]) -> None:
        """Save all data to storage."""
        pass