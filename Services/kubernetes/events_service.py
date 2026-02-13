"""
Kubernetes Events Service - Handles cluster events and issues processing
Split from kubernetes_client.py for better architecture
"""

import logging
from datetime import datetime
from typing import Dict, Any, List
from kubernetes.client.rest import ApiException

# Event configuration constants
EVENT_BATCH_SIZE = 100
MAX_ISSUES_RETURNED = 50
EVENT_MAX_AGE_HOURS = 24


class KubernetesEventsService:
    """Service for managing Kubernetes events and issues"""

    def __init__(self, api_service):
        self.api_service = api_service
        logging.debug("KubernetesEventsService initialized")

    def get_cluster_issues(self, cluster_name: str) -> List[Dict[str, Any]]:
        """Get cluster issues with real data and improved filtering"""

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

    def _format_age(self, timestamp) -> str:
        """Format age"""
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

    def clear_cache(self):
        """Clear all cached formatting results"""
        # No caching is implemented in this service
        logging.debug("No cache to clear for events formatting")

    def cleanup(self):
        """Cleanup events service resources"""
        logging.debug("Cleaning up KubernetesEventsService")
        self.clear_cache()


# Factory function
def create_kubernetes_events_service(api_service) -> KubernetesEventsService:
    """Create a new Kubernetes events service instance"""
    return KubernetesEventsService(api_service)
