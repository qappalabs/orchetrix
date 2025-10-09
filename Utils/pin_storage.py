"""
Pin Storage Manager - Handles persistent storage of pinned items in JSON format.
"""
import json
import os
import logging
from typing import Set, List

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
        
    def _ensure_data_directory(self):
        """Ensure the data directory exists."""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            logging.info(f"Data directory ready: {self.data_dir}")
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
                "last_updated": self._get_current_timestamp()
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
            
    def add_pinned_item(self, item_name: str) -> bool:
        """
        Add an item to pinned items.
        
        Args:
            item_name: Name of the item to pin
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        pinned_items = self.load_pinned_items()
        pinned_items.add(item_name)
        return self.save_pinned_items(pinned_items)
        
    def remove_pinned_item(self, item_name: str) -> bool:
        """
        Remove an item from pinned items.
        
        Args:
            item_name: Name of the item to unpin
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        pinned_items = self.load_pinned_items()
        pinned_items.discard(item_name)  # discard doesn't raise error if item not found
        return self.save_pinned_items(pinned_items)
        
    def is_item_pinned(self, item_name: str) -> bool:
        """
        Check if an item is pinned.
        
        Args:
            item_name: Name of the item to check
            
        Returns:
            bool: True if item is pinned, False otherwise
        """
        pinned_items = self.load_pinned_items()
        return item_name in pinned_items
        
    def clear_all_pins(self) -> bool:
        """
        Clear all pinned items.
        
        Returns:
            bool: True if cleared successfully, False otherwise
        """
        return self.save_pinned_items(set())
        
    def get_pins_file_path(self) -> str:
        """Get the path to the pins file."""
        return self.pins_file
        
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as string."""
        from datetime import datetime
        return datetime.now().isoformat()

# Global instance
_pin_storage_manager = None

def get_pin_storage_manager() -> PinStorageManager:
    """Get the global pin storage manager instance."""
    global _pin_storage_manager
    if _pin_storage_manager is None:
        _pin_storage_manager = PinStorageManager()
    return _pin_storage_manager