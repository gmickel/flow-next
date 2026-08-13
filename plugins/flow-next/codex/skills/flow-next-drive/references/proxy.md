# Proxy Support

Proxy configuration for geo-testing, rate limiting avoidance, and corporate environments.

## Basic Configuration

```bash
# Via CLI flag
agent-browser --proxy "http://proxy.example.com:8080" open https://example.com

# Via environment variable
export HTTP_PROXY="http://proxy.example.com:8080"
export HTTPS_PROXY="http://proxy.example.com:8080"
agent-browser open https://example.com
```

## Authenticated Proxy

```bash
export HTTP_PROXY="http://username:password@proxy.example.com:8080"
agent-browser open https://example.com
```

## SOCKS Proxy

```bash
export ALL_PROXY="socks5://proxy.example.com:1080"
agent-browser open https://example.com

# With auth
export ALL_PROXY="socks5://user:pass@proxy.example.com:1080"
```

## Proxy Bypass

```bash
# Via CLI flag
agent-browser --proxy "http://proxy:8080" --proxy-bypass "localhost,*.internal.com" open https://example.com

# Via environment variable
export NO_PROXY="localhost,127.0.0.1,.internal.company.com"
```

## Common Use Cases

### Geo-Location Testing

```bash
PROXIES=(
    "http://us-proxy.example.com:8080"
    "http://eu-proxy.example.com:8080"
    "http://asia-proxy.example.com:8080"
)

for proxy in "${PROXIES[@]}"; do
    export HTTP_PROXY="$proxy"
    export HTTPS_PROXY="$proxy"
    region=$(echo "$proxy" | grep -oP '^\w+-\w+')
    agent-browser --session "$region" open https://example.com
    agent-browser --session "$region" screenshot "./screenshots/$region.png"
    agent-browser --session "$region" close
done
```

### Rotating Proxies for Scraping

```bash
PROXY_LIST=(
    "http://proxy1.example.com:8080"
    "http://proxy2.example.com:8080"
    "http://proxy3.example.com:8080"
)

for i in "${!URLS[@]}"; do
    proxy_index=$((i % ${#PROXY_LIST[@]}))
    export HTTP_PROXY="${PROXY_LIST[$proxy_index]}"
    export HTTPS_PROXY="${PROXY_LIST[$proxy_index]}"
    agent-browser open "${URLS[$i]}"
    agent-browser get text body > "output-$i.txt"
    agent-browser close
    sleep 1
done
```

### Corporate Network

```bash
export HTTP_PROXY="http://corpproxy.company.com:8080"
export HTTPS_PROXY="http://corpproxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1,.company.com"

agent-browser open https://external-vendor.com   # Via proxy
agent-browser open https://intranet.company.com  # Direct (bypassed)
```

## Verifying Proxy

```bash
agent-browser open https://httpbin.org/ip
agent-browser get text body  # Should show proxy's IP
```

## Troubleshooting

**Connection failed**: Test proxy first with `curl -x http://proxy:8080 https://httpbin.org/ip`

**SSL errors through proxy**: Some proxies do SSL inspection:
```bash
agent-browser open https://example.com --ignore-https-errors
```

**Slow performance**: Bypass proxy for CDN/static assets:
```bash
export NO_PROXY="*.cdn.com,*.static.com"
```

## Best Practices

1. Use environment variables — don't hardcode proxy credentials
2. Set `NO_PROXY` — avoid routing local traffic through proxy
3. Test proxy before automation
4. Rotate proxies for large scraping jobs
