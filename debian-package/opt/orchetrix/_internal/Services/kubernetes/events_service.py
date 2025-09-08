"""
Kubernetes Events Service - Handles cluster events and issues processing
Split from kubernetes_client.py for better architecture
"""

import logging
from datetime import datetime
from functools import lru_cache
from typing import Dict, Any, List, Optional
from kubernetes.client.rest import ApiException

# Event configuration constants
EVENT_BATCH_SIZE = 100
MAX_ISSUES_RETURNED = 50
EVENT_MAX_AGE_HOURS = 24


class KubernetesEventsService:
    """Service for managing Kubernetes events and issues"""
    
    def __init__(self, api_service, cache_service):
        self.api_service = api_service
        self.cache_service = cache_service
        logging.debug("KubernetesEventsService initialized")
    
    def get_cluster_issues(self, cluster_name: str) -> List[Dict[str, Any]]:
        """Get cluster issues with real data and improved filtering"""
        # Check cache first
        cached_issues = self.cache_service.get_cached_resources('issues', f'cluster_{cluster_name}')
        if cached_issues:
            logging.debug(f"Using cached issues for {cluster_name}")
            return cached_issues
        
        try:
            issues = []
            
            # Get events efficiently with field selector for non-normal events
            try:
                events_list = self.api_service.v1.list_event_for_all_namespaces(
                    field_selector="type!=Normal",
                    limit=EVENT_BATCH_SIZE
                )
            except Exception as e:
                logging.warning(f"Failed to get events with field selector, trying without: {e}")
                events_list = self.api_service.v1.list_event_for_all_namespaces(limit=EVENT_BATCH_SIZE)
            
            # Process events and filter for actual issues
            for event in events_list.items:
                # Skip normal events if they got through
                if event.type == "Normal":
                    continue
                
                # Filter for recent events (last 24 hours)
                if event.metadata.creation_timestamp:
                    event_time = event.metadata.creation_timestamp
                    now = datetime.now(event_time.tzinfo) if event_time.tzinfo else datetime.now()
                    age_hours = (now - event_time).total_seconds() / 3600
                    
                    # Only include events from last 24 hours
                    if age_hours > EVENT_MAX_AGE_HOURS:
                        continue
                
                # Create issue object
                issue = {
                    "type": event.type or "Warning",
                    "reason": event.reason or "Unknown",
                    "message": (event.message or "No message")[:200],  # Truncate long messages
                    "object": f"{event.involved_object.kind}/{event.involved_object.name}" if event.involved_object else "Unknown",
                    "age": self._format_age(event.metadata.creation_timestamp) if event.metadata.creation_timestamp else "Unknown",
                    "namespace": event.metadata.namespace or "default"
                }
                
                issues.append(issue)
            
            # Sort by most recent first
            issues.sort(key=lambda x: x.get("age", ""), reverse=False)
            
            # Limit to most recent issues
            issues = issues[:MAX_ISSUES_RETURNED]
            
            # Cache the results
            self.cache_service.cache_resources('issues', f'cluster_{cluster_name}', issues)
            
            logging.info(f"Found {len(issues)} real cluster issues")
            return issues
            
        except Exception as e:
            logging.error(f"Error getting cluster issues: {e}")
            return []
    
    def get_events_for_resource(self, resource_type: str, resource_name: str, 
                               namespace: str = "default") -> List[Dict[str, Any]]:
        """Get events for a specific resource"""
        try:
            # Get events for the specific resource
            field_selector = f"involvedObject.kind={resource_type},involvedObject.name={resource_name}"
            
            if namespace != "default":
                events_list = self.api_service.v1.list_namespaced_event(
                    namespace=namespace,
                    field_selector=field_selector,
                    limit=50
                )
            else:
                events_list = self.api_service.v1.list_event_for_all_namespaces(
                    field_selector=field_selector,
                    limit=50
                )
            
            events = []
            for event in events_list.items:
                event_data = {
                    "type": event.type or "Normal",
                    "reason": event.reason or "Unknown",
                    "message": event.message or "No message",
                    "first_timestamp": event.first_timestamp,
                    "last_timestamp": event.last_timestamp,
                    "count": event.count or 1,
                    "age": self._format_age(event.metadata.creation_timestamp) if event.metadata.creation_timestamp else "Unknown",
                    "namespace": event.metadata.namespace or namespace
                }
                events.append(event_data)
            
            # Sort by most recent first
            events.sort(key=lambda x: x.get("last_timestamp", x.get("first_timestamp", datetime.min)), reverse=True)
            
            logging.debug(f"Found {len(events)} events for {resource_type}/{resource_name}")
            return events
            
        except ApiException as e:
            logging.error(f"API error getting events for {resource_type}/{resource_name}: {e}")
            return []
        except Exception as e:
            logging.error(f"Error getting events for {resource_type}/{resource_name}: {e}")
            return []
    
    def get_namespace_events(self, namespace: str, event_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get events for a specific namespace"""
        try:
            # Build field selector for event types if specified
            field_selector = None
            if event_types:
                type_filters = [f"type={event_type}" for event_type in event_types]
                field_selector = ",".join(type_filters)
            
            events_list = self.api_service.v1.list_namespaced_event(
                namespace=namespace,
                field_selector=field_selector,
                limit=EVENT_BATCH_SIZE
            )
            
            events = []
            for event in events_list.items:
                # Filter for recent events
                if event.metadata.creation_timestamp:
                    event_time = event.metadata.creation_timestamp
                    now = datetime.now(event_time.tzinfo) if event_time.tzinfo else datetime.now()
                    age_hours = (now - event_time).total_seconds() / 3600
                    
                    if age_hours > EVENT_MAX_AGE_HOURS:
                        continue
                
                event_data = {
                    "type": event.type or "Normal",
                    "reason": event.reason or "Unknown",
                    "message": (event.message or "No message")[:200],
                    "object": f"{event.involved_object.kind}/{event.involved_object.name}" if event.involved_object else "Unknown",
                    "age": self._format_age(event.metadata.creation_timestamp) if event.metadata.creation_timestamp else "Unknown",
                    "count": event.count or 1,
                    "namespace": namespace
                }
                events.append(event_data)
            
            # Sort by most recent first
            events.sort(key=lambda x: x.get("age", ""), reverse=False)
            
            logging.debug(f"Found {len(events)} events in namespace {namespace}")
            return events
            
        except ApiException as e:
            logging.error(f"API error getting events for namespace {namespace}: {e}")
            return []
        except Exception as e:
            logging.error(f"Error getting events for namespace {namespace}: {e}")
            return []
    
    def get_critical_events(self, cluster_name: str) -> List[Dict[str, Any]]:
        """Get only critical/error events"""
        try:
            # Get events with error/warning types
            events_list = self.api_service.v1.list_event_for_all_namespaces(
                field_selector="type=Warning",
                limit=EVENT_BATCH_SIZE * 2  # Get more to filter for critical ones
            )
            
            critical_events = []
            critical_reasons = [
                "Failed", "FailedMount", "FailedScheduling", "FailedCreate", 
                "FailedDelete", "FailedUpdate", "Unhealthy", "BackOff",
                "FailedSync", "NetworkNotReady", "NodeNotReady"
            ]
            
            for event in events_list.items:
                # Filter for critical reasons
                if not any(reason in (event.reason or "") for reason in critical_reasons):
                    continue
                
                # Filter for recent events
                if event.metadata.creation_timestamp:
                    event_time = event.metadata.creation_timestamp
                    now = datetime.now(event_time.tzinfo) if event_time.tzinfo else datetime.now()
                    age_hours = (now - event_time).total_seconds() / 3600
                    
                    if age_hours > EVENT_MAX_AGE_HOURS:
                        continue
                
                critical_event = {
                    "type": event.type or "Warning",
                    "reason": event.reason or "Unknown",
                    "message": (event.message or "No message")[:200],
                    "object": f"{event.involved_object.kind}/{event.involved_object.name}" if event.involved_object else "Unknown",
                    "age": self._format_age(event.metadata.creation_timestamp) if event.metadata.creation_timestamp else "Unknown",
                    "namespace": event.metadata.namespace or "default",
                    "severity": "critical"
                }
                critical_events.append(critical_event)
            
            # Sort by most recent first and limit
            critical_events.sort(key=lambda x: x.get("age", ""), reverse=False)
            critical_events = critical_events[:25]  # Limit to 25 most critical
            
            logging.info(f"Found {len(critical_events)} critical events")
            return critical_events
            
        except Exception as e:
            logging.error(f"Error getting critical events: {e}")
            return []
    
    @lru_cache(maxsize=256)
    def _format_age(self, timestamp) -> str:
        """Format age with caching"""
        if not timestamp:
            return "Unknown"
        
        try:
            if isinstance(timestamp, str):
                created = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                created = timestamp
            
            now = datetime.now(created.tzinfo or datetime.now().astimezone().tzinfo)
            diff = now - created
            
            if diff.days > 0:
                return f"{diff.days}d"
            elif diff.seconds >= 3600:
                return f"{diff.seconds // 3600}h"
            else:
                return f"{diff.seconds // 60}m"
                
        except (ValueError, TypeError, AttributeError) as e:
            logging.debug(f"Error calculating event age: {e}")
            return "Unknown"
        except Exception as e:
            logging.error(f"Unexpected error calculating event age: {e}")
            return "Unknown"
    
    def get_event_summary(self, cluster_name: str) -> Dict[str, Any]:
        """Get a summary of events by type and severity"""
        try:
            events_list = self.api_service.v1.list_event_for_all_namespaces(
                limit=EVENT_BATCH_SIZE * 3  # Get more events for summary
            )
            
            summary = {
                "total_events": 0,
                "warning_count": 0,
                "normal_count": 0,
                "recent_events": 0,  # Events in last hour
                "top_reasons": {},
                "namespaces_with_issues": set()
            }
            
            now = datetime.now()
            
            for event in events_list.items:
                summary["total_events"] += 1
                
                # Count by type
                if event.type == "Warning":
                    summary["warning_count"] += 1
                    if event.metadata.namespace:
                        summary["namespaces_with_issues"].add(event.metadata.namespace)
                else:
                    summary["normal_count"] += 1
                
                # Count recent events (last hour)
                if event.metadata.creation_timestamp:
                    event_time = event.metadata.creation_timestamp
                    age_hours = (now - event_time.replace(tzinfo=None) if event_time.tzinfo else event_time).total_seconds() / 3600
                    if age_hours <= 1:
                        summary["recent_events"] += 1
                
                # Count top reasons
                reason = event.reason or "Unknown"
                summary["top_reasons"][reason] = summary["top_reasons"].get(reason, 0) + 1
            
            # Convert set to list for JSON serialization
            summary["namespaces_with_issues"] = list(summary["namespaces_with_issues"])
            
            # Get top 5 reasons
            summary["top_reasons"] = dict(sorted(summary["top_reasons"].items(), 
                                               key=lambda x: x[1], reverse=True)[:5])
            
            logging.debug(f"Event summary: {summary['warning_count']} warnings, {summary['normal_count']} normal")
            return summary
            
        except Exception as e:
            logging.error(f"Error getting event summary: {e}")
            return {
                "total_events": 0,
                "warning_count": 0,
                "normal_count": 0,
                "recent_events": 0,
                "top_reasons": {},
                "namespaces_with_issues": []
            }
    
    def clear_cache(self):
        """Clear all cached formatting results"""
        self._format_age.cache_clear()
        logging.debug("Cleared events formatting cache")
    
    def cleanup(self):
        """Cleanup events service resources"""
        logging.debug("Cleaning up KubernetesEventsService")
        self.clear_cache()
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            if hasattr(self, '_format_age'):
                self.cleanup()
        except Exception as e:
            logging.error(f"Error in KubernetesEventsService destructor: {e}")


# Factory function
def create_kubernetes_events_service(api_service, cache_service) -> KubernetesEventsService:
    """Create a new Kubernetes events service instance"""
    return KubernetesEventsService(api_service, cache_service)