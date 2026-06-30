"""
Pin Storage Manager – Handles persistent storage of pinned items in JSON format.
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Set

__all__ = ["PinStorageManager", "get_pin_storage_manager"]

class PinStorageManager:
    """Manages persistent storage of pinned items using JSON files."""

    def __init__(self, base_path: str = None):
        """
        Initialize the pin storage manager.
        
        Args:
            base_path: Base directory path. If None, uses current directory.
        """
        if base_path is None:
            base_path = os.path.dirname(os.path.abspath(__file__))
            base_path = os.path.dirname(base_path)  # Go up one level from Utils

        self.data_dir = os.path.join(base_path, "data")
        self.pins_file = os.path.join(self.data_dir, "pinned_items.json")

        # Ensure data directory exists
        self._ensure_data_directory()

    def _ensure_data_directory(self) -> None:
        """Ensure the data directory exists."""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            logging.debug(f"Data directory ready: {self.data_dir}")
        except Exception as e:
            logging.error(f"Failed to create data directory {self.data_dir}: {e}")

    def save_pinned_items(self, pinned_items: Set[str]) -> bool:
        """
        Save pinned items to JSON file.
        
        Args:
            pinned_items: Set of pinned item names
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Convert set to list for JSON serialization
            pinned_list = list(pinned_items) if pinned_items else []

            data = {
                "pinned_items": pinned_list,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

            with open(self.pins_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logging.info(f"Saved {len(pinned_list)} pinned items to {self.pins_file}")
            return True

        except Exception as e:
            logging.error(f"Failed to save pinned items: {e}")
            return False

    def load_pinned_items(self) -> Set[str]:
        """
        Load pinned items from JSON file.
        
        Returns:
            Set[str]: Set of pinned item names
        """
        try:
            if not os.path.exists(self.pins_file):
                logging.info(f"Pins file not found: {self.pins_file}. Starting with empty pins.")
                return set()

            with open(self.pins_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            pinned_list = data.get("pinned_items", [])
            pinned_set = set(pinned_list)

            logging.info(f"Loaded {len(pinned_set)} pinned items from {self.pins_file}")
            return pinned_set

        except Exception as e:
            logging.error(f"Failed to load pinned items: {e}")
            return set()

# Module-level singleton – use get_pin_storage_manager() for access
_pin_storage_manager: Optional[PinStorageManager] = None


def get_pin_storage_manager() -> PinStorageManager:
    """Return the application-wide PinStorageManager instance (lazy init)."""
    global _pin_storage_manager
    if _pin_storage_manager is None:
        _pin_storage_manager = PinStorageManager()
    return _pin_storage_manager
