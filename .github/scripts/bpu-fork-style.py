"""Check the fixed-baseline diff using the repository's official hooks."""

import os
from pathlib import Path
import subprocess
import tempfile


BASE = "0785475d8f9c5800158b2046293b2ea6d394b24a"


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


run("git", "merge-base", "--is-ancestor", BASE, "HEAD")
run("git", "diff", "--check", BASE, "HEAD")
run("pre-commit", "run", "--from-ref", BASE, "--to-ref", "HEAD")
run("git", "diff", "--exit-code")
files = (
    subprocess.check_output(["git", "diff", "--name-only", "-z", BASE, "HEAD"])
    .decode()
    .rstrip("\0")
    .split("\0")
)

with tempfile.TemporaryDirectory(prefix="bpu-fork-style-") as directory:
    env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / "index"))
    run("git", "read-tree", BASE, env=env)
    run("git", "add", "--all", "--", *files, env=env)
    run("python3", "util/git-pre-commit.py", env=env)

print(f"Official source checks passed against {BASE}.")
