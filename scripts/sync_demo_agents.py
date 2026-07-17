"""Sync AGENTS array in demo HTML from YAML source-of-truth.

Reads all YAML definitions from packages/haip-hospital/agents/definitions/*.yaml,
generates `const AGENTS = [...]` entries, and writes them into
docs/xhaip-agent-demo.html in place of `let AGENTS = [];`.

Also patches loadAgents() to mutate the const array instead of reassigning.
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEF_DIR = ROOT / "packages" / "haip-hospital" / "agents" / "definitions"
HTML_PATH = ROOT / "docs" / "xhaip-agent-demo.html"

# ── Type ordering for sort ──
TYPE_ORDER = {"business": 0, "master_data": 1, "specialist": 2, "architecture": 3}
# Maturity bonus per type (matches loadAgents JS logic)
MAT_BONUS = {"business": 5, "architecture": 10, "specialist": 0, "master_data": 2}


def load_yaml_agents() -> list[dict]:
    """Load all YAML definitions and return list of agent dicts."""
    agents = []
    for f in sorted(DEF_DIR.glob("*.yaml")):
        with open(f, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        agents.append(data)
    return agents


def build_entry(agent: dict) -> str:
    """Build a JS object literal string for one agent."""
    name = agent["name"]
    cn = agent.get("cn_name", name)
    atype = agent.get("type", "business")
    port = agent.get("port", 0)
    dept = agent.get("department", "未知")

    tools = agent.get("tools") or []
    tc = len(tools)
    raw_deps = agent.get("depends_on") or []
    # depends_on can be list-of-dict (YAML) or list-of-str; extract agent names
    depends_on = []
    for d in raw_deps:
        if isinstance(d, dict):
            depends_on.append(d.get("agent", str(d)))
        else:
            depends_on.append(str(d))

    mat = min(100, 60 + min(tc, 10) * 3 + MAT_BONUS.get(atype, 0))

    desc = _synthesize_desc(agent)

    depends_str = "[" + ",".join(f'"{d}"' for d in depends_on) + "]"

    # Build tools list for detail panel
    tools_str = "[" + ",".join(
        "{" + f'name:"{t["name"]}",description:"{_js_escape(t.get("description",""))}"' + "}"
        for t in tools
    ) + "]"

    return (
        f'{{name:"{name}",cn:"{cn}",type:"{atype}",port:{port},'
        f'dept:"{dept}",tags:{tc},desc:"{desc}",mat:{mat},depends_on:{depends_str},tools:{tools_str}}}'
    )


def _synthesize_desc(agent: dict) -> str:
    """Synthesize a short CN description from YAML prompt/tools/cn_name."""
    name = agent.get("cn_name", agent["name"])
    # Strip common suffixes
    for suffix in ["智能体", "评估", "中心", "门户", "管理"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break

    tools = agent.get("tools") or []
    if tools:
        # Use first 2-3 tool descriptions
        tool_descs = [t.get("description", "") for t in tools[:3]]
        # Extract short labels from tool descriptions
        labels = []
        for td in tool_descs:
            # Take first meaningful phrase
            parts = td.split("—") if "—" in td else [td]
            label = parts[0].strip()
            if len(label) > 20:
                label = label[:20] + "…"
            if label:
                labels.append(label)

        if labels:
            return name + "：" + " / ".join(labels)

    # Fallback: use system prompt first sentence
    prompt = agent.get("prompt", {})
    system = prompt.get("system", "") if isinstance(prompt, dict) else ""
    if system:
        lines = system.strip().split("。")
        first = lines[0].replace("\n", " ").strip()
        if len(first) > 40:
            first = first[:40] + "…"
        return f"{name}：{first}"

    return name + "：南方医院AI智能助手"


def _js_escape(s: str) -> str:
    """Escape a string for inclusion in a JS string literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def main():
    # 1. Load YAML
    yaml_agents = load_yaml_agents()
    print(f"Loaded {len(yaml_agents)} YAML agent definitions")

    # 2. Sort by type then by maturity
    entries_raw = []
    for a in yaml_agents:
        tc = len(a.get("tools") or [])
        atype = a.get("type", "business")
        mat = min(100, 60 + min(tc, 10) * 3 + MAT_BONUS.get(atype, 0))
        entries_raw.append((a, mat))

    entries_raw.sort(key=lambda x: (
        TYPE_ORDER.get(x[0].get("type", "business"), 99),
        -x[1],
    ))

    # 3. Build JS array text
    lines = ["const AGENTS = ["]
    for agent, _mat in entries_raw:
        lines.append(f"  {build_entry(agent)},")
    lines.append("];")

    agents_array_text = "\n".join(lines)

    # 4. Read HTML
    html = HTML_PATH.read_text(encoding="utf-8")
    original = html

    # 5. Replace existing AGENTS array block (let or const) with new one
    if "let AGENTS = [];" in html:
        html = html.replace("let AGENTS = [];", agents_array_text)
        print("Replaced 'let AGENTS = [];' with YAML-synced const AGENTS array")
    elif "const AGENTS = [" in html:
        # Re-run: find and replace the existing const AGENTS = [...]; block
        html = re.sub(
            r"const AGENTS = \[.*?\];",
            agents_array_text,
            html, count=1, flags=re.DOTALL
        )
        print("Replaced existing 'const AGENTS = [...];' with YAML-synced array")
    else:
        print("ERROR: Neither 'let AGENTS = [];' nor 'const AGENTS = [' found in HTML")
        sys.exit(1)

    # 6. Fix loadAgents() to not reassign const AGENTS
    #    Change: AGENTS = raw.map(a => { ... });
    #    To:      AGENTS.length = 0; raw.map(a => { ... }).forEach(x => AGENTS.push(x));
    old_reassign = "AGENTS = raw.map(a => {"
    if old_reassign in html:
        new_reassign = "AGENTS.length = 0; raw.map(a => {"
        html = html.replace(old_reassign, new_reassign)
        print("Patched loadAgents: AGENTS.length = 0 instead of reassign")

        # Also need to close it: after map callback, instead of:
        #   });
        #   AGENTS.sort(...);
        # We need:
        #   }).forEach(x => AGENTS.push(x));
        # But the structure is more complex. Let me find the closing pattern.

        # After the map callback, the code is:
        #   });
        #   AGENTS.sort((a, b) => b.mat - a.mat);
        # We need to change `});` to `}).forEach(x => AGENTS.push(x));`

        # Find the specific closing of the map:
        # Looking for:   });
        # Followed by:   AGENTS.sort
        pattern = re.compile(r"(AGENTS\.length = 0; raw\.map\(a => \{.*?\}\);)\s*\n\s*(AGENTS\.sort)", re.DOTALL)
        m = pattern.search(html)
        if m:
            old_block = m.group(1)
            new_block = old_block.replace("});", "}).forEach(x => AGENTS.push(x));")
            html = html[:m.start()] + new_block + "\n      " + m.group(2) + html[m.end():]
            print("Patched loadAgents: added .forEach(x => AGENTS.push(x))")
        else:
            # Try simpler approach: find exact pattern
            # The structure is:
            #       AGENTS.length = 0; raw.map(a => {
            #         ...
            #         return { ... };
            #       });
            #       AGENTS.sort(...)
            match = re.search(
                r"(AGENTS\.length = 0; raw\.map\(a => \{.*?return \{.*?\};\s*\}\);)",
                html, re.DOTALL
            )
            if match:
                old_chunk = match.group(1)
                new_chunk = old_chunk.rstrip(";") + ".forEach(x => AGENTS.push(x));"
                html = html.replace(old_chunk, new_chunk, 1)
                print("Patched loadAgents: appended .forEach(x => AGENTS.push(x))")
            else:
                print("WARNING: Could not pattern-match loadAgents map closing")
    else:
        print("WARNING: Could not find 'AGENTS = raw.map(a => {' to patch loadAgents")

    # 7. Write back
    if html != original:
        HTML_PATH.write_text(html, encoding="utf-8")
        print(f"Written updated HTML: {len(html)} chars")
    else:
        print("No changes made to HTML")

    # 8. Summary
    types_seen = {}
    for a in yaml_agents:
        t = a.get("type", "business")
        types_seen[t] = types_seen.get(t, 0) + 1
    print(f"Agent types: {types_seen}")
    print("Done.")


if __name__ == "__main__":
    main()
