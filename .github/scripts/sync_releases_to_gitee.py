#!/usr/bin/env python3
"""Sync GitHub releases (metadata + assets) to Gitee.

Design notes
------------
- GitHub is the single source of truth. This script never deletes anything on
  GitHub and never touches GitHub releases (read-only on the GitHub side).
- Idempotent: safe to re-run any number of times. Existing Gitee attach files
  whose SHA256 matches the GitHub digest are skipped; mismatched files are
  deleted and re-uploaded; release title/body/prerelease are updated in place.
- Integrity: every asset downloaded from GitHub is checked against the
  ``digest`` (sha256) field of the GitHub Release API, and every file uploaded
  to Gitee is downloaded back and re-checked against the same digest before
  the script reports success.
- Retries: all HTTP requests are retried with exponential backoff. The whole
  step is additionally wrapped by nick-fields/retry in the workflow, and any
  manual re-run resumes cleanly because every operation is idempotent.

Gitee API v5 endpoints used (verified against the official swagger spec):
  GET    /repos/{owner}/{repo}/releases/tags/{tag}
  POST   /repos/{owner}/{repo}/releases
  PATCH  /repos/{owner}/{repo}/releases/{id}
  GET    /repos/{owner}/{repo}/releases/{release_id}/attach_files
  POST   /repos/{owner}/{repo}/releases/{release_id}/attach_files      (multipart)
  DELETE /repos/{owner}/{repo}/releases/{release_id}/attach_files/{id}
  GET    /repos/{owner}/{repo}/releases/{release_id}/attach_files/{id}/download
"""

import argparse
import hashlib
import json
import mimetypes
import os
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

GITHUB_API = "https://api.github.com"
# GITEE_API_BASE exists so the write paths can be exercised against a local
# mock server in tests; it always points at Gitee in production.
GITEE_API = os.environ.get("GITEE_API_BASE", "https://gitee.com/api/v5").rstrip("/")

HTTP_ATTEMPTS = 3          # attempts for each individual HTTP request
HTTP_BACKOFF = 5           # seconds; doubled after every failed attempt
UPLOAD_ATTEMPTS = 3        # upload+verify cycles per asset
REQUEST_TIMEOUT = 120      # seconds, for metadata API calls
DOWNLOAD_TIMEOUT = 600     # seconds, for asset downloads (files are 40-60 MB)
PER_PAGE = 100

OK = "\u2713"   # check mark
CHANGED = "~"
SKIP = "-"


def log(msg):
    print(msg, flush=True)


# Windows consoles may default to a legacy code page (e.g. GBK) that cannot
# encode the check marks used in the summary lines.
for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


class SyncError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Low-level HTTP helpers (stdlib only, with retry + backoff)
# ---------------------------------------------------------------------------

def retry_call(desc, func, attempts=HTTP_ATTEMPTS):
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as exc:  # noqa: BLE001 - deliberate broad retry
            last_exc = exc
            if attempt == attempts:
                break
            wait = HTTP_BACKOFF * (2 ** (attempt - 1))
            log(f"    ! {desc} failed (attempt {attempt}/{attempts}): {exc}")
            log(f"    ! retrying in {wait}s ...")
            time.sleep(wait)
    raise SyncError(f"{desc} failed after {attempts} attempts: {last_exc}")


def http_request(url, *, method="GET", headers=None, data=None, timeout=REQUEST_TIMEOUT):
    """Perform an HTTP request and return (status, headers, body-bytes)."""
    req = urllib.request.Request(url, data=data, method=method)
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode(), dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def github_api(path, token=None, *, method="GET", params=None):
    """Call the GitHub REST API and return parsed JSON. Raises SyncError on >=400."""
    url = f"{GITHUB_API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "unitree-network-tool-gitee-sync",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    def call():
        status, _, body = http_request(url, method=method, headers=headers)
        if status >= 400:
            raise SyncError(f"GitHub API {method} {path} -> HTTP {status}: {body[:400]!r}")
        return json.loads(body.decode("utf-8")) if body else None

    return retry_call(f"GitHub API {method} {path}", call)


def gitee_api(path, token, *, method="GET", form=None, params=None):
    """Call the Gitee API v5 and return parsed JSON. Raises SyncError on >=400."""
    url = f"{GITEE_API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"User-Agent": "unitree-network-tool-gitee-sync"}
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    def call():
        status, _, body = http_request(url, method=method, headers=headers, data=data)
        if status >= 400:
            raise SyncError(f"Gitee API {method} {path} -> HTTP {status}: {body[:400]!r}")
        return json.loads(body.decode("utf-8")) if body else None

    return retry_call(f"Gitee API {method} {path}", call)


