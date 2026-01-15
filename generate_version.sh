#!/bin/bash
# Generate VERSION file from git tags with semantic versioning
# This script creates a JSON file with complete version metadata

set -e

# Get build number from total commit count
BUILD_NUMBER=$(git rev-list --count HEAD 2>/dev/null || echo "0")

# Get git describe output
GIT_DESCRIBE=$(git describe --tags --always --dirty 2>/dev/null || echo "v0.0.0-dev${BUILD_NUMBER}")

# Check for dirty working directory
DIRTY=""
if [[ "$GIT_DESCRIBE" == *"-dirty" ]]; then
    DIRTY=".dirty"
    GIT_DESCRIBE="${GIT_DESCRIBE%-dirty}"
fi

# Extract short commit hash
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Parse git describe output
# Format: v1.0.0-beta.3 or v1.0.0-beta.3-2-gc6e425e
if [[ "$GIT_DESCRIBE" =~ ^v?([0-9]+\.[0-9]+\.[0-9]+)(-([a-zA-Z0-9.]+))?(-([0-9]+)-g([0-9a-f]+))?$ ]]; then
    VERSION="${BASH_REMATCH[1]}"
    PRERELEASE="${BASH_REMATCH[3]}"
    COMMITS_SINCE="${BASH_REMATCH[5]}"
    
    # Determine build type and full version
    if [ -n "$COMMITS_SINCE" ] && [ "$COMMITS_SINCE" -gt 0 ]; then
        # Development build (commits after tag)
        if [ -n "$PRERELEASE" ]; then
            BUILD_TYPE="prerelease-dev"
            FULL_VERSION="${VERSION}-${PRERELEASE}.dev${COMMITS_SINCE}${DIRTY}"
        else
            BUILD_TYPE="development"
            FULL_VERSION="${VERSION}.dev${COMMITS_SINCE}${DIRTY}"
        fi
    else
        # On a tag
        if [ -n "$PRERELEASE" ]; then
            BUILD_TYPE="prerelease"
            FULL_VERSION="${VERSION}-${PRERELEASE}${DIRTY}"
        else
            BUILD_TYPE="release"
            FULL_VERSION="${VERSION}${DIRTY}"
        fi
    fi
else
    # Fallback for no tags
    VERSION="0.0.0"
    PRERELEASE=""
    BUILD_TYPE="development"
    FULL_VERSION="0.0.0-dev${BUILD_NUMBER}${DIRTY}"
fi

# Create VERSION JSON file
if [ -n "$PRERELEASE" ]; then
    PRERELEASE_JSON="\"$PRERELEASE\""
else
    PRERELEASE_JSON="null"
fi

cat > VERSION <<EOF
{
  "version": "$VERSION",
  "prerelease": $PRERELEASE_JSON,
  "build_type": "$BUILD_TYPE",
  "build_number": $BUILD_NUMBER,
  "commit": "$COMMIT",
  "full_version": "$FULL_VERSION"
}
EOF

echo "Generated VERSION file:"
cat VERSION
