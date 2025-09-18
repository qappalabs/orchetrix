"""
High-Performance Data Formatters and Utilities
Consolidates scattered formatting functions into optimized utilities.
Designed for maximum performance and consistent formatting across the app.
"""

import re
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Union, Optional, Dict, Any, List
from functools import wraps
from dataclasses import dataclass


@dataclass
class ResourceUsage:
    """Structured resource usage information"""
    value: float
    unit: str
    raw_value: str
    percentage: Optional[float] = None
    formatted: str = ""


class HighPerformanceFormatters:
    """High-performance formatters with caching and optimization"""
    
    # Pre-compiled regex patterns for performance
    _CPU_PATTERN = re.compile(r'^(\d+(?:\.\d+)?)([m]?)$')
    _MEMORY_PATTERN = re.compile(r'^(\d+(?:\.\d+)?)([KMGTPE]?i?)$')
    
    @staticmethod
    def format_age(timestamp_str: str) -> str:
        """Format age for display"""
        try:
            # Handle various timestamp formats
            if not timestamp_str or timestamp_str == 'Unknown':
                return 'Unknown'
            
            # Parse timestamp
            if isinstance(timestamp_str, str):
                # ISO format timestamp
                if 'T' in timestamp_str:
                    created = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    created = datetime.fromtimestamp(float(timestamp_str), tz=timezone.utc)
            else:
                created = timestamp_str
            
            # Ensure timezone aware
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            
            # Calculate age
            now = datetime.now(timezone.utc)
            age_delta = now - created
            
            # Format efficiently
            days = age_delta.days
            hours = age_delta.seconds // 3600
            minutes = (age_delta.seconds % 3600) // 60
            seconds = age_delta.seconds % 60
            
            # Return most significant unit
            if days > 365:
                years = days // 365
                return f"{years}y"
            elif days > 30:
                months = days // 30
                return f"{months}mo"
            elif days > 0:
                return f"{days}d"
            elif hours > 0:
                return f"{hours}h"
            elif minutes > 0:
                return f"{minutes}m"
            else:
                return f"{seconds}s"
                
        except Exception as e:
            logging.debug(f"Error formatting age for '{timestamp_str}': {e}")
            return 'Unknown'
    
    @staticmethod
    def format_age_from_datetime(dt: Optional[datetime]) -> str:
        """Format age from datetime object with performance optimization"""
        if not dt:
            return 'Unknown'
        
        # Convert to string for caching
        if hasattr(dt, 'timestamp'):
            timestamp_str = str(dt.timestamp())
        else:
            timestamp_str = dt.isoformat()
        
        return HighPerformanceFormatters.format_age(timestamp_str)
    
    @staticmethod
    def parse_cpu_value(cpu_str: str) -> ResourceUsage:
        """Parse CPU values"""
        if not cpu_str or not isinstance(cpu_str, str):
            return ResourceUsage(0.0, 'cores', cpu_str or '0', formatted='0 cores')
        
        cpu_str = cpu_str.strip()
        
        try:
            match = HighPerformanceFormatters._CPU_PATTERN.match(cpu_str)
            if not match:
                return ResourceUsage(0.0, 'cores', cpu_str, formatted='0 cores')
            
            value_str, unit = match.groups()
            value = float(value_str)
            
            if unit == 'm':  # millicores
                cores = value / 1000.0
                return ResourceUsage(
                    value=cores,
                    unit='cores',
                    raw_value=cpu_str,
                    formatted=f"{cores:.2f} cores" if cores >= 0.01 else f"{int(value)}m"
                )
            else:  # cores
                return ResourceUsage(
                    value=value,
                    unit='cores', 
                    raw_value=cpu_str,
                    formatted=f"{value} cores"
                )
                
        except (ValueError, AttributeError) as e:
            logging.debug(f"Error parsing CPU value '{cpu_str}': {e}")
            return ResourceUsage(0.0, 'cores', cpu_str, formatted='0 cores')
    
    @staticmethod
    def parse_memory_value(memory_str: str) -> ResourceUsage:
        """Parse memory values"""
        if not memory_str or not isinstance(memory_str, str):
            return ResourceUsage(0, 'bytes', memory_str or '0', formatted='0 B')
        
        memory_str = memory_str.strip()
        
        try:
            match = HighPerformanceFormatters._MEMORY_PATTERN.match(memory_str)
            if not match:
                # Try parsing as plain number (bytes)
                try:
                    value = float(memory_str)
                    return HighPerformanceFormatters._format_memory_bytes(value, memory_str)
                except ValueError:
                    return ResourceUsage(0, 'bytes', memory_str, formatted='0 B')
            
            value_str, unit = match.groups()
            value = float(value_str)
            
            # Memory unit multipliers (binary)
            multipliers = {
                '': 1,
                'Ki': 1024,
                'Mi': 1024**2,
                'Gi': 1024**3,
                'Ti': 1024**4,
                'Pi': 1024**5,
                'Ei': 1024**6,
                # Decimal units (less common in Kubernetes)
                'K': 1000,
                'M': 1000**2,
                'G': 1000**3,
                'T': 1000**4,
                'P': 1000**5,
                'E': 1000**6,
            }
            
            multiplier = multipliers.get(unit, 1)
            bytes_value = int(value * multiplier)
            
            return HighPerformanceFormatters._format_memory_bytes(bytes_value, memory_str)
            
        except (ValueError, AttributeError) as e:
            logging.debug(f"Error parsing memory value '{memory_str}': {e}")
            return ResourceUsage(0, 'bytes', memory_str, formatted='0 B')
    
    @staticmethod
    def _format_memory_bytes(bytes_value: float, original_str: str) -> ResourceUsage:
        """Format bytes value into human-readable format"""
        
        # Choose best unit for display
        if bytes_value >= 1024**4:  # TB
            formatted = f"{bytes_value / (1024**4):.1f} TB"
        elif bytes_value >= 1024**3:  # GB  
            formatted = f"{bytes_value / (1024**3):.1f} GB"
        elif bytes_value >= 1024**2:  # MB
            formatted = f"{bytes_value / (1024**2):.1f} MB"
        elif bytes_value >= 1024:  # KB
            formatted = f"{bytes_value / 1024:.1f} KB"
        else:  # Bytes
            formatted = f"{int(bytes_value)} B"
        
        return ResourceUsage(
            value=bytes_value,
            unit='bytes',
            raw_value=original_str,
            formatted=formatted
        )
    
    @staticmethod
    def format_percentage(value: Optional[float], precision: int = 1) -> str:
        """Format percentage with consistent precision"""
        if value is None:
            return 'N/A'
        
        try:
            if value < 0:
                return '0.0%'
            elif value > 100:
                return '100.0%'
            else:
                return f"{value:.{precision}f}%"
        except (TypeError, ValueError):
            return 'N/A'
    
    @staticmethod
    def format_resource_ratio(used: Union[str, int, float], total: Union[str, int, float]) -> str:
        """Format resource usage ratio (e.g., '2/4')"""
        try:
            if isinstance(used, str):
                used_val = float(used) if used.replace('.', '', 1).isdigit() else 0
            else:
                used_val = float(used or 0)
            
            if isinstance(total, str):
                total_val = float(total) if total.replace('.', '', 1).isdigit() else 0
            else:
                total_val = float(total or 0)
            
            # Handle special cases
            if total_val == 0:
                return f"{int(used_val)}/0"
            
            return f"{int(used_val)}/{int(total_val)}"
            
        except (ValueError, TypeError):
            return f"{used}/{total}"
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration"""
        if seconds < 0:
            return '0s'
        
        try:
            # Handle very small durations
            if seconds < 1:
                return f"{int(seconds * 1000)}ms"
            
            # Calculate time units
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            
            # Format based on magnitude
            if days > 0:
                return f"{days}d {hours}h"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            elif minutes > 0:
                return f"{minutes}m {secs}s"
            else:
                return f"{secs}s"
                
        except (ValueError, TypeError):
            return '0s'
    
    @staticmethod
    def format_status_with_color(status: str, status_mapping: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Format status with appropriate color coding"""
        default_mapping = {
            # Pod statuses
            'Running': '#4CAF50',      # Green
            'Pending': '#FF9800',      # Orange
            'Succeeded': '#2196F3',    # Blue
            'Failed': '#F44336',       # Red
            'Unknown': '#9E9E9E',      # Grey
            'CrashLoopBackOff': '#F44336',  # Red
            'ImagePullBackOff': '#F44336',  # Red
            'CreateContainerError': '#F44336',  # Red
            
            # Node statuses
            'Ready': '#4CAF50',        # Green
            'NotReady': '#F44336',     # Red
            'SchedulingDisabled': '#FF9800',  # Orange
            
            # General statuses
            'Active': '#4CAF50',       # Green
            'Inactive': '#9E9E9E',     # Grey
            'Error': '#F44336',        # Red
            'Warning': '#FF9800',      # Orange
            'Success': '#4CAF50',      # Green
            'Info': '#2196F3',         # Blue
        }
        
        color_mapping = status_mapping or default_mapping
        
        return {
            'status': status,
            'color': color_mapping.get(status, '#9E9E9E'),  # Default grey
            'text_color': '#FFFFFF' if color_mapping.get(status) in ['#F44336', '#4CAF50'] else '#000000'
        }
    
    @staticmethod
    def truncate_string(text: str, max_length: int = 50, suffix: str = '...') -> str:
        """Truncate string with performance optimization"""
        if not text or len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def format_list_display(items: List[str], max_items: int = 3, separator: str = ', ') -> str:
        """Format list for display with item limit"""
        if not items:
            return '<none>'
        
        if len(items) <= max_items:
            return separator.join(items)
        
        displayed_items = items[:max_items]
        remaining_count = len(items) - max_items
        
        return f"{separator.join(displayed_items)} (+{remaining_count} more)"
    
    @staticmethod
    def parse_label_selector(selector: str) -> Dict[str, str]:
        """Parse Kubernetes label selector efficiently"""
        if not selector:
            return {}
        
        labels = {}
        
        try:
            # Handle simple key=value pairs
            pairs = selector.split(',')
            for pair in pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    labels[key.strip()] = value.strip()
                else:
                    # Handle existence selectors (just key)
                    labels[pair.strip()] = ''
                    
        except Exception as e:
            logging.debug(f"Error parsing label selector '{selector}': {e}")
        
        return labels
    
    @staticmethod
    def format_labels_for_display(labels: Dict[str, str], max_labels: int = 5) -> str:
        """Format labels dictionary for display"""
        if not labels:
            return '<none>'
        
        # Sort labels by key for consistent display
        sorted_labels = sorted(labels.items())
        
        if len(sorted_labels) <= max_labels:
            return ', '.join(f"{k}={v}" if v else k for k, v in sorted_labels)
        
        displayed = sorted_labels[:max_labels]
        remaining = len(sorted_labels) - max_labels
        
        label_strings = [f"{k}={v}" if v else k for k, v in displayed]
        
        return f"{', '.join(label_strings)} (+{remaining} more)"
    
    @staticmethod
    def calculate_usage_percentage(used: Union[str, float], total: Union[str, float]) -> Optional[float]:
        """Calculate usage percentage with error handling"""
        try:
            # Parse used value
            if isinstance(used, str):
                used_resource = HighPerformanceFormatters.parse_memory_value(used)
                used_val = used_resource.value
            else:
                used_val = float(used or 0)
            
            # Parse total value
            if isinstance(total, str):
                total_resource = HighPerformanceFormatters.parse_memory_value(total)
                total_val = total_resource.value
            else:
                total_val = float(total or 0)
            
            if total_val <= 0:
                return None
            
            percentage = (used_val / total_val) * 100
            return min(100.0, max(0.0, percentage))
            
        except (ValueError, TypeError, AttributeError):
            return None


