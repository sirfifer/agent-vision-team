#!/usr/bin/env python3
"""Fast scale assessment for project bootstrapper.

Runs deterministic CLI tools (find, wc, ls) to profile a project's size,
languages, and structure. Completes in under 5 seconds even for 500K LOC.

Usage:
    python scripts/bootstrap-scale-check.py /path/to/project

Output: JSON to stdout with the scale profile.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

# Directories to always exclude from analysis
EXCLUDED_DIRS = [
    "node_modules",
    ".git",
    "vendor",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".next",
    ".nuxt",
    "target",  # Rust/Java
    ".gradle",
    ".idea",
    ".vscode",
]

# Source file extensions to count
SOURCE_EXTENSIONS = [
    "py", "ts", "tsx", "js", "jsx", "swift", "rs", "go", "java",
    "rb", "kt", "cs", "cpp", "c", "h", "hpp", "m", "mm",
    "vue", "svelte", "scala", "clj", "ex", "exs", "hs",
]

# Package boundary files (indicate a self-contained package/module)
PACKAGE_FILES = [
    "package.json", "pyproject.toml", "setup.py", "Cargo.toml",
    "go.mod", "pom.xml", "build.gradle", "Package.swift",
    "Gemfile", "mix.exs", "build.sbt",
]

# Monorepo indicator files
MONOREPO_FILES = [
    "pnpm-workspace.yaml", "lerna.json", "turbo.json", "nx.json",
    "rush.json",
]

# Config files for convention detection
CONFIG_FILES = [
    ".eslintrc*", ".prettierrc*", "ruff.toml", "pyproject.toml",
    "tsconfig.json", ".editorconfig", ".swiftformat", ".swiftlint.yml",
    ".clang-format", "Makefile", "Justfile", ".rubocop.yml",
    "biome.json", "deno.json",
]

# Scale tier thresholds
TIERS = [
    ("Small", 10_000, 100),
    ("Medium", 100_000, 1_000),
    ("Large", 500_000, 5_000),
    ("Massive", 2_000_000, 20_000),
    ("Enterprise", float("inf"), float("inf")),
]


def _run(cmd: str, cwd: str, timeout: int = 10) -> str:
    """Run a shell command and return stdout, empty string on failure."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, Exception):
        return ""


def _build_find_exclude(root: str) -> str:
    """Build the -not -path exclusion clauses for find."""
    parts = []
    for d in EXCLUDED_DIRS:
        parts.append(f'-not -path "*/{d}/*"')
    return " ".join(parts)


