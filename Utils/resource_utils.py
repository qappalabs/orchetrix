"""
Utility functions for resource type handling.
"""

# Hard-coded exceptions map for irregular plurals
IRREGULAR_PLURALS = {
    "ingresses": "ingress",
    "indices": "index",
    "addresses": "address",
    "classes": "class",
    "statuses": "status",
    "processes": "process",
    "accesses": "access",
    "namespaces": "namespace",
    "policies": "policy",
    "entries": "entry",
    "registries": "registry",
    "repositories": "repository",
    "inventories": "inventory",
    "categories": "category",
}

# Words that are already singular but end in 's'
# These should not be modified
SINGULAR_WORDS_ENDING_IN_S = frozenset({
    "ingress",
    "address",
    "class",
    "status",
    "process",
    "access",
    "namespace",
    "atlas",
    "alias",
    "basis",
    "canvas",
    "chaos",
    "consensus",
    "corpus",
    "diagnosis",
    "synopsis",
    "analysis",
    "axis",
    "thesis",
    "iris",
    "gas",
    "bus",
})


def _apply_casing(source: str, target: str) -> str:
    """
    Apply the casing pattern from source string to target string.

    Matches casing character-by-character where possible. For characters
    in target beyond source's length, uses the predominant case pattern
    from source.
    """
    if not source or not target:
        return target

    result = []
    for i, char in enumerate(target):
        if i < len(source):
            # Apply casing from corresponding source character
            if source[i].isupper():
                result.append(char.upper())
            else:
                result.append(char.lower())
        else:
            # Beyond source length: use predominant case from source
            if source.isupper():
                result.append(char.upper())
            else:
                result.append(char.lower())
    return ''.join(result)


def singularize_resource_type(resource_type: str) -> str:
    """
    Convert a plural resource type to its singular form.

    First checks a hard-coded exceptions map for irregular plurals,
    then checks if the word is already singular (ends in 's' but is singular),
    then applies pattern-based rules for common plural endings.

    Args:
        resource_type: The plural resource type string

    Returns:
        The singular form of the resource type
    """
    if not resource_type:
        return resource_type

    # Convert to lowercase for consistent lookup
    lower_type = resource_type.lower()

    # Check exceptions map first
    if lower_type in IRREGULAR_PLURALS:
        singular = IRREGULAR_PLURALS[lower_type]
        # Preserve original casing pattern character-by-character
        return _apply_casing(resource_type, singular)

    # Check if already singular (words ending in 's' that are singular)
    if lower_type in SINGULAR_WORDS_ENDING_IN_S:
        return resource_type

    # Handle -ies -> -y (e.g., "policies" -> "policy")
    if lower_type.endswith('ies') and len(lower_type) > 3:
        return resource_type[:-3] + 'y'

    # Handle -sses -> -ss (e.g., "addresses" -> "address" - backup if not in map)
    if lower_type.endswith('sses'):
        return resource_type[:-2]

    # Handle -xes -> -x (e.g., "boxes" -> "box")
    if lower_type.endswith('xes'):
        return resource_type[:-2]

    # Handle -ches -> -ch (e.g., "patches" -> "patch")
    if lower_type.endswith('ches'):
        return resource_type[:-2]

    # Handle -shes -> -sh (e.g., "meshes" -> "mesh")
    if lower_type.endswith('shes'):
        return resource_type[:-2]

    # Simple rule: remove trailing 's' if present
    if lower_type.endswith('s'):
        return resource_type[:-1]

    # If no 's' at end, assume it's already singular
    return resource_type
