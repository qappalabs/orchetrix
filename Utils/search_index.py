"""
Resource Search Index - Efficient search for large datasets
Provides indexed search to replace O(n) linear search patterns
"""

import re
import threading
import time
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
import logging


@dataclass
class SearchResult:
    """Search result with scoring information"""
    row_index: int
    resource: Dict[str, Any]
    score: float  # Relevance score (0.0 to 1.0)
    matched_fields: List[str]  # Fields that matched the search


class ResourceSearchIndex:
    """
    Thread-safe search index for Kubernetes resources.
    Builds an inverted index for fast text search across large datasets.
    """
    
    def __init__(self, max_results: int = 1000):
        self.max_results = max_results
        self.index: Dict[str, Set[int]] = {}  # term -> set of row indices
        self.resources: List[Dict] = []
        self.searchable_fields: List[str] = []
        self._lock = threading.RLock()
        self._last_build = 0
        
        # Search statistics
        self.stats = {
            'builds': 0,
            'searches': 0,
            'index_size': 0,
            'avg_search_time': 0.0
        }
        
        logging.debug("ResourceSearchIndex initialized")
    
    def build_index(self, resources: List[Dict], searchable_fields: List[str]):
        """Build search index for resources"""
        build_start = time.time()
        
        with self._lock:
            self.resources = resources
            self.searchable_fields = searchable_fields
            self.index.clear()
            
            for i, resource in enumerate(resources):
                self._index_resource(i, resource)
            
            self._last_build = time.time()
            self.stats['builds'] += 1
            self.stats['index_size'] = len(self.index)
            
            build_time = time.time() - build_start
            logging.info(
                f"Search index built: {len(resources)} resources, "
                f"{len(self.index)} terms, {build_time:.3f}s"
            )
    
    def _index_resource(self, row_index: int, resource: Dict):
        """Index a single resource"""
        for field in self.searchable_fields:
            value = self._get_nested_value(resource, field)
            if value:
                terms = self._extract_terms(str(value).lower())
                for term in terms:
                    if term not in self.index:
                        self.index[term] = set()
                    self.index[term].add(row_index)
    
    def _get_nested_value(self, resource: Dict, field: str) -> Optional[str]:
        """Get nested value from resource using dot notation"""
        keys = field.split('.')
        value = resource
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def _extract_terms(self, text: str) -> List[str]:
        """Extract searchable terms from text"""
        # Split on word boundaries and filter out empty strings
        terms = re.findall(r'\w+', text)
        
        # Include both full terms and prefixes for partial matching
        all_terms = set(terms)
        
        # Add prefixes for terms longer than 2 characters
        for term in terms:
            if len(term) > 2:
                for i in range(3, len(term) + 1):
                    all_terms.add(term[:i])
        
        return list(all_terms)
    
    def search(self, query: str, max_results: Optional[int] = None) -> List[SearchResult]:
        """
        Search for query and return matching resources with scores.
        Supports multiple terms, phrase matching, and relevance scoring.
        """
        search_start = time.time()
        
        if not query.strip():
            return []
        
        max_results = max_results or self.max_results
        
        with self._lock:
            if not self.resources:
                return []
            
            # Parse query into terms
            query_terms = self._extract_query_terms(query.lower())
            if not query_terms:
                return []
            
            # Find matching resources
            matching_indices = self._find_matching_indices(query_terms)
            
            # Score and sort results
            scored_results = []
            for row_index in matching_indices:
                if row_index < len(self.resources):
                    resource = self.resources[row_index]
                    score, matched_fields = self._calculate_score(
                        resource, query_terms, query.lower()
                    )
                    
                    scored_results.append(SearchResult(
                        row_index=row_index,
                        resource=resource,
                        score=score,
                        matched_fields=matched_fields
                    ))
            
            # Sort by relevance score (highest first)
            scored_results.sort(key=lambda r: r.score, reverse=True)
            
            # Update statistics
            search_time = time.time() - search_start
            self.stats['searches'] += 1
            self.stats['avg_search_time'] = (
                (self.stats['avg_search_time'] * (self.stats['searches'] - 1) + search_time)
                / self.stats['searches']
            )
            
            logging.debug(
                f"Search completed: '{query}' -> {len(scored_results)} results "
                f"in {search_time:.3f}s"
            )
            
            return scored_results[:max_results]
    
    def _extract_query_terms(self, query: str) -> List[str]:
        """Extract terms from search query"""
        # Handle quoted phrases
        phrases = re.findall(r'"([^"]*)"', query)
        remaining_query = re.sub(r'"[^"]*"', '', query)
        
        # Extract individual terms
        terms = re.findall(r'\w+', remaining_query)
        
        # Combine phrases and terms
        all_terms = phrases + terms
        return [term for term in all_terms if len(term) > 0]
    
    def _find_matching_indices(self, query_terms: List[str]) -> Set[int]:
        """Find resource indices that match query terms"""
        if not query_terms:
            return set()
        
        # Start with matches for the first term
        first_term = query_terms[0]
        matching_indices = self._get_term_matches(first_term)
        
        # For multiple terms, find intersection (AND logic)
        for term in query_terms[1:]:
            term_matches = self._get_term_matches(term)
            matching_indices &= term_matches
            
            # Early termination if no matches
            if not matching_indices:
                break
        
        return matching_indices
    
    def _get_term_matches(self, term: str) -> Set[int]:
        """Get all resource indices that match a term (including partial matches)"""
        matches = set()
        
        # Exact matches
        if term in self.index:
            matches.update(self.index[term])
        
        # Prefix matches for partial search
        for indexed_term in self.index:
            if indexed_term.startswith(term):
                matches.update(self.index[indexed_term])
        
        return matches
    
    def _calculate_score(self, resource: Dict, query_terms: List[str], 
                        original_query: str) -> tuple[float, List[str]]:
        """Calculate relevance score for a resource"""
        score = 0.0
        matched_fields = []
        
        # Field importance weights
        field_weights = {
            'name': 3.0,
            'namespace': 2.0,
            'status': 2.5,
            'message': 1.5,
            'reason': 2.0,
            'type': 2.0
        }
        
        for field in self.searchable_fields:
            value = self._get_nested_value(resource, field)
            if not value:
                continue
            
            value_lower = str(value).lower()
            field_score = 0.0
            
            # Check for exact phrase match (highest score)
            if original_query in value_lower:
                field_score += 5.0
                matched_fields.append(field)
            
            # Check for individual term matches
            for term in query_terms:
                if term in value_lower:
                    field_score += 1.0
                    if field not in matched_fields:
                        matched_fields.append(field)
                    
                    # Bonus for exact word boundaries
                    if re.search(r'\b' + re.escape(term) + r'\b', value_lower):
                        field_score += 0.5
                    
                    # Bonus for matches at the beginning
                    if value_lower.startswith(term):
                        field_score += 1.0
            
            # Apply field weight
            weight = field_weights.get(field.split('.')[-1], 1.0)
            score += field_score * weight
        
        # Normalize score (0.0 to 1.0)
        max_possible_score = len(query_terms) * 7.5 * 3.0  # Rough estimate
        normalized_score = min(score / max_possible_score, 1.0) if max_possible_score > 0 else 0.0
        
        return normalized_score, matched_fields
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search index statistics"""
        with self._lock:
            return {
                **self.stats,
                'resources_count': len(self.resources),
                'last_build_time': self._last_build,
                'fields_indexed': self.searchable_fields.copy()
            }
    
    def update_resource(self, row_index: int, resource: Dict):
        """Update a single resource in the index"""
        with self._lock:
            if 0 <= row_index < len(self.resources):
                # Remove old index entries for this resource
                self._remove_resource_from_index(row_index)
                
                # Update resource and re-index
                self.resources[row_index] = resource
                self._index_resource(row_index, resource)
    
    def _remove_resource_from_index(self, row_index: int):
        """Remove a resource from the search index"""
        terms_to_clean = []
        for term, indices in self.index.items():
            if row_index in indices:
                indices.discard(row_index)
                if not indices:  # Remove empty term entries
                    terms_to_clean.append(term)
        
        for term in terms_to_clean:
            del self.index[term]
    
    def clear(self):
        """Clear the entire search index"""
        with self._lock:
            self.index.clear()
            self.resources.clear()
            self.searchable_fields.clear()
            self.stats = {
                'builds': 0,
                'searches': 0, 
                'index_size': 0,
                'avg_search_time': 0.0
            }
            logging.debug("Search index cleared")


# Global search index instances for different resource types
_search_indexes: Dict[str, ResourceSearchIndex] = {}
_indexes_lock = threading.Lock()


def get_search_index(resource_type: str) -> ResourceSearchIndex:
    """Get or create a search index for a resource type"""
    with _indexes_lock:
        if resource_type not in _search_indexes:
            _search_indexes[resource_type] = ResourceSearchIndex()
        return _search_indexes[resource_type]


def clear_all_search_indexes():
    """Clear all search indexes"""
    with _indexes_lock:
        for index in _search_indexes.values():
            index.clear()
        _search_indexes.clear()
        logging.info("All search indexes cleared")


def get_search_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all search indexes"""
    with _indexes_lock:
        return {
            resource_type: index.get_stats() 
            for resource_type, index in _search_indexes.items()
        }