def download_file(url, dest, *, token=None, desc=None):
    """Stream a remote file to ``dest`` (Path) with retry."""
    desc = desc or f"download {url}"

    def call():
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "unitree-network-tool-gitee-sync")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp, open(dest, "wb") as out:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)

    retry_call(desc, call)


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def multipart_body(fields, file_field, file_path):
    """Build a multipart/form-data body: text ``fields`` plus one binary file."""
    boundary = "----gitee-sync-" + uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )
    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{file_field}"; '
            f'filename="{file_path.name}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")
    )
    with open(file_path, "rb") as fh:
        parts.append(fh.read())
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


# ---------------------------------------------------------------------------
# Gitee release operations
# ---------------------------------------------------------------------------

def gitee_get_release_by_tag(owner, repo, tag, token):
    """Return the Gitee release dict for ``tag``, or None when it does not exist."""
    path = f"/repos/{owner}/{repo}/releases/tags/{urllib.parse.quote(tag)}"
    url = f"{GITEE_API}{path}"
    headers = {"User-Agent": "unitree-network-tool-gitee-sync"}
    params = {"access_token": token} if token else {}

    def call():
        full_url = url + ("?" + urllib.parse.urlencode(params) if params else "")
        status, _, body = http_request(full_url, headers=headers)
        if status == 404:
            return None
        if status >= 400:
            raise SyncError(f"Gitee API GET {path} -> HTTP {status}: {body[:400]!r}")
        return json.loads(body.decode("utf-8"))

    return retry_call(f"Gitee GET release by tag {tag}", call)


def gitee_create_release(owner, repo, token, gh_release):
    form = {
        "access_token": token,
        "tag_name": gh_release["tag_name"],
        "name": gh_release.get("name") or gh_release["tag_name"],
        "body": gh_release.get("body") or "",
        "prerelease": "true" if gh_release.get("prerelease") else "false",
        "target_commitish": gh_release.get("target_commitish") or "main",
    }
    return gitee_api(f"/repos/{owner}/{repo}/releases", token, method="POST", form=form)


def gitee_update_release(owner, repo, token, release_id, gh_release):
    form = {
        "access_token": token,
        "tag_name": gh_release["tag_name"],
        "name": gh_release.get("name") or gh_release["tag_name"],
        "body": gh_release.get("body") or "",
        "prerelease": "true" if gh_release.get("prerelease") else "false",
    }
    return gitee_api(
        f"/repos/{owner}/{repo}/releases/{release_id}", token, method="PATCH", form=form
    )


def gitee_list_attach_files(owner, repo, token, release_id):
    files, page = [], 1
    while True:
        params = {"page": page, "per_page": PER_PAGE, "direction": "desc"}
        if token:
            params["access_token"] = token
        batch = gitee_api(
            f"/repos/{owner}/{repo}/releases/{release_id}/attach_files",
            token,
            params=params,
        )
        files.extend(batch)
        if len(batch) < PER_PAGE:
            return files
        page += 1


def gitee_delete_attach_file(owner, repo, token, release_id, attach_id, name):
    gitee_api(
        f"/repos/{owner}/{repo}/releases/{release_id}/attach_files/{attach_id}",
        token,
        method="DELETE",
        params={"access_token": token},
    )


def gitee_upload_attach_file(owner, repo, token, release_id, file_path):
    url = f"{GITEE_API}/repos/{owner}/{repo}/releases/{release_id}/attach_files"
    body, content_type = multipart_body(
        {"access_token": token}, "file", file_path
    )
    headers = {
        "User-Agent": "unitree-network-tool-gitee-sync",
        "Content-Type": content_type,
    }

    def call():
        status, _, resp = http_request(url, method="POST", headers=headers, data=body)
        if status >= 400:
            raise SyncError(f"Gitee upload -> HTTP {status}: {resp[:400]!r}")
        return json.loads(resp.decode("utf-8")) if resp else None

    return retry_call(f"Gitee upload {file_path.name}", call)


def gitee_download_attach_file(owner, repo, token, release_id, attach_id, dest, name):
    url = (
        f"{GITEE_API}/repos/{owner}/{repo}/releases/{release_id}"
        f"/attach_files/{attach_id}/download"
    )
    if token:
        url += "?" + urllib.parse.urlencode({"access_token": token})
    download_file(url, dest, desc=f"Gitee download {name}")


# ---------------------------------------------------------------------------
# Sync logic
# ---------------------------------------------------------------------------

