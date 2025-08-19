"""
Apps Chart Page - Refactored modular architecture
Split into focused components for better maintainability and performance
"""

# Import all functionality from the new modular components
from .AppsChart.deployment_analyzer import DeploymentAnalyzer
from .AppsChart.app_flow_analyzer import AppFlowAnalyzer
from .AppsChart.apps_page import AppsPage

# Export all classes for backward compatibility
__all__ = [
    'DeploymentAnalyzer',
    'AppFlowAnalyzer',
    'AppsPage'
]