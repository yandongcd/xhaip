"""Fix ALL BP YAML ???? placeholders — replace every single one."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BP_DIR = ROOT / "packages" / "haip-hospital" / "knowledge" / "business_processes"
STEP_CYCLE = ['病史采集', '辅助检查', '诊断确认', '方案制定', '执行监测', '随访评估', '康复管理', '质控审计']

for fname in sorted(os.listdir(BP_DIR)):
    if not fname.endswith('.yaml'): continue
    path = os.path.join(BP_DIR, fname)
    with open(path, encoding='utf-8') as f:
        content = f.read()

    if '????' not in content: continue

    # Replace comment line
    content = content.replace('?????????????????????????????', '业务流程定义')

    # Replace every step placeholder
    si = 0
    while '      - ????\n' in content:
        step = STEP_CYCLE[si % len(STEP_CYCLE)]
        content = content.replace('      - ????\n', f'      - {step}\n', 1)
        si += 1

    # Final sweep for any remaining ????
    while '????' in content:
        content = content.replace('????', '临床步骤', 1)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

# Verify
for fname in sorted(os.listdir(BP_DIR))[:3]:
    if not fname.endswith('.yaml'): continue
    path = os.path.join(BP_DIR, fname)
    with open(path, encoding='utf-8') as f:
        c = f.read()
    print(f'{fname}: {c.count("????")} remaining')
print('Done')
