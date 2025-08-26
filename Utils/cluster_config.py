"""
Cluster Configuration Manager
Handles persistence of cluster-related settings like pinned clusters
"""

import json
import os
import logging
from typing import Set, List


class ClusterConfig:
    """Simple cluster configuration manager for persistent settings"""
    
    def __init__(self):
        # Store config in user's home directory under .orchetrix
        self.config_dir = os.path.expanduser("~/.orchetrix")
        self.config_file = os.path.join(self.config_dir, "cluster_config.json")
        self.config = self._load_config()
        
    def _ensure_config_dir(self):
        """Ensure the configuration directory exists"""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
        except Exception as e:
            logging.warning(f"Could not create config directory {self.config_dir}: {e}")
            
    def _load_config(self) -> dict:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logging.debug(f"Loaded cluster config from {self.config_file}")
                    return config
        except Exception as e:
            logging.warning(f"Could not load cluster config: {e}")
            
        # Return default config
        return {
            "pinned_clusters": []
        }
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            self._ensure_config_dir()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
                logging.debug(f"Saved cluster config to {self.config_file}")
        except Exception as e:
            logging.error(f"Could not save cluster config: {e}")
    
    def get_pinned_clusters(self) -> Set[str]:
        """Get the set of pinned cluster names"""
        return set(self.config.get("pinned_clusters", []))
    
    def set_pinned_clusters(self, pinned_clusters: Set[str]):
        """Set the pinned cluster names and save to file"""
        self.config["pinned_clusters"] = list(pinned_clusters)
        self._save_config()
        logging.info(f"Updated pinned clusters: {pinned_clusters}")
    
    def add_pinned_cluster(self, cluster_name: str):
        """Add a cluster to the pinned list"""
        pinned = self.get_pinned_clusters()
        pinned.add(cluster_name)
        self.set_pinned_clusters(pinned)
        
    def remove_pinned_cluster(self, cluster_name: str):
        """Remove a cluster from the pinned list"""
        pinned = self.get_pinned_clusters()
        pinned.discard(cluster_name)
        self.set_pinned_clusters(pinned)
        
    def is_pinned(self, cluster_name: str) -> bool:
        """Check if a cluster is pinned"""
        return cluster_name in self.get_pinned_clusters()


# Global singleton instance
_cluster_config = None


def get_cluster_config() -> ClusterConfig:
    """Get the global cluster configuration singleton"""
    global _cluster_config
    if _cluster_config is None:
        _cluster_config = ClusterConfig()
    return _cluster_config