from typing import Tuple

def parse_semver(ver_str: str) -> Tuple:
    """
    Parse semantic version into comparable tuple.
    
    Args:
        ver_str: Version string like "1.0.0" or "1.0.0-beta.2"
        
    Returns:
        Tuple that can be compared: (base_version_tuple, is_release, prerelease_tuple)
        
    Examples:
        "1.0.0"         -> ((1, 0, 0), 1, None)
        "1.0.0-beta.3"  -> ((1, 0, 0), 0, ("beta", 3))
        "2.1.5-alpha.1" -> ((2, 1, 5), 0, ("alpha", 1))
    
    Comparison rules:
        - Release versions > prerelease versions
        - 1.0.0 > 1.0.0-beta.3
        - 1.0.0-beta.3 > 1.0.0-beta.2
    """
    # Split into base version and prerelease
    if '-' in ver_str:
        base, pre = ver_str.split('-', 1)
    else:
        base, pre = ver_str, None
    
    # Parse base version (e.g., "1.0.0" -> (1, 0, 0))
    try:
        base_parts = tuple(int(x) for x in base.split('.'))
    except ValueError:
        # Fallback for malformed versions
        base_parts = (0, 0, 0)
    
    # Prerelease versions are "less than" release versions
    # Examples: beta.2 < beta.3 < release
    if pre:
        # Parse prerelease (e.g., "beta.2" -> ("beta", 2))
        # Remove any .dev or .dirty suffixes for comparison
        pre_clean = pre.split('.dev')[0].split('.dirty')[0]
        
        if '.' in pre_clean:
            pre_name, pre_num = pre_clean.rsplit('.', 1)
            try:
                pre_tuple = (pre_name, int(pre_num))
            except ValueError:
                pre_tuple = (pre_clean, 0)
        else:
            pre_tuple = (pre_clean, 0)
        return (base_parts, 0, pre_tuple)  # 0 means prerelease
    else:
        return (base_parts, 1, None)  # 1 means release