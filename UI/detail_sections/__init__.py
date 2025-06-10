"""
Detail sections package for Kubernetes DetailPage component
"""

from .base_detail_section import BaseDetailSection
from .detailpage_overviewsection import DetailPageOverviewSection
from .detailpage_detailsection import DetailPageDetailsSection
from .detailpage_yamlsection import DetailPageYAMLSection
from .detailpage_eventssection import DetailPageEventsSection

__all__ = [
    'BaseDetailSection',
    'DetailPageOverviewSection',
    'DetailPageDetailsSection',
    'DetailPageYAMLSection',
    'DetailPageEventsSection'
]