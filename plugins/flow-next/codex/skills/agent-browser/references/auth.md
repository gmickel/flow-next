# Authentication

Patterns for handling login, sessions, and auth state.

## State Persistence

Save and restore full browser state (cookies, localStorage, sessionStorage):

```bash
# After successful login
agent-browser state save auth.json

# In new session
agent-browser state load auth.json
agent-browser open https://app.example.com/dashboard
```

## Token Auth via Headers

Skip login flows entirely with auth headers:

```bash
# Headers scoped to origin only (safe!)
agent-browser open api.example.com --headers '{"Authorization": "Bearer <token>"}'
```

Multiple origins:
```bash
agent-browser open api.example.com --headers '{"Authorization": "Bearer token1"}'
agent-browser open api.acme.com --headers '{"Authorization": "Bearer token2"}'
```

Global headers (all domains):
```bash
agent-browser set headers '{"X-Custom-Header": "value"}'
```

## Cookies

```bash
agent-browser cookies                    # Get all cookies
agent-browser cookies set name "value"   # Set cookie
agent-browser cookies clear              # Clear all cookies
```

## Local Storage

```bash
agent-browser storage local              # Get all localStorage
agent-browser storage local key          # Get specific key
agent-browser storage local set key val  # Set value
agent-browser storage local clear        # Clear all
```

## Session Storage

```bash
agent-browser storage session            # Get all sessionStorage
agent-browser storage session key        # Get specific key
agent-browser storage session set k v    # Set value
agent-browser storage session clear      # Clear all
```

## HTTP Basic Auth

```bash
agent-browser set credentials username password
agent-browser open https://protected-site.com
```

## OAuth / SSO Flows

Handle OAuth redirects across domains:

```bash
# Start OAuth flow
agent-browser open https://app.example.com/auth/google

# Handle redirects automatically
agent-browser wait --url "**/accounts.google.com**"
agent-browser snapshot -i

# Fill Google credentials
agent-browser fill @e1 "user@gmail.com"
agent-browser click @e2  # Next button
agent-browser wait 2000
agent-browser snapshot -i
agent-browser fill @e3 "password"
agent-browser click @e4  # Sign in

# Wait for redirect back
agent-browser wait --url "**/app.example.com**"
agent-browser state save ./oauth-state.json
```

## Two-Factor Authentication

Handle 2FA with manual intervention:

```bash
# Login with credentials
agent-browser open https://app.example.com/login --headed  # Show browser
agent-browser snapshot -i
agent-browser fill @e1 "user@example.com"
agent-browser fill @e2 "password123"
agent-browser click @e3

# Wait for user to complete 2FA manually
echo "Complete 2FA in the browser window..."
agent-browser wait --url "**/dashboard" --timeout 120000

# Save state after 2FA
agent-browser state save ./2fa-state.json
```

## Token Refresh Handling

For sessions with expiring tokens:

```bash
STATE_FILE="./auth-state.json"

# Try loading existing state
if [[ -f "$STATE_FILE" ]]; then
    agent-browser state load "$STATE_FILE"
    agent-browser open https://app.example.com/dashboard

    # Check if session still valid
    URL=$(agent-browser get url)
    if [[ "$URL" == *"/login"* ]]; then
        echo "Session expired, re-authenticating..."
        agent-browser snapshot -i
        agent-browser fill @e1 "$USERNAME"
        agent-browser fill @e2 "$PASSWORD"
        agent-browser click @e3
        agent-browser wait --url "**/dashboard"
        agent-browser state save "$STATE_FILE"
    fi
else
    # First-time login
    agent-browser open https://app.example.com/login
    # ... login flow ...
fi
```

## Example: Full Login Flow with State Save

```bash
# First run: perform login
agent-browser open https://app.example.com/login
agent-browser snapshot -i
agent-browser fill @e1 "user@example.com"
agent-browser fill @e2 "password123"
agent-browser click @e3
agent-browser wait --url "**/dashboard"
agent-browser wait --load networkidle
agent-browser snapshot -i  # Verify dashboard
agent-browser state save auth.json
agent-browser close
```

```bash
# Subsequent runs: skip login
agent-browser state load auth.json
agent-browser open https://app.example.com/dashboard
```

## Session Isolation

Different auth states in parallel:

```bash
# Admin session
agent-browser --session admin state load admin-auth.json
agent-browser --session admin open https://app.example.com/admin

# User session
agent-browser --session user state load user-auth.json
agent-browser --session user open https://app.example.com/profile
```

## Security Best Practices

1. **Never commit state files** — they contain session tokens
   ```bash
   echo "*.auth-state.json" >> .gitignore
   ```
2. **Use environment variables for credentials**
   ```bash
   agent-browser fill @e1 "$APP_USERNAME"
   agent-browser fill @e2 "$APP_PASSWORD"
   ```
3. **Clean up after automation**
   ```bash
   agent-browser cookies clear
   rm -f ./auth-state.json
   ```
4. **Use short-lived sessions for CI/CD** — don't persist state
