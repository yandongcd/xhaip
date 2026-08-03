"""MDT 辩论效果演示 — 使用 MockProvider 模拟完整辩论流水线。

运行: python scripts/demo_debate.py

模拟场景: 85 岁女性股骨颈骨折 Garden IV，骨科建议"限期手术"，
心内科建议"紧急手术"（心脏风险评估高危）。辩论引擎检测到
surgical_timing 冲突，触发双主持人裁决。
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "haip-core"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "haip-hospital" / "modules"))

from haip.debate.conflict import ConflictDetector
from haip.debate.moderator import Moderator
from haip.debate.protocol import DebateProtocol
from haip.llm.mock import MockProvider


def build_mock_llm():
    """创建预置了辩论裁决对话的 MockProvider。"""

    moderator_a_verdict = json.dumps({
        "consensus": False,
        "resolved_conflicts": [],
        "verdict": "建议采取**紧急手术**（48h内）。依据：1) 心内科提供的心脏风险证据充分——EF=42%+cTnI升高提示围术期心脏事件风险显著；2) 股骨颈Garden IV骨折延迟手术可能加重全身状况恶化。两方的timing分歧本质是对'限期'与'紧急'的定义差异，非实质性临床判断冲突。",
        "rationale": "心内科的风险评估（EF=42% cTnI升高）支持加速手术时机。两方在风险评级上一致（均为高危），分歧仅在timing语义边界。",
        "risk_assessment": "high",
    }, ensure_ascii=False)

    moderator_b_verdict = json.dumps({
        "consensus": True,
        "critical_concerns": ["需额外关注肾功能Cr=142对麻醉药物代谢的影响", "氯吡格雷停药时间是否足够需>=5天"],
        "verdict": "同意紧急手术方向，补充要点：1) 麻醉方式从全麻调整为腰麻加镇静考虑心脏风险；2) 术前确认氯吡格雷停药>=5天；3) 术后ICU监护48h。两方核心判断一致——分歧仅在措辞差异。",
        "rationale": "从麻醉安全角度全麻对EF<50%患者风险过高。抗凝管理是骨科手术常见盲区——患者长期服用氯吡格雷需确保停药充分。",
        "risk_assessment": "high",
    }, ensure_ascii=False)

    appeal_verdict = json.dumps({
        "final_consensus": True,
        "final_verdict": "终裁结论：患者需在48h内进行THA全髋置换术（紧急）。术前管理：1) 心内科会诊完成冠脉评估；2) 确认氯吡格雷停药>=5天；3) 麻醉采用腰麻加镇静；4) 术后ICU监护48h。骨科和心内科核心判断一致——分歧仅在术语边界不影响临床决策。",
        "rationale": "主持人A正确识别了分歧本质（语义而非实质），主持人B补充了关键麻醉和用药安全要点。综合两方意见紧急手术是最优解。",
        "remaining_disagreements": [],
        "risk_assessment": "high",
    }, ensure_ascii=False)

    fixtures = {
        "你是多学科会诊（MDT）的主持人": {"content": moderator_a_verdict, "model": "mock"},
        "你是多学科会诊（MDT）的独立审查员": {"content": moderator_b_verdict, "model": "mock"},
        "终裁": {"content": appeal_verdict, "model": "mock"},
    }

    return MockProvider(fixtures=fixtures)


def main():
    print("=" * 70)
    print("  MDT 多学科辩论 — 效果演示")
    print("  场景: 骨科 (限期手术) vs 心内科 (紧急手术)")
    print("=" * 70)

    llm = build_mock_llm()
    protocol = DebateProtocol()

    # ── Step 1: 模拟 Agent 输出 ──
    agent_outputs = {
        "orthopedic-surgery": (
            "【骨折评估】股骨颈骨折 Garden IV，完全移位，稳定性差。\n"
            "【手术时机】限期手术。患者年龄85岁，合并高血压、冠心病、肾衰，EF=42%。\n"
            "  建议术前优化48-72h，待心内科+肾内科评估后择期THA。\n"
            "【风险评级】高危 — 多系统合并症。\n"
            "【依据】成人股骨颈骨折诊治指南(2018) §3"
        ),
        "cardio-risk": (
            "【心脏评估】EF=42%（前壁运动减弱），cTnI=0.08 ng/mL（临界升高），pro-BNP=5800。\n"
            "【手术时机】建议**紧急手术**（48h内）。延迟手术将增加卧床期间心梗和心衰风险。\n"
            "  EF<50%+cTnI升高提示围术期心脏事件风险高，应尽快手术而非进一步等待。\n"
            "【风险评级】高危 — 心功能不全+肾功能异常(Cr=142)。\n"
            "【依据】ACC/AHA 围术期心血管评估指南"
        ),
    }

    print("[Step 1] Agent 原始输出")
    for agent, output in agent_outputs.items():
        print(f"\n  ── {agent} ──")
        for line in output.split("\n")[:4]:
            print(f"  {line}")

    # ── Step 2: 声明直接创建（demo绕过LLM提取，生产环境由DeclarationLayer处理）──
    print("-" * 70)
    print("[Step 2] 结构化声明 (生产环境由DeclarationLayer LLM提取)")

    from haip.debate.declaration import Declaration
    declarations = [
        Declaration(id="D_ortho_1", agent="orthopedic-surgery", metric="surgical_timing",
                    value="限期手术（48-72h优化后）", category="urgent",
                    evidence="Garden IV + 年龄85 + EF=42% + 多合并症", confidence=0.75),
        Declaration(id="D_ortho_2", agent="orthopedic-surgery", metric="risk_level",
                    value="高危", category="high",
                    evidence="多系统合并症（冠心病+高血压+肾衰）", confidence=0.9),
        Declaration(id="D_cardio_1", agent="cardio-risk", metric="surgical_timing",
                    value="紧急手术（48h内）", category="emergency",
                    evidence="EF=42% + cTnI=0.08临界 + pro-BNP=5800", confidence=0.85),
        Declaration(id="D_cardio_2", agent="cardio-risk", metric="risk_level",
                    value="高危", category="high",
                    evidence="心功能不全 + 肾功能异常(Cr=142)", confidence=0.9),
    ]

    for d in declarations:
        print(f"  [{d.id}] {d.agent}: {d.metric} = {d.value} ({d.category}) "
              f"[conf={d.confidence:.0%}]")

    # ── Step 3: 冲突检测 ──
    print("-" * 70)
    print("[Step 3] 确定性冲突检测 (ConflictDetector — 无 LLM)")
    detector = ConflictDetector()
    conflicts = detector.detect(declarations)

    if conflicts:
        print(f"  [OK] 检测到 {len(conflicts)} 个冲突:")
        for c in conflicts:
            print(f"  {c.summary()}")
    else:
        print("  [OK] 无冲突 — Agent 已达成共识")

    # ── Step 4: 辩论触发 ──
    if not conflicts:
        print("\n  无需辩论，直接输出共识。")
        return

    print("-" * 70)
    print("[Step 4] 辩论触发 — 冲突声明发送给主持人")
    print(f"  {protocol.conflicts_text(conflicts)}")

    # ── Step 5: 双主持人裁决 ──
    print("-" * 70)
    print("[Step 5] 双主持人裁决 (Moderator A vs B)")
    moderator = Moderator(llm)
    decl_text = protocol.declarations_text(declarations)
    conflict_text = protocol.conflicts_text(conflicts)
    vote_a, vote_b = moderator.judge(decl_text, conflict_text)

    print(f"\n  主持人 A (温度=0.2): consensus={'Y' if vote_a.consensus else 'N'}")
    print(f"  裁决: {vote_a.verdict[:120]}...")
    print(f"\n  主持人 B (温度=0.5): consensus={'Y' if vote_b.consensus else 'N'}")
    print(f"  补充关注点: {', '.join(vote_b.critical_concerns[:3])}")

    # ── Step 6: 分歧处理 ──
    votes_agreed = (vote_a.consensus and vote_b.consensus) or (not vote_a.consensus and not vote_b.consensus)
    if votes_agreed:
        print("\n  [OK] 主持人一致 — 无需上诉")
        final_verdict = vote_a.verdict
    else:
        print("\n  [WARN] 主持人分歧 — 触发上诉机制")
        print("\n" + "-" * 70)
        print("[Step 6] 上诉终裁 (Tiebreaker)")
        final = moderator.appeal(vote_a, vote_b, decl_text)
        final_verdict = final.verdict
        print(f"\n  终裁结论: {final_verdict[:150]}...")

    # ── 最终输出 ──
    print("=" * 70)
    print("  最终 MDT 决议")
    print("=" * 70)
    print(f"\n{final_verdict}")
    print(f"\n  主持人一致: {'[OK] 是' if votes_agreed else '[WARN] 否（已上诉）'}")
    print("  共识达成: [OK]")
    print("=" * 70)


if __name__ == "__main__":
    main()