# Global formatter instance for maximum performance
_formatter_instance = HighPerformanceFormatters()


# Convenience functions that use the optimized formatter
def format_age(timestamp: Optional[Union[str, datetime]]) -> str:
    """Format age for display"""
    if timestamp is None:
        return 'Unknown'
    
    if isinstance(timestamp, datetime):
        return _formatter_instance.format_age_from_datetime(timestamp)
    else:
        return _formatter_instance.format_age(str(timestamp))


def parse_cpu_value(cpu_str: str) -> ResourceUsage:
    """Parse CPU value"""
    return _formatter_instance.parse_cpu_value(cpu_str)


def parse_memory_value(memory_str: str) -> ResourceUsage:
    """Parse memory value"""
    return _formatter_instance.parse_memory_value(memory_str)


def format_percentage(value: Optional[float], precision: int = 1) -> str:
    """Format percentage with consistent precision"""
    return _formatter_instance.format_percentage(value, precision)


def format_resource_ratio(used: Union[str, int, float], total: Union[str, int, float]) -> str:
    """Format resource usage ratio"""
    return _formatter_instance.format_resource_ratio(used, total)


def format_duration(seconds: float) -> str:
    """Format duration"""
    return _formatter_instance.format_duration(seconds)


def format_status_with_color(status: str, status_mapping: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Format status with appropriate color coding"""
    return _formatter_instance.format_status_with_color(status, status_mapping)


def truncate_string(text: str, max_length: int = 50, suffix: str = '...') -> str:
    """Truncate string efficiently"""
    return _formatter_instance.truncate_string(text, max_length, suffix)


def format_list_display(items: List[str], max_items: int = 3, separator: str = ', ') -> str:
    """Format list for display with item limit"""
    return _formatter_instance.format_list_display(items, max_items, separator)


def parse_label_selector(selector: str) -> Dict[str, str]:
    """Parse Kubernetes label selector efficiently"""
    return _formatter_instance.parse_label_selector(selector)


def format_labels_for_display(labels: Dict[str, str], max_labels: int = 5) -> str:
    """Format labels dictionary for display"""
    return _formatter_instance.format_labels_for_display(labels, max_labels)


def calculate_usage_percentage(used: Union[str, float], total: Union[str, float]) -> Optional[float]:
    """Calculate usage percentage with error handling"""
    return _formatter_instance.calculate_usage_percentage(used, total)


# Performance monitoring functions removed (no more caching)