#!/bin/bash

# Script to manage Docker secrets safely
# Usage: ./manage-secrets.sh [create|update|remove] [secret_name] [secret_value]

set -euo pipefail

SECRETS_DIR="./secrets"
SECRET_NAME="$2"
SECRET_VALUE="${3:-}"

# Create secrets directory if it doesn't exist
mkdir -p "$SECRETS_DIR"

case "$1" in
    "create"|"update")
        if [ -z "$SECRET_VALUE" ]; then
            echo "Please provide a secret value"
            echo "Usage: $0 create|update <secret_name> <secret_value>"
            exit 1
        fi
        
        echo "Creating/updating secret: $SECRET_NAME"
        echo -n "$SECRET_VALUE" > "$SECRETS_DIR/${SECRET_NAME}.txt"
        chmod 600 "$SECRETS_DIR/${SECRET_NAME}.txt"
        echo "Secret $SECRET_NAME created/updated successfully"
        ;;
    
    "remove")
        if [ -f "$SECRETS_DIR/${SECRET_NAME}.txt" ]; then
            rm "$SECRETS_DIR/${SECRET_NAME}.txt"
            echo "Secret $SECRET_NAME removed successfully"
        else
            echo "Secret $SECRET_NAME not found"
            exit 1
        fi
        ;;
    
    "list")
        echo "Available secrets:"
        ls -la "$SECRETS_DIR"/ 2>/dev/null || echo "No secrets directory found"
        ;;
    
    *)
        echo "Usage: $0 [create|update|remove|list] [secret_name] [secret_value]"
        echo "Examples:"
        echo "  $0 create db_password 'my_secure_password'"
        echo "  $0 create auth0_client_secret 'your_auth0_secret'"
        echo "  $0 list"
        echo "  $0 remove db_password"
        exit 1
        ;;
esac