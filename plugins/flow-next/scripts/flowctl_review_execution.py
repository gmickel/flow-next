"""Opt-in local execution provider for the packaged review adapters.

Only inference crosses this boundary. The caller retains review prompts,
reservations, verdict parsing and receipt publication.
"""

import hashlib
import ipaddress
import json
import os
import urllib.error
import urllib.parse
import urllib.request


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def execute_review(*, backend, model, effort, prompt, repository_path,
                   session_id, resume_only, timeout, resolution_out, request_scope=None):
    """Return the adapter tuple, or None only when no provider was configured."""
    url = os.environ.get("FLOW_REVIEW_EXECUTION_URL")
    if url is None:
        return None
    try:
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme != "http" or not parsed.hostname
                or not ipaddress.ip_address(parsed.hostname).is_loopback
                or parsed.username or parsed.password or parsed.fragment):
            raise ValueError("provider URL must be a loopback HTTP endpoint")
        token = os.environ.get("FLOW_REVIEW_EXECUTION_TOKEN", "")
        if not token or "\r" in token or "\n" in token:
            raise ValueError("provider requires a scoped token")
        payload = {
            "schemaVersion": 1,
            "backend": backend, "model": model, "effort": effort,
            "prompt": prompt, "repositoryPath": str(repository_path),
            "sessionId": session_id, "resumeOnly": resume_only,
            "permissionMode": "read-only", "timeoutSeconds": timeout,
        }
        identity = {key: value for key, value in payload.items() if key != "timeoutSeconds"}
        identity["requestScope"] = request_scope
        payload["requestId"] = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        request = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        )
        # Local scope credentials must not follow redirects or environment proxies.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError("provider response exceeds 16 MiB")
        result = json.loads(raw)
        if (not isinstance(result, dict) or result.get("schemaVersion") != 1
                or not isinstance(result.get("output"), str)
                or not isinstance(result.get("stderr"), str)
                or type(result.get("exitCode")) is not int
                or result["exitCode"] < 0
                or (result.get("sessionId") is not None
                    and not isinstance(result["sessionId"], str))
                or type(result.get("resumeFailed", False)) is not bool
                or (result.get("observedModel") is not None
                    and not isinstance(result["observedModel"], str))):
            raise ValueError("invalid provider response")
        if result.get("resumeFailed") and (not session_id or result["exitCode"] == 0):
            raise ValueError("invalid resume failure")
        if resolution_out is not None:
            resolution_out["resume_failed"] = result.get("resumeFailed", False)
        # Nonzero transport outcomes must never leak a verdict into the parser.
        return (result["output"] if result["exitCode"] == 0 else "",
                result.get("sessionId"), result["exitCode"], result["stderr"])
    except (OSError, ValueError, TypeError, urllib.error.URLError):
        # Avoid copying URLs, response bodies or credentials into ordinary logs.
        return "", session_id, 2, "managed review execution failed; inspect the provider's protected diagnostics"
