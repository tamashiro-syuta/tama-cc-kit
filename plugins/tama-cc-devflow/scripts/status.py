#!/usr/bin/env python3
"""Read and update the session's status.json.

Usage:
  status.py [--session <id>] summary
  status.py [--session <id>] get <dotted.path>
  status.py [--session <id>] set <dotted.path> <json-value>
  status.py [--session <id>] task <id> <status>          # pending|running|review|done|failed|blocked
  status.py [--session <id>] ready                        # tasks runnable now, capped by MAX_PARALLEL
  status.py [--session <id>] reset-running                # running -> pending (used by resume)
  status.py [--session <id>] path                         # print session dir

`--session` defaults to the id in .tama-cc-devflow/current.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

MAX_PARALLEL = 3
TASK_STATUSES = {"pending", "running", "review", "done", "failed", "blocked"}


def project_dir():
    d = os.environ.get("CLAUDE_PROJECT_DIR")
    if d:
        return d
    return subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()


def session_dir(session):
    root = os.path.join(project_dir(), ".tama-cc-devflow")
    if session is None:
        current = os.path.join(root, "current")
        if not os.path.isfile(current):
            sys.exit("no devflow session exists yet (missing .tama-cc-devflow/current); start one with /tama-cc-devflow:run")
        with open(current) as f:
            session = f.read().strip()
    d = os.path.join(root, session)
    if not os.path.isdir(d):
        sys.exit(f"session directory not found: {d}")
    return d


def load(d):
    with open(os.path.join(d, "status.json")) as f:
        return json.load(f)


def save(d, status):
    status["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tmp = os.path.join(d, "status.json.tmp")
    with open(tmp, "w") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, os.path.join(d, "status.json"))


def walk(obj, path, create=False):
    keys = path.split(".")
    for k in keys[:-1]:
        if k not in obj:
            if not create:
                sys.exit(f"path not found: {path}")
            obj[k] = {}
        obj = obj[k]
    return obj, keys[-1]


def cmd_summary(status):
    print(f"session: {status['session_id']}")
    print(f"size: {status['size']}  phase: {status['phase']}  branch: {status['branch']}")
    print(f"design review rounds: {status['review_rounds']['design']}")
    tasks = status["tasks"]
    if tasks:
        print("tasks:")
        for tid, t in sorted(tasks.items(), key=lambda kv: (kv[1].get("wave", 0), kv[0])):
            deps = ",".join(t.get("depends_on", [])) or "-"
            print(f"  {tid:<6} wave={t.get('wave', '?')} status={t['status']:<8} rounds={t.get('review_rounds', 0)} deps={deps}  {t.get('title', '')}")
    if status["human_decisions_required"]:
        print("human decisions required:")
        for h in status["human_decisions_required"]:
            print(f"  - {h}")
    if status.get("pr_url"):
        print(f"pr: {status['pr_url']}")


def cmd_ready(status):
    tasks = status["tasks"]
    running = sum(1 for t in tasks.values() if t["status"] in ("running", "review"))
    slots = MAX_PARALLEL - running
    ready = [
        tid for tid, t in sorted(tasks.items(), key=lambda kv: (kv[1].get("wave", 0), kv[0]))
        if t["status"] == "pending" and all(tasks[d]["status"] == "done" for d in t.get("depends_on", []))
    ]
    # Only hand out tasks from the lowest pending wave, so waves stay meaningful.
    if ready:
        lowest = tasks[ready[0]].get("wave", 0)
        ready = [tid for tid in ready if tasks[tid].get("wave", 0) == lowest]
    for tid in ready[: max(slots, 0)]:
        print(tid)


def main(argv):
    session = None
    if len(argv) >= 2 and argv[0] == "--session":
        session = argv[1]
        argv = argv[2:]
    if not argv:
        sys.exit(__doc__)
    d = session_dir(session)
    cmd, args = argv[0], argv[1:]

    if cmd == "path":
        print(d)
        return
    status = load(d)
    if cmd == "summary":
        cmd_summary(status)
    elif cmd == "get":
        obj, k = walk(status, args[0])
        print(json.dumps(obj.get(k), ensure_ascii=False))
    elif cmd == "set":
        obj, k = walk(status, args[0], create=True)
        obj[k] = json.loads(args[1])
        save(d, status)
    elif cmd == "task":
        tid, new = args
        if new not in TASK_STATUSES:
            sys.exit(f"invalid task status: {new}")
        status["tasks"][tid]["status"] = new
        if new == "review":
            status["tasks"][tid]["review_rounds"] = status["tasks"][tid].get("review_rounds", 0) + 1
        save(d, status)
    elif cmd == "ready":
        cmd_ready(status)
    elif cmd == "reset-running":
        for t in status["tasks"].values():
            if t["status"] in ("running", "review"):
                t["status"] = "pending"
        status["claude_session_id"] = os.environ.get("CLAUDE_SESSION_ID", status["claude_session_id"])
        save(d, status)
    else:
        sys.exit(f"unknown command: {cmd}\n{__doc__}")


if __name__ == "__main__":
    main(sys.argv[1:])
