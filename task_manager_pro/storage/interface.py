"""
storage/interface.py

Defines an abstract interface for storage backends used by Task Manager PRO.
This interface enforces a contract for loading and saving task/user data,
enabling flexibility to support different storage mechanisms (e.g., JSON, SQLite).
"""

from abc import ABC, abstractmethod
from typing import Any


class StorageInterface(ABC):
    @abstractmethod
    def load_data(self) -> dict[str, Any]:
        """
        Load all data from the storage backend.

        Returns:
            Dict[str, Any]: Dictionary containing 'users', 'tasks', and any other metadata.
        """
        pass

    @abstractmethod
    def save_data(self, data: dict[str, Any]) -> None:
        """
        Save all data to the storage backend.

        Args:
            data (Dict[str, Any]): Dictionary containing 'users', 'tasks', and other relevant info.
        """
        pass
