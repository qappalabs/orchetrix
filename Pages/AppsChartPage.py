"""
Apps Chart Page - Refactored modular architecture
Split into focused components for better maintainability and performance
"""

# Import all functionality from the new modular components
from .apps_chart.deployment_analyzer import DeploymentAnalyzer
from .apps_chart.app_flow_analyzer import AppFlowAnalyzer
from .apps_chart.apps_page import AppsPage

# Export all classes for backward compatibility
__all__ = [
    'DeploymentAnalyzer',
    'AppFlowAnalyzer',
    'AppsPage'
]