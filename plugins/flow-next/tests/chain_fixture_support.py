"""Shared git/GitHub fixtures still used by work and make-pr chain tests.

Extracted from retired land fence tests; no land workflow is simulated here.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

STUB = Path(__file__).parent / "fixtures" / "land_chain_gh_stub.py"
_FENCE_RE = re.compile(r"^[ \t]*# fence:(?P<name>[a-z-]+)\b.*?$", re.MULTILINE)

def fence(path: Path, name: str) -> str:
    """The bash block that starts at `# fence:<name>` up to its closing ```."""
    if path.parent.name == "flow-next-make-pr":
        script = "make-pr-preflight.sh" if path.name == "workflow.md" else "make-pr-create.sh"
        path = path.parents[2] / "scripts" / script
    text = path.read_text(encoding="utf-8")
    for m in _FENCE_RE.finditer(text):
        if m.group("name") == name:
            end = text.index("# end:block" if path.suffix == ".sh" else "```", m.end())
            block = text[m.start():end]
            # the frontier fence is indented inside a list item
            indent = re.match(r"[ \t]*", block).group(0)
            return "\n".join(line[len(indent):] if line.startswith(indent) else line for line in block.splitlines()) + "\n"
    raise AssertionError(f"fence {name!r} not found in {path}")


def git(cwd: Path, *args: str, check: bool = True) -> str:
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and out.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed in {cwd}: {out.stderr}")
    return out.stdout.strip()


class ChainWorld:
    """Bare origin + author clone + land clone + gh world for one scenario."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.origin = tmp / "origin.git"
        self.work = tmp / "work"
        self.land = tmp / "land"
        self.world_path = tmp / "world.json"
        self.bin = tmp / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(f"#!/bin/sh\nexec {sys.executable} {STUB} \"$@\"\n", encoding="utf-8")
        gh.chmod(0o755)
        git(tmp, "init", "-q", "--bare", "-b", "main", str(self.origin))
        git(tmp, "clone", "-q", str(self.origin), str(self.work))
        git(self.work, "config", "user.email", "t@example.com")
        git(self.work, "config", "user.name", "t")
        git(self.work, "checkout", "-q", "-b", "main")
        self.commit(self.work, "base.txt", "base\n", "base")
        git(self.work, "push", "-q", "-u", "origin", "main")
        git(tmp, "clone", "-q", str(self.origin), str(self.land))
        git(self.land, "config", "user.email", "land@example.com")
        git(self.land, "config", "user.name", "land")
        self.world = {"owner_repo": "o/r", "origin": str(self.origin), "prs": {}, "stacks": {}, "delete_mode": "ok", "comments": {}, "calls": []}
        self.save()

    # ---- world ----
    def save(self) -> None:
        self.world_path.write_text(json.dumps(self.world), encoding="utf-8")

    def reload(self) -> dict:
        self.world = json.loads(self.world_path.read_text(encoding="utf-8"))
        return self.world

    def add_pr(self, number: int, head: str, base: str, stack: dict | None = None, state: str = "OPEN") -> None:
        self.world["prs"][str(number)] = {
            "number": number, "url": f"https://github.com/o/r/pull/{number}", "state": state,
            "headRefName": head, "baseRefName": base, "stack": stack, "mergedAt": None, "reviewDecision": "",
        }
        self.save()

    def calls(self, *prefix: str) -> list[list[str]]:
        return [c for c in self.reload()["calls"] if c[:len(prefix)] == list(prefix)]

    # ---- git ----
    def commit(self, cwd: Path, name: str, content: str, msg: str) -> str:
        (cwd / name).write_text(content, encoding="utf-8")
        git(cwd, "add", name)
        git(cwd, "commit", "-q", "-m", msg)
        return git(cwd, "rev-parse", "HEAD")

    def branch(self, name: str, from_ref: str, files: list[tuple[str, str]]) -> str:
        git(self.work, "checkout", "-q", "-B", name, from_ref)
        for f, c in files:
            self.commit(self.work, f, c, f"{name}: {f}")
        git(self.work, "push", "-q", "-f", "-u", "origin", name)
        return git(self.work, "rev-parse", "HEAD")

    def squash_merge(self, branch: str, into: str = "main") -> str:
        git(self.work, "fetch", "-q", "origin")
        git(self.work, "checkout", "-q", "-B", into, f"origin/{into}")
        git(self.work, "merge", "-q", "--squash", f"origin/{branch}")
        git(self.work, "commit", "-q", "-m", f"squash {branch}")
        git(self.work, "push", "-q", "origin", into)
        return git(self.work, "rev-parse", "HEAD")

    def origin_sha(self, branch: str) -> str:
        return git(self.tmp, "--git-dir", str(self.origin), "rev-parse", "-q", "--verify", f"refs/heads/{branch}", check=False)


    def reject_pushes_to(self, branch: str | None) -> None:
        hook = self.origin / "hooks" / "pre-receive"
        if branch is None:
            hook.unlink(missing_ok=True)
            return
        hook.write_text(
            "#!/bin/sh\nwhile read old new ref; do\n"
            f"  [ \"$ref\" = \"refs/heads/{branch}\" ] && {{ echo \"rejected $ref\" >&2; exit 1; }}\n"
            "done\nexit 0\n", encoding="utf-8")
        hook.chmod(0o755)

    # ---- fences ----


