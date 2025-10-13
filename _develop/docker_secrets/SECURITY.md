# Security Best Practices for Environment Variables

This document outlines safe methods to inject environment variables into Docker containers.

## 🔐 Security Hierarchy (Priority Order)

1. **Docker Secrets** (Highest Security - Production)
2. **Environment Variables** (Medium Security - Development)
3. **Configuration Files** (Lowest Security - Defaults only)

## 🚀 Quick Start

### Development Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Fill in your actual values in `.env`:
   ```bash
   # Never commit this file to version control!
   AUTH0_CLIENT_ID=your_actual_client_id
   AUTH0_CLIENT_SECRET=your_actual_secret
   DB_PASSWORD=your_database_password
   ```

3. Run with docker-compose:
   ```bash
   docker-compose up -d
   ```

### Production Setup

1. Create secrets using the management script:
   ```bash
   ./manage-secrets.sh create auth0_client_secret "your_auth0_secret_here"
   ./manage-secrets.sh create db_password "your_database_password"
   ./manage-secrets.sh create api_key "your_api_key_here"
   ```

2. Use the production compose file:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

## 🛡️ Security Features

### SecureSettingsManager

The `dunebugger_settings_secure.py` module provides:

- **Automatic secret detection**: Checks Docker secrets first, then environment variables
- **Fallback hierarchy**: Gracefully falls back to config file values or defaults
- **Logging safety**: Logs which source is used without exposing actual values
- **Type validation**: Ensures values are properly converted to expected types

### Usage in Your Code

```python
from dunebugger_settings_secure import settings

# These will automatically use the most secure source available
auth_domain = settings.authURL
client_secret = settings.auth0_client_secret  # From Docker secret or env var
db_password = settings.db_password            # From Docker secret or env var
```

## 📁 File Structure

```
/
├── .env.example              # Template for environment variables
├── .env                      # Your actual env vars (NEVER commit!)
├── docker-compose.yml        # Development configuration
├── docker-compose.prod.yml   # Production with secrets
├── manage-secrets.sh         # Script to manage Docker secrets
├── secrets/                  # Directory for secret files (NEVER commit!)
│   ├── auth0_client_secret.txt
│   ├── db_password.txt
│   └── api_key.txt
└── app/
    └── dunebugger_settings_secure.py  # Secure settings manager
```

## ⚠️ Security Rules

### DO ✅
- Use Docker secrets for production environments
- Use environment variables for development
- Keep `.env` files out of version control
- Use the secrets management script for consistency
- Rotate secrets regularly
- Use least-privilege principles

### DON'T ❌
- Commit `.env` files to Git
- Put secrets directly in Dockerfile
- Use `ENV` instructions for sensitive data
- Log secret values (even in debug mode)
- Use config files for sensitive information
- Hardcode secrets in source code

## 🔧 Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `AUTH0_DOMAIN` | Auth0 domain for authentication | No | dunebugger.eu.auth0.com |
| `AUTH0_CLIENT_ID` | Auth0 client identifier | Yes* | - |
| `AUTH0_CLIENT_SECRET` | Auth0 client secret | Yes* | - |
| `DB_HOST` | Database hostname | No | localhost |
| `DB_PASSWORD` | Database password | Yes* | - |
| `API_KEY` | External API key | Yes* | - |
| `LOG_LEVEL` | Logging level | No | DEBUG |
| `ENVIRONMENT` | Environment name | No | development |

*Required for production deployments

## 🐳 Docker Secrets Commands

```bash
# Create a new secret
./manage-secrets.sh create secret_name "secret_value"

# Update an existing secret
./manage-secrets.sh update secret_name "new_secret_value"

# List all secrets
./manage-secrets.sh list

# Remove a secret
./manage-secrets.sh remove secret_name
```

## 🔄 Migration from Old Settings

To migrate from your current `dunebugger_settings.py`:

1. Update your imports:
   ```python
   # Old
   from dunebugger_settings import settings
   
   # New
   from dunebugger_settings_secure import settings
   ```

2. The API remains the same - your existing code will work unchanged!

## 🚨 Security Checklist

- [ ] `.env` files are in `.gitignore`
- [ ] Secrets directory is in `.gitignore`
- [ ] Production uses Docker secrets
- [ ] Development uses environment variables
- [ ] No secrets are hardcoded in source code
- [ ] Secrets have appropriate file permissions (600)
- [ ] Regular secret rotation schedule in place