"""Skill sync: source modules -> .openharness/skills/ runtime directory.

Convention:
  1. Skills live in agent/module source directories as SKILL.md files.
  2. Synced to runtime: .openharness/skills/<skill-name>/
  3. Source is the single source of truth; runtime is a mirror.
  4. SKILL_OWNERSHIP registry maps source_path -> runtime_name.

Usage:
    python -m haip.operations.skill_sync            # show diff (dry-run)
    python -m haip.operations.skill_sync --apply     # actually sync
    python -m haip.operations.skill_sync --validate  # check consistency
"""

from __future__ import annotations

import filecmp
import shutil
import sys
from pathlib import Path
from typing import Any


def _discover_project_root() -> Path:
    current = Path(__file__).resolve().parents[3]
    markers = [".openharness", "packages", "pyproject.toml"]
    if any((current / m).exists() for m in markers):
        return current
    cwd = Path.cwd()
    for m in markers:
        if (cwd / m).exists():
            return cwd
    return current


PROJECT_ROOT = _discover_project_root()
SKILLS_RUNTIME_DIR = PROJECT_ROOT / ".openharness" / "skills"

# -- Skill ownership registry --
# source_path (relative to PROJECT_ROOT) -> runtime_name
# Add entries here for any module/department that owns skills.
SKILL_OWNERSHIP: dict[str, str] = {
    # Architecture / core
    "packages/haip-core": "xhaip-core",
    # Department agents (haip-hospital)
    "packages/haip-hospital/agents/definitions/pharmacy": "xhaip-pharmacy",
    "packages/haip-hospital/agents/definitions/orthopedic-surgery": "xhaip-orthopedic",
    "packages/haip-hospital/agents/definitions/cardio-surgery": "xhaip-cardio",
    "packages/haip-hospital/agents/definitions/cardio-risk": "xhaip-cardio",
    "packages/haip-hospital/agents/definitions/anesthesia-risk": "xhaip-anesthesia",
    "packages/haip-hospital/agents/definitions/pain-hub": "xhaip-pain",
    "packages/haip-hospital/agents/definitions/pediatrics": "xhaip-pediatrics",
    "packages/haip-hospital/agents/definitions/medical-record": "xhaip-masterdata",
    "packages/haip-hospital/agents/definitions/metrics": "xhaip-masterdata",
}


def _ensure_utf8_stdout() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def _resolve_source_path(rel: str) -> Path:
    return (PROJECT_ROOT / rel).resolve()


def _resolve_runtime_path(name: str) -> Path:
    return (SKILLS_RUNTIME_DIR / name).resolve()


