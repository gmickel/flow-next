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

## Cookies, Storage, and HTTP Basic Auth

Basic `cookies`, `storage local`, `storage session`, and `set credentials` syntax lives in [commands.md](commands.md).

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

For sessions with expiring tokens (covers both first-time login and state-save reuse):

```bash
STATE_FILE="./auth-state.json"

if [[ -f "$STATE_FILE" ]]; then
    agent-browser state load "$STATE_FILE"
    agent-browser open https://app.example.com/dashboard
    URL=$(agent-browser get url)
else
    URL="/login"
    agent-browser open https://app.example.com/login
fi

if [[ "$URL" == *"/login"* ]]; then
    agent-browser snapshot -i
    agent-browser fill @e1 "$USERNAME"
    agent-browser fill @e2 "$PASSWORD"
    agent-browser click @e3
    agent-browser wait --url "**/dashboard"
    agent-browser wait --load networkidle
    agent-browser state save "$STATE_FILE"
fi
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