def fetch_github_releases(github_repo, token, args):
    """Return the list of GitHub releases to sync, oldest first."""
    if args.all:
        releases, page = [], 1
        while True:
            batch = github_api(
                f"/repos/{github_repo}/releases",
                token,
                params={"per_page": PER_PAGE, "page": page},
            )
            releases.extend(batch)
            if len(batch) < PER_PAGE:
                break
            page += 1
        releases = [r for r in releases if not r.get("draft")]
        releases.reverse()  # oldest first, so Gitee shows a natural history
        if not releases:
            raise SyncError("no published GitHub releases found")
        return releases
    if args.tag:
        release = github_api(
            f"/repos/{github_repo}/releases/tags/{urllib.parse.quote(args.tag)}", token
        )
        if release.get("draft"):
            raise SyncError(f"release {args.tag} is a draft; drafts are never synced")
        return [release]
    release = github_api(f"/repos/{github_repo}/releases/latest", token)
    return [release]


def expected_sha256(asset):
    """Extract the sha256 hex digest reported by the GitHub API."""
    digest = asset.get("digest") or ""
    if digest.startswith("sha256:"):
        return digest[len("sha256:"):]
    return None


def download_and_verify_github_asset(asset, token, workdir):
    """Download one GitHub asset, verify its SHA256 against the API digest."""
    name = asset["name"]
    expected = expected_sha256(asset)
    dest = workdir / name
    download_file(
        asset["browser_download_url"], dest, token=token, desc=f"GitHub download {name}"
    )
    actual = sha256_of(dest)
    if expected and actual != expected:
        raise SyncError(
            f"SHA256 mismatch after GitHub download for {name}: "
            f"api={expected} downloaded={actual}"
        )
    if not expected:
        log(f"    ! note: GitHub reports no digest for {name}; using computed sha256 {actual}")
    return dest, actual, expected


def verify_gitee_attach(owner, repo, token, release_id, attach, expected_sha, workdir):
    """Download one Gitee attach file and compare its SHA256. True when equal."""
    with tempfile.TemporaryDirectory(dir=workdir) as tmp:
        dest = Path(tmp) / attach["name"]
        gitee_download_attach_file(
            owner, repo, token, release_id, attach["id"], dest, attach["name"]
        )
        return sha256_of(dest) == expected_sha


