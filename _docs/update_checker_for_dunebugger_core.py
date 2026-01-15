"""
Update checker for dunebugger.

Checks GitHub releases for updates and compares versions.
"""

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    
from version import get_version_info
import json


def parse_semver(ver_str):
    """
    Parse semantic version into comparable tuple.
    
    Args:
        ver_str: Version string like "1.0.0" or "1.0.0-beta.2"
        
    Returns:
        Tuple that can be compared: (base_version_tuple, is_release, prerelease_tuple)
    """
    # Split into base version and prerelease
    if '-' in ver_str:
        base, pre = ver_str.split('-', 1)
    else:
        base, pre = ver_str, None
    
    # Parse base version (e.g., "1.0.0" -> (1, 0, 0))
    base_parts = tuple(int(x) for x in base.split('.'))
    
    # Prerelease versions are "less than" release versions
    # Examples: beta.2 < beta.3 < release
    if pre:
        # Parse prerelease (e.g., "beta.2" -> ("beta", 2))
        if '.' in pre:
            pre_name, pre_num = pre.rsplit('.', 1)
            try:
                pre_tuple = (pre_name, int(pre_num))
            except ValueError:
                pre_tuple = (pre, 0)
        else:
            pre_tuple = (pre, 0)
        return (base_parts, 0, pre_tuple)  # 0 means prerelease
    else:
        return (base_parts, 1, None)  # 1 means release


class UpdateChecker:
    """Check for updates from GitHub releases."""
    
    def __init__(self, owner="marco-svitol", repo="dunebugger"):
        self.owner = owner
        self.repo = repo
        self.api_base = f"https://api.github.com/repos/{owner}/{repo}"
    
    def get_latest_release(self, include_prereleases=True):
        """
        Get the latest release from GitHub.
        
        Args:
            include_prereleases: If True, include beta/prerelease versions
            
        Returns:
            dict with release info or None if no releases found
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for update checking. Install with: pip install requests")
        
        try:
            # Get all releases
            url = f"{self.api_base}/releases"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            releases = response.json()
            if not releases:
                return None
            
            # Filter prereleases if needed
            if not include_prereleases:
                releases = [r for r in releases if not r.get('prerelease', False)]
            
            # Return the first (latest) release
            return releases[0] if releases else None
            
        except Exception as e:
            print(f"Error fetching releases: {e}")
            return None
    
    def get_version_info_from_release(self, release):
        """
        Extract version info from a GitHub release.
        
        First tries to download VERSION.json from release assets.
        Falls back to parsing the tag_name.
        
        Args:
            release: GitHub release dict from API
            
        Returns:
            dict with version info (compatible with get_version_info())
        """
        # Try to get VERSION.json from release assets
        for asset in release.get('assets', []):
            if asset['name'] == 'VERSION.json':
                try:
                    response = requests.get(asset['browser_download_url'], timeout=10)
                    response.raise_for_status()
                    return response.json()
                except Exception as e:
                    print(f"Error downloading VERSION.json: {e}")
                    break
        
        # Fallback: parse tag_name
        tag_name = release.get('tag_name', '').lstrip('v')
        is_prerelease = release.get('prerelease', False)
        
        # Parse version
        if '-' in tag_name:
            parts = tag_name.split('-', 1)
            version = parts[0]
            prerelease = parts[1]
        else:
            version = tag_name
            prerelease = None
        
        return {
            'version': version,
            'prerelease': prerelease,
            'build_type': 'prerelease' if is_prerelease else 'release',
            'build_number': 0,  # Unknown from tag alone
            'commit': 'unknown',
            'full_version': tag_name
        }
    
    def compare_versions(self, local_info, remote_info):
        """
        Compare local and remote versions.
        
        Args:
            local_info: dict from get_version_info()
            remote_info: dict from get_version_info_from_release()
            
        Returns:
            int: -1 if local is older, 0 if same, 1 if local is newer
        """
        # Build semantic version strings (without build numbers)
        def make_semver(info):
            if info.get('prerelease'):
                return f"{info['version']}-{info['prerelease']}"
            return info['version']
        
        local_semver = make_semver(local_info)
        remote_semver = make_semver(remote_info)
        
        local_parsed = parse_semver(local_semver)
        remote_parsed = parse_semver(remote_semver)
        
        if local_parsed < remote_parsed:
            return -1
        elif local_parsed > remote_parsed:
            return 1
        else:
            # Same semantic version - compare build numbers if available
            local_build = local_info.get('build_number', 0)
            remote_build = remote_info.get('build_number', 0)
            
            if remote_build > 0 and local_build < remote_build:
                return -1
            elif remote_build > 0 and local_build > remote_build:
                return 1
            
            return 0
    
    def check_for_updates(self, include_prereleases=True):
        """
        Check if an update is available.
        
        Args:
            include_prereleases: If True, include beta/prerelease versions
            
        Returns:
            dict with:
                - has_update: bool
                - local_version: dict
                - remote_version: dict or None
                - download_url: str or None
        """
        local_info = get_version_info()
        
        # Get latest release from GitHub
        release = self.get_latest_release(include_prereleases)
        if not release:
            return {
                'has_update': False,
                'local_version': local_info,
                'remote_version': None,
                'download_url': None
            }
        
        remote_info = self.get_version_info_from_release(release)
        comparison = self.compare_versions(local_info, remote_info)
        
        # Find tarball asset
        download_url = None
        for asset in release.get('assets', []):
            if asset['name'].endswith('.tar.gz') and 'sha256' not in asset['name']:
                download_url = asset['browser_download_url']
                break
        
        return {
            'has_update': comparison < 0,
            'local_version': local_info,
            'remote_version': remote_info,
            'download_url': download_url,
            'release_notes': release.get('body', ''),
            'published_at': release.get('published_at', '')
        }


# Example usage
if __name__ == "__main__":
    checker = UpdateChecker()
    
    print("Current version:")
    local = get_version_info()
    print(json.dumps(local, indent=2))
    print()
    
    print("Checking for updates (including prereleases)...")
    result = checker.check_for_updates(include_prereleases=True)
    
    print(f"\nHas update: {result['has_update']}")
    if result['remote_version']:
        print(f"Remote version: {result['remote_version']['full_version']}")
        if result['has_update']:
            print(f"Download URL: {result['download_url']}")
