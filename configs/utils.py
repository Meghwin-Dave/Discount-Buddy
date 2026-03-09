import logging

logger = logging.getLogger(__name__)

def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings (e.g., "1.2.3" and "1.2.4").
    Returns:
        1: v1 > v2
        0: v1 == v2
        -1: v1 < v2
    """
    if not v1 and not v2: return 0
    if not v1: return -1
    if not v2: return 1

    try:
        v1_parts = [int(p) for p in v1.strip().split(".") if p.isdigit()]
        v2_parts = [int(p) for p in v2.strip().split(".") if p.isdigit()]
        
        # Normalize parts to at least 3 segments (major, minor, patch)
        while len(v1_parts) < 3: v1_parts.append(0)
        while len(v2_parts) < 3: v2_parts.append(0)

        for i in range(max(len(v1_parts), len(v2_parts))):
            p1 = v1_parts[i] if i < len(v1_parts) else 0
            p2 = v2_parts[i] if i < len(v2_parts) else 0
            if p1 > p2: return 1
            if p1 < p2: return -1
        return 0
    except (ValueError, AttributeError) as e:
        logger.error(f"Error comparing versions {v1} and {v2}: {e}")
        return 0

def is_less_than(v1: str, v2: str) -> bool: return compare_versions(v1, v2) < 0
def is_greater_than(v1: str, v2: str) -> bool: return compare_versions(v1, v2) > 0