def _find_skill_md_in_dir(path: Path) -> Path | None:
    """Find SKILL.md in a directory or its 'skills' subdirectory."""
    candidates = [
        path / "SKILL.md",
        path / "skills" / "SKILL.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def auto_discover_skills() -> dict[str, str]:
    """Walk packages/ for SKILL.md files and return ownership mapping.

    Returns a dict compatible with SKILL_OWNERSHIP: source_path -> skill_name.
    Only discovers skills NOT already in SKILL_OWNERSHIP.
    """
    discovered: dict[str, str] = dict(SKILL_OWNERSHIP)
    search_roots = [
        PROJECT_ROOT / "packages",
    ]
    for search_root in search_roots:
        if not search_root.exists():
            continue
        for skill_file in search_root.rglob("SKILL.md"):
            parent = skill_file.parent
            try:
                rel_dir = parent.relative_to(PROJECT_ROOT)
            except ValueError:
                continue
            rel_str = str(rel_dir).replace("\\", "/")

            # Skip already-registered paths
            if any(
                s.replace("\\", "/") == rel_str
                or rel_str.startswith(s.replace("\\", "/") + "/")
                for s in discovered
            ):
                continue

            # Derive skill name from directory name
            skill_name = rel_dir.parent.name if parent.name == "skills" else parent.name
            skill_name = skill_name.replace("_", "-").replace(" ", "-").lower()
            if not skill_name.startswith("xhaip-"):
                skill_name = f"xhaip-{skill_name}"
            discovered[rel_str] = skill_name

    return discovered


def sync(dry_run: bool = True) -> dict[str, Any]:
    """Sync skills from source to runtime. Returns summary dict."""
    _ensure_utf8_stdout()
    ownership = auto_discover_skills()
    changed = 0
    missing_src = 0
    skipped_dirs: list[str] = []

    for src_rel, runtime_name in sorted(ownership.items()):
        src = _resolve_source_path(src_rel)
        dst = _resolve_runtime_path(runtime_name)

        # Find SKILL.md in the source directory
        skill_src = _find_skill_md_in_dir(src)
        if skill_src is None:
            print(f"[SKIP] No SKILL.md found: {src_rel}")
            missing_src += 1
            continue

        # Check if runtime dir has SKILL.md and content matches
        dst_md = dst / "SKILL.md"
        if dst_md.exists() and filecmp.cmp(skill_src, dst_md, shallow=False):
            continue  # already in sync

        if dry_run:
            print(f"[DRY-RUN] Would sync: {src_rel}/SKILL.md  ->  .openharness/skills/{runtime_name}/SKILL.md")
            changed += 1
        else:
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(skill_src, dst_md)
            # Also copy any supporting files from source dir
            for extra_file in skill_src.parent.glob("*"):
                if extra_file.name != "SKILL.md" and extra_file.is_file():
                    shutil.copy2(extra_file, dst / extra_file.name)
            print(f"[SYNC] {src_rel}/SKILL.md  ->  .openharness/skills/{runtime_name}/")
            # Check for orphaned directories in source
            for orphan_dir in skill_src.parent.glob("*/"):
                if orphan_dir.name != "SKILL.md":
                    pass
            changed += 1

    # Check for extra runtime dirs not in ownership
    known_names = set(ownership.values())
    if SKILLS_RUNTIME_DIR.exists():
        for rt_dir in SKILLS_RUNTIME_DIR.iterdir():
            if rt_dir.is_dir() and rt_dir.name not in known_names:
                if not rt_dir.name.startswith("_"):
                    skipped_dirs.append(rt_dir.name)

    if changed == 0 and missing_src == 0:
        print("[OK] All skills are in sync." if not dry_run else "[OK] Nothing to sync.")
    elif dry_run:
        print(f"\n[DRY-RUN] {changed} skill(s) need sync, {missing_src} source(s) missing.")
    else:
        print(f"\n[SYNC] {changed} skill(s) synced, {missing_src} source(s) missing.")

    if skipped_dirs:
        print(f"[INFO] {len(skipped_dirs)} runtime dir(s) without source: {', '.join(skipped_dirs)}")

    return {
        "changed": changed,
        "missing_src": missing_src,
        "skipped_runtime": len(skipped_dirs),
        "total_owned": len(ownership),
    }


def validate() -> int:
    """Validate skill sync consistency. Returns number of issues."""
    _ensure_utf8_stdout()
    ownership = auto_discover_skills()
    issues = 0

    for src_rel, runtime_name in sorted(ownership.items()):
        src = _resolve_source_path(src_rel)
        dst = _resolve_runtime_path(runtime_name)

        skill_src = _find_skill_md_in_dir(src)
        if skill_src is None:
            print(f"[FAIL] Source missing SKILL.md: {src_rel}")
            issues += 1
            continue

        dst_md = dst / "SKILL.md"
        if not dst_md.exists():
            print(f"[FAIL] Runtime missing: .openharness/skills/{runtime_name}/SKILL.md")
            issues += 1
            continue

        if not filecmp.cmp(skill_src, dst_md, shallow=False):
            print(f"[FAIL] SKILL.md out of sync: {src_rel}/SKILL.md")
            print("       Run `xhaip sync-skills --apply` to fix.")
            issues += 1

    if issues == 0:
        print(f"[PASS] All {len(ownership)} owned skills are synced.")
    else:
        print(f"\n[WARN] {issues} issue(s) found.")

    return issues


def init_from_runtime() -> int:
    """Initial setup: copy all owned skills from runtime -> source.
    Run this once when first establishing the convention.
    """
    _ensure_utf8_stdout()
    ownership = auto_discover_skills()
    created = 0
    for src_rel, runtime_name in sorted(ownership.items()):
        src = _resolve_source_path(src_rel)
        dst = _resolve_runtime_path(runtime_name)

        dst_md = dst / "SKILL.md"
        if not dst_md.exists():
            print(f"[SKIP] Runtime missing: .openharness/skills/{runtime_name}/SKILL.md")
            continue

        skill_src_md = _find_skill_md_in_dir(src)
        if skill_src_md is not None:
            print(f"[SKIP] Already exists: {src_rel}/SKILL.md")
            continue

        # Copy from runtime to source
        src.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dst_md, src / "SKILL.md")
        print(f"[INIT] Runtime -> source: .openharness/skills/{runtime_name}/SKILL.md  ->  {src_rel}/SKILL.md")
        created += 1

    print(f"\n[INIT] Copied {created} skill(s) from runtime to source.")
    return 0


def list_skills() -> dict[str, Any]:
    """List all skills in the runtime directory with metadata."""
    result: dict[str, Any] = {"skills": [], "count": 0}
    if not SKILLS_RUNTIME_DIR.exists():
        return result

    for skill_dir in sorted(SKILLS_RUNTIME_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("_") or skill_dir.name.endswith(".md"):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        info: dict[str, Any] = {"name": skill_dir.name, "files": []}
        for f in sorted(skill_dir.iterdir()):
            info["files"].append({"name": f.name, "size": f.stat().st_size if f.is_file() else 0})
        # Parse frontmatter
        try:
            content = skill_md.read_text(encoding="utf-8")
            if content.startswith("---"):
                end = content.index("---", 3)
                for line in content[3:end].strip().split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        info[k.strip()] = v.strip()
        except (ValueError, UnicodeDecodeError):
            pass
        result["skills"].append(info)

    result["count"] = len(result["skills"])
    return result


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Sync skills between source and runtime")
    parser.add_argument("--apply", action="store_true", help="Sync source -> runtime (default is dry-run)")
    parser.add_argument("--validate", action="store_true", help="Check consistency only")
    parser.add_argument("--init", action="store_true", help="Initial setup: copy runtime -> source")
    parser.add_argument("--list", action="store_true", help="List all registered skills")
    args = parser.parse_args()

    if args.validate:
        return validate()
    if args.init:
        return init_from_runtime()
    if args.list:
        import json
        print(json.dumps(list_skills(), ensure_ascii=False, indent=2))
        return 0
    sync(dry_run=not args.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
