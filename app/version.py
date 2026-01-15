"""
Version information

Version is read from a VERSION file.
Generate the VERSION file using ./generate_version.sh before running the application.
The version follows semantic versioning (MAJOR.MINOR.PATCH).
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dunebugger_settings import settings

logger = logging.getLogger(__name__)


def _load_version_from_file() -> Optional[Dict[str, Any]]:
    """
    Load version information from the VERSION file.
    
    Returns:
        Dictionary with version data if successful, None otherwise.
    """
    try:
        version_file = Path(__file__).parent.parent / "VERSION"
        if not version_file.exists():
            logger.warning(f"VERSION file not found at {version_file}")
            return None
            
        content = version_file.read_text().strip()
        version_data = json.loads(content)
        logger.debug(f"Successfully loaded version from {version_file}")
        return version_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse VERSION file as JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error reading VERSION file: {e}")
        return None


def _create_version_info(version_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a complete version info dictionary.
    
    Args:
        version_data: Optional dictionary with version data from VERSION file.
        
    Returns:
        Dictionary with all version fields populated.
    """
    if version_data is None:
        version_data = {}
    
    return {
        "component": settings.mQueueClientID,
        "version": version_data.get("version", "0.0.0"),
        "prerelease": version_data.get("prerelease"),
        "build_type": version_data.get("build_type", "unknown"),
        "build_number": version_data.get("build_number", 0),
        "commit": version_data.get("commit", "unknown"),
        "full_version": version_data.get("full_version", "0.0.0-unknown")
    }


# Load version information at module initialization
_version_data = _load_version_from_file()
_version_info = _create_version_info(_version_data)


def get_version_info() -> Dict[str, Any]:
    """
    Return a dictionary with complete version information.
    
    Returns:
        Dictionary containing:
            - component: Component identifier from settings
            - version: Semantic version (MAJOR.MINOR.PATCH)
            - prerelease: Pre-release identifier (e.g., 'beta.1') or None
            - build_type: Type of build (e.g., 'release', 'prerelease')
            - build_number: Build number
            - commit: Git commit hash
            - full_version: Complete version string
    """
    return _version_info