def sync_one_release(gh_release, *, github_repo, owner, repo, tokens, args, workdir):
    tag = gh_release["tag_name"]
    gh_name = gh_release.get("name") or tag
    log("")
    log(f"=== Release {tag} - {gh_name} ===")
    log(f"    GitHub: {gh_release['html_url']}")

    # 1) Download every GitHub asset first and verify integrity at the source.
    local_assets = []  # (asset, path, sha256)
    for asset in gh_release.get("assets", []):
        path, sha, _ = download_and_verify_github_asset(asset, tokens["github"], workdir)
        log(f"  {OK} GitHub asset {asset['name']} sha256={sha[:16]}... verified")
        local_assets.append((asset, path, sha))

    # 2) Locate or create the Gitee release.
    gitee_release = gitee_get_release_by_tag(owner, repo, tag, tokens["gitee"])
    if gitee_release is None:
        log(f"  + Gitee release {tag} does not exist yet -> create")
        if args.dry_run:
            log(f"  {SKIP} dry-run: would create release {tag} "
                f"(name/prerelease/target from GitHub)")
        else:
            gitee_release = gitee_create_release(owner, repo, tokens["gitee"], gh_release)
            log(f"  {OK} created Gitee release id={gitee_release['id']}")
    else:
        log(f"  = Gitee release {tag} already exists (id={gitee_release['id']})")
        needs_update = (
            (gitee_release.get("name") or "") != (gh_release.get("name") or tag)
            or (gitee_release.get("body") or "") != (gh_release.get("body") or "")
            or bool(gitee_release.get("prerelease")) != bool(gh_release.get("prerelease"))
        )
        if needs_update:
            log(f"  {CHANGED} metadata differs (title/body/prerelease) -> update")
            if not args.dry_run:
                gitee_update_release(
                    owner, repo, tokens["gitee"], gitee_release["id"], gh_release
                )
                log(f"  {OK} Gitee release metadata updated")
        else:
            log(f"  {OK} metadata already in sync")

    # 3) Sync assets (idempotent, SHA256-checked both sides).
    attach_files = (
        gitee_list_attach_files(owner, repo, tokens["gitee"], gitee_release["id"])
        if gitee_release
        else []
    )
    by_name = {f["name"]: f for f in attach_files}
    wanted_names = {a["name"] for a, _, _ in local_assets}

    for asset, path, sha in local_assets:
        name = asset["name"]
        existing = by_name.get(name)
        if existing is not None:
            log(f"  = Gitee already has {name} (id={existing['id']}) -> verify SHA256")
            if verify_gitee_attach(
                owner, repo, tokens["gitee"], gitee_release["id"], existing, sha, workdir
            ):
                log(f"  {OK} {name} identical on Gitee (sha256 match) -> skip upload")
                continue
            log(f"  {CHANGED} {name} differs on Gitee -> delete and re-upload")
            if not args.dry_run:
                gitee_delete_attach_file(
                    owner, repo, tokens["gitee"], gitee_release["id"], existing["id"], name
                )
            existing = None

        if args.dry_run:
            log(f"  {SKIP} dry-run: would upload {name} "
                f"({asset['size']} bytes) and verify sha256")
            continue

        uploaded = False
        for attempt in range(1, UPLOAD_ATTEMPTS + 1):
            gitee_upload_attach_file(
                owner, repo, tokens["gitee"], gitee_release["id"], path
            )
            refreshed = {
                f["name"]: f
                for f in gitee_list_attach_files(
                    owner, repo, tokens["gitee"], gitee_release["id"]
                )
            }
            uploaded_file = refreshed.get(name)
            if uploaded_file and verify_gitee_attach(
                owner, repo, tokens["gitee"], gitee_release["id"], uploaded_file, sha, workdir
            ):
                log(f"  {OK} uploaded {name}; Gitee sha256 verified "
                    f"(attempt {attempt})")
                uploaded = True
                break
            log(f"    ! upload attempt {attempt}/{UPLOAD_ATTEMPTS} for {name} "
                f"failed verification; retrying")
        if not uploaded:
            raise SyncError(f"failed to upload+verify {name} on Gitee")

    # 4) Report (and optionally prune) files that only exist on Gitee.
    extras = [n for n in by_name if n not in wanted_names]
    if extras:
        if args.prune and not args.dry_run:
            for name in extras:
                log(f"  - pruning extra Gitee file not present on GitHub: {name}")
                gitee_delete_attach_file(
                    owner, repo, tokens["gitee"], gitee_release["id"], by_name[name]["id"], name
                )
        else:
            log(f"  ! Gitee has extra files not present on GitHub (kept, "
                f"use --prune to remove): {', '.join(extras)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--github-repo", required=True, help="owner/repo on GitHub")
    parser.add_argument("--gitee-owner", required=True)
    parser.add_argument("--gitee-repo", required=True)
    parser.add_argument("--tag", help="specific release tag to sync (default: latest)")
    parser.add_argument("--all", action="store_true",
                        help="sync every published release (backfill, oldest first)")
    parser.add_argument("--prune", action="store_true",
                        help="delete Gitee attach files that no longer exist on GitHub")
    parser.add_argument("--dry-run", action="store_true",
                        help="verify and plan only; no write calls against Gitee")
    parser.add_argument("--github-token", default=os.environ.get("GITHUB_TOKEN"))
    parser.add_argument("--gitee-token", default=os.environ.get("GITEE_TOKEN"))
    args = parser.parse_args()

    if args.tag and args.all:
        parser.error("--tag and --all are mutually exclusive")
    if not args.gitee_token and not args.dry_run:
        raise SyncError(
            "Gitee token is required for syncing (pass --gitee-token or set GITEE_TOKEN); "
            "it is optional only together with --dry-run on public repositories"
        )

    tokens = {"github": args.github_token, "gitee": args.gitee_token}
    releases = fetch_github_releases(args.github_repo, args.github_token, args)
    mode = "all releases (backfill)" if args.all else (args.tag or "latest")
    log(f"Syncing {mode}: {len(releases)} release(s) from GitHub "
        f"{args.github_repo} to Gitee {args.gitee_owner}/{args.gitee_repo}"
        f"{' [DRY-RUN]' if args.dry_run else ''}")

    with tempfile.TemporaryDirectory(prefix="gitee-sync-") as tmp:
        workdir = Path(tmp)
        for release in releases:
            sync_one_release(
                release,
                github_repo=args.github_repo,
                owner=args.gitee_owner,
                repo=args.gitee_repo,
                tokens=tokens,
                args=args,
                workdir=workdir,
            )

    log("")
    log(f"DONE: {len(releases)} release(s) processed successfully.")


if __name__ == "__main__":
    try:
        main()
    except SyncError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
