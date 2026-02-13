"""
High-Performance Data Formatters and Utilities
Consolidates scattered formatting functions into optimized utilities.
Designed for maximum performance and consistent formatting across the app.
"""

import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Union, Optional
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
    # Pattern requires: number, then optional (letter from KMGTPE optionally followed by 'i')
    # This ensures 'i' is never matched alone
    _MEMORY_PATTERN = re.compile(r'^(\d+(?:\.\d+)?)([KMGTPE]i?)?$')

    @staticmethod
    def _format_age_from_timedelta(age_delta: timedelta) -> str:
        """Format age from timedelta - eliminates datetime string conversion overhead"""
        try:
            # Format efficiently from timedelta
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
            logging.debug(f"Error formatting age from timedelta: {e}")
            return 'Unknown'

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

            # Calculate age and format
            now = datetime.now(timezone.utc)
            age_delta = now - created

            return HighPerformanceFormatters._format_age_from_timedelta(age_delta)

        except Exception as e:
            logging.debug(f"Error formatting age for '{timestamp_str}': {e}")
            return 'Unknown'

    @staticmethod
    def format_age_from_datetime(dt: Optional[datetime]) -> str:
        """Format age from datetime object - direct computation without string conversion"""
        if not dt:
            return 'Unknown'

        try:
            # Ensure timezone aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            # Compute age directly as timedelta, bypassing string conversion
            now = datetime.now(timezone.utc)
            age_delta = now - dt

            return HighPerformanceFormatters._format_age_from_timedelta(age_delta)
        except Exception as e:
            logging.debug(f"Error formatting age from datetime: {e}")
            return 'Unknown'

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

            # Normalize unit: None (no unit captured) becomes empty string for lookup
            if unit is None:
                unit = ''

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
    def truncate_string(text: str, max_length: int = 50, suffix: str = '...') -> str:
        """Truncate string with performance optimization"""
        if not text or len(text) <= max_length:
            return text

        # Guard against negative slice index: if suffix is too long for max_length,
        # return truncated suffix instead
        if max_length <= len(suffix):
            return suffix[:max_length]

        return text[:max_length - len(suffix)] + suffix


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


def parse_memory_value(memory_str: str) -> ResourceUsage:
    """Parse memory value"""
    return _formatter_instance.parse_memory_value(memory_str)


def format_percentage(value: Optional[float], precision: int = 1) -> str:
    """Format percentage with consistent precision"""
    return _formatter_instance.format_percentage(value, precision)


def truncate_string(text: str, max_length: int = 50, suffix: str = '...') -> str:
    """Truncate string efficiently"""
    return _formatter_instance.truncate_string(text, max_length, suffix)


# Pre-compiled pattern for age parsing - matches number+suffix pairs
_AGE_PATTERN = re.compile(r'(\d+)(mo|[ydhms])')


def parse_age_to_seconds(age_str: str) -> int:
    """Parse a Kubernetes age string to total seconds for sorting.

    Handles single-unit ('5d', '12h') and compound ('5d2h30m') formats,
    plus 'y' (years) and 'mo' (months) produced by format_age().
    Returns 0 for invalid or empty input.
    """
    if not age_str or not isinstance(age_str, str):
        return 0

    multipliers = {
        'y': 365 * 86400,
        'mo': 30 * 86400,
        'd': 86400,
        'h': 3600,
        'm': 60,
        's': 1,
    }

    total = 0
    for value_str, unit in _AGE_PATTERN.findall(age_str):
        try:
            total += int(value_str) * multipliers.get(unit, 0)
        except ValueError:
            continue

    return total
