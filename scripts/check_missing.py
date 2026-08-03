import pathlib

import yaml

for agent_name in ["antiemetic", "mdt", "orthopedic-surgery", "pharmacy", "togaf"]:
    yf = pathlib.Path(__file__).resolve().parent.parent / "packages" / "haip-hospital" / "agents" / "definitions" / f"{agent_name}.yaml"
    d = yaml.safe_load(yf.read_text(encoding="utf-8"))
    handlers = [t.get("handler","") for t in d.get("tools",[])]
    print(f"=== {agent_name} ===")
    print(f"YAML handlers: {len(handlers)}")
    for h in handlers:
        print(f"  {h}")
    mod_name = agent_name.replace("-", "_")
    init = pathlib.Path(__file__).resolve().parent.parent / "packages" / "haip-hospital" / "modules" / mod_name / "__init__.py"
    if init.exists():
        c = init.read_text(encoding="utf-8")
        funcs = [l.strip().split("(")[0].replace("def ", "") for l in c.splitlines() if "def " in l[:20]]
        print(f"Module functions ({mod_name}/__init__.py): {len(funcs)}")
        for f in funcs[:10]:
            print(f"  def {f}")
        if len(funcs) > 10:
            print(f"  ... +{len(funcs)-10} more")
    print()
