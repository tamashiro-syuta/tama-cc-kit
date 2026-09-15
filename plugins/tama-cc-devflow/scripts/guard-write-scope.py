#!/usr/bin/env python3
"""PreToolUse hook: block Edit/Write outside the active session's allowed paths.

Active only when a devflow session exists whose claude_session_id matches the hook's session_id
and whose phase is one of the guarded phases. Always allows writes under .tama-cc-devflow/.

- phase == implementation: allowed = union of write_scope of tasks in running/review status
- other guarded phases: no source writes at all (design, review, planning, pr phases must not touch code)
Exit 2 blocks the tool call; the message on stderr is shown to the model.
"""
import fnmatch
import json
import os
import sys

GUARDED = {"routing", "clarify", "design", "design_review", "design_approval", "planning",
           "implementation", "integration", "human_review", "pr"}


def main():
    payload = json.load(sys.stdin)
    project = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    project = os.environ.get("CLAUDE_PROJECT_DIR", project)
    root = os.path.join(project, ".tama-cc-devflow")
    current = os.path.join(root, "current")
    if not os.path.isfile(current):
        return
    with open(current) as f:
        sdir = os.path.join(root, f.read().strip())
    try:
        with open(os.path.join(sdir, "status.json")) as f:
            status = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    if status.get("claude_session_id") != payload.get("session_id"):
        return
    if status.get("phase") not in GUARDED:
        return

    tool_input = payload.get("tool_input", {})
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not path:
        return
    abs_path = os.path.abspath(os.path.join(project, path))
    rel = os.path.relpath(abs_path, project)
    if rel.startswith(".tama-cc-devflow/"):
        return

    phase = status["phase"]
    if phase != "implementation":
        print(f"devflow guard: phase '{phase}' does not allow editing source files ({rel}). "
              f"Only the session whiteboard under .tama-cc-devflow/ may be written now.", file=sys.stderr)
        sys.exit(2)

    allowed = []
    for tid, t in status.get("tasks", {}).items():
        if t.get("status") in ("running", "review"):
            allowed.extend((tid, p.lstrip("./")) for p in t.get("write_scope", []))
    for tid, pattern in allowed:
        if rel == pattern or fnmatch.fnmatch(rel, pattern):
            return
        pdir = pattern.split("*")[0].rstrip("/")
        if pdir and rel.startswith(pdir + "/"):
            return
    scopes = "; ".join(f"{tid}: {p}" for tid, p in allowed) or "(no task running)"
    print(f"devflow guard: {rel} is outside the write_scope of running tasks [{scopes}]. "
          f"If the task genuinely needs this file, stop and report it as a scope deviation in your result "
          f"instead of editing it.", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