def assess_scale(project_path: str) -> dict:
    """Run fast scale assessment and return a profile dict."""
    root = Path(project_path).resolve()
    if not root.is_dir():
        return {"error": f"Not a directory: {project_path}"}

    root_str = str(root)
    exclude = _build_find_exclude(root_str)

    # 1. Source files by extension
    ext_list = " -o ".join(f'-name "*.{ext}"' for ext in SOURCE_EXTENSIONS)
    ext_clause = f"\\( {ext_list} \\)" if ext_list else ""
    find_src = f'find "{root_str}" -type f {ext_clause} {exclude}'

    # Count by extension
    count_cmd = f"{find_src} | sed 's/.*\\.//' | sort | uniq -c | sort -rn"
    count_output = _run(count_cmd, root_str)

    languages = []
    total_files = 0
    for line in count_output.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            count = int(parts[0])
            ext = parts[1]
            languages.append({"extension": ext, "count": count})
            total_files += count

    # 2. Total source LOC
    loc_cmd = f"{find_src} | xargs wc -l 2>/dev/null | tail -1"
    loc_output = _run(loc_cmd, root_str, timeout=30)
    total_loc = 0
    if loc_output:
        parts = loc_output.strip().split()
        if parts:
            try:
                total_loc = int(parts[0])
            except ValueError:
                pass

    # 3. Documentation files
    doc_cmd = f'find "{root_str}" -type f \\( -name "*.md" -o -name "*.rst" -o -name "*.txt" \\) {exclude} | wc -l'
    doc_output = _run(doc_cmd, root_str)
    doc_files = int(doc_output) if doc_output.strip().isdigit() else 0

    # 4. Top-level directory count
    top_dirs_cmd = f'ls -d "{root_str}"/*/ 2>/dev/null | wc -l'
    top_dirs_output = _run(top_dirs_cmd, root_str)
    top_level_dirs = int(top_dirs_output) if top_dirs_output.strip().isdigit() else 0

    # 5. Package boundaries
    pkg_names = " -o ".join(f'-name "{pf}"' for pf in PACKAGE_FILES)
    pkg_clause = f"\\( {pkg_names} \\)"
    pkg_cmd = f'find "{root_str}" -maxdepth 4 {pkg_clause} {exclude} 2>/dev/null'
    pkg_output = _run(pkg_cmd, root_str)
    packages = [p.strip() for p in pkg_output.splitlines() if p.strip()]

    # 6. Monorepo indicators
    mono_names = " -o ".join(f'-name "{mf}"' for mf in MONOREPO_FILES)
    mono_clause = f"\\( {mono_names} \\)"
    mono_cmd = f'find "{root_str}" -maxdepth 2 {mono_clause} 2>/dev/null'
    mono_output = _run(mono_cmd, root_str)
    monorepo_indicators = [m.strip() for m in mono_output.splitlines() if m.strip()]

    # Also check for Cargo workspace
    cargo_toml = root / "Cargo.toml"
    if cargo_toml.exists():
        content = cargo_toml.read_text(errors="ignore")
        if "[workspace]" in content:
            monorepo_indicators.append(str(cargo_toml))

    # 7. Config files
    config_results = []
    for pattern in CONFIG_FILES:
        cfg_cmd = f'find "{root_str}" -maxdepth 3 -name "{pattern}" {exclude} 2>/dev/null'
        cfg_output = _run(cfg_cmd, root_str)
        for line in cfg_output.splitlines():
            if line.strip():
                config_results.append(line.strip())

    # Classify tier
    tier = "Small"
    for tier_name, loc_threshold, file_threshold in TIERS:
        if total_loc < loc_threshold or total_files < file_threshold:
            tier = tier_name
            break

    # Estimate time and agents
    language_count = len(languages)
    package_count = len(packages)

    if tier == "Small":
        estimated_time = 5
        estimated_agents = 0  # Inline analysis
    else:
        doc_items = max(1, math.ceil(doc_files / 25))
        structure_items = max(1, package_count) if package_count > 0 else max(1, top_level_dirs)
        pattern_items = max(1, math.ceil(total_files / 400))
        convention_items = max(1, language_count)

        total_items = doc_items + structure_items + pattern_items + convention_items
        # Add aggregators: 4 phase aggregators + 1 synthesizer minimum
        aggregators = 5
        # Wave aggregators if any phase > 20
        for count in [doc_items, structure_items, pattern_items, convention_items]:
            if count > 20:
                aggregators += math.ceil(count / 15)

        estimated_agents = total_items + aggregators

        # Wall time: bottleneck phase waves * 2min + patterns + aggregation + synthesis
        max_waves = max(
            math.ceil(doc_items / 15),
            math.ceil(structure_items / 15),
            math.ceil(convention_items / 15),
        )
        pattern_waves = math.ceil(pattern_items / 15)
        estimated_time = (max_waves * 2) + (pattern_waves * 2) + 4  # +4 for aggregation+synthesis

    return {
        "sourceFiles": total_files,
        "sourceLoc": total_loc,
        "docFiles": doc_files,
        "topLevelDirs": top_level_dirs,
        "languages": languages,
        "packages": [str(Path(p).relative_to(root)) for p in packages],
        "monorepoIndicators": [str(Path(m).relative_to(root)) for m in monorepo_indicators if Path(m).is_relative_to(root)],
        "configFiles": [str(Path(c).relative_to(root)) for c in config_results if Path(c).is_relative_to(root)],
        "tier": tier,
        "estimatedTimeMinutes": estimated_time,
        "estimatedAgents": estimated_agents,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: bootstrap-scale-check.py <project_path>"}))
        sys.exit(1)

    profile = assess_scale(sys.argv[1])
    print(json.dumps(profile, indent=2))
