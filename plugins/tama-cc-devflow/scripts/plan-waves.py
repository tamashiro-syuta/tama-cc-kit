#!/usr/bin/env python3
"""Validate plan.json, detect write-scope conflicts, assign waves, and register tasks in status.json.

Usage: plan-waves.py [--session <id>]

plan.json shape:
{
  "tasks": [
    {
      "id": "T1",
      "title": "...",
      "depends_on": ["T0"],
      "read_scope": ["src/foo/**"],
      "write_scope": ["src/foo/bar.go"],
      "interface_changes": false,
      "db_changes": false,
      "infra_changes": false
    }
  ]
}

Rules:
- depends_on must reference existing tasks; cycles are an error.
- Two tasks with overlapping write_scope and no dependency path between them are a conflict.
  Conflicts are resolved by serializing: the later id depends on the earlier one. Each serialization is reported.
- A task with db_changes or infra_changes is never run in parallel with another such task.
- Wave = longest dependency chain length. Waves larger than MAX_PARALLEL are split by status.py ready at runtime.
Exit code 1 on validation errors.
"""
import fnmatch
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import status as st  # noqa: E402


def normalize(p):
    return p.strip().lstrip("./")


def overlaps(a, b):
    a, b = normalize(a), normalize(b)
    if a == b:
        return True
    if fnmatch.fnmatch(a, b) or fnmatch.fnmatch(b, a):
        return True
    a_dir = a.split("*")[0].rstrip("/")
    b_dir = b.split("*")[0].rstrip("/")
    return bool(a_dir) and bool(b_dir) and (a.startswith(b_dir + "/") or b.startswith(a_dir + "/"))


def reachable(graph, src, dst):
    stack, seen = [src], set()
    while stack:
        n = stack.pop()
        if n == dst:
            return True
        if n in seen:
            continue
        seen.add(n)
        stack.extend(graph[n])
    return False


def main(argv):
    session = None
    if len(argv) >= 2 and argv[0] == "--session":
        session = argv[1]
    d = st.session_dir(session)
    with open(os.path.join(d, "plan.json")) as f:
        plan = json.load(f)
    tasks = {t["id"]: t for t in plan["tasks"]}
    errors = []
    for t in tasks.values():
        for dep in t.get("depends_on", []):
            if dep not in tasks:
                errors.append(f"{t['id']} depends on unknown task {dep}")
        if not t.get("write_scope"):
            errors.append(f"{t['id']} has empty write_scope")
        if not os.path.isfile(os.path.join(d, "tasks", f"{t['id']}.md")):
            errors.append(f"tasks/{t['id']}.md is missing")
    if errors:
        print("\n".join("error: " + e for e in errors), file=sys.stderr)
        sys.exit(1)

    deps = {tid: list(t.get("depends_on", [])) for tid, t in tasks.items()}
    ids = sorted(tasks)
    serialized = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if reachable(deps, a, b) or reachable(deps, b, a):
                continue
            conflict = any(overlaps(x, y) for x in tasks[a]["write_scope"] for y in tasks[b]["write_scope"])
            heavy = (tasks[a].get("db_changes") or tasks[a].get("infra_changes")) and \
                    (tasks[b].get("db_changes") or tasks[b].get("infra_changes"))
            if conflict or heavy:
                deps[b].append(a)
                serialized.append((b, a, "write_scope overlap" if conflict else "db/infra change"))

    waves, visiting = {}, set()

    def wave(tid):
        if tid in waves:
            return waves[tid]
        if tid in visiting:
            print(f"error: dependency cycle at {tid}", file=sys.stderr)
            sys.exit(1)
        visiting.add(tid)
        waves[tid] = 1 + max((wave(x) for x in deps[tid]), default=0)
        visiting.discard(tid)
        return waves[tid]

    for tid in ids:
        wave(tid)

    status = st.load(d)
    status["tasks"] = {
        tid: {
            "title": tasks[tid].get("title", ""),
            "status": status["tasks"].get(tid, {}).get("status", "pending"),
            "depends_on": sorted(set(deps[tid])),
            "write_scope": tasks[tid]["write_scope"],
            "wave": waves[tid],
            "review_rounds": status["tasks"].get(tid, {}).get("review_rounds", 0),
            "design_break": None,
        }
        for tid in ids
    }
    st.save(d, status)

    for b, a, why in serialized:
        print(f"serialized: {b} now depends on {a} ({why})")
    by_wave = {}
    for tid, w in waves.items():
        by_wave.setdefault(w, []).append(tid)
    for w in sorted(by_wave):
        print(f"wave {w}: {', '.join(sorted(by_wave[w]))}")


if __name__ == "__main__":
    main(sys.argv[1:])
