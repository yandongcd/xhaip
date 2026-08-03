# xhaip 语音链路评估报告 — Corti Symphony vs 开源替代

> 日期: 2026-08-03 | 状态: 决策点评估 (未实施)
> 背景: 业界语音病历赛道已进入论文级工程验证 (Symphony 2026-05), xhaip 无任何语音能力

## 1. 候选方案

| 维度 | **Corti Symphony** (2605.16545) | **MultiMed 系列** (leduckhai, 379★) | 自研 (Whisper 微调) |
|---|---|---|---|
| 来源 | 商业 API (production-grade) | 开源 (EMNLP 2025 / ACL 2025 / NAACL 2025) | 开源基座 + 自训 |
| 能力 | 流式/批处理 STT, 临床结构化文本 | 多语言医学 ASR/NER/摘要/翻译 (MultiMed-ST) | 需自建管道 |
| 中文支持 | 未证实 (Corti 主欧美市场) | ⚠️ 多语言含中文, 但医学中文语料覆盖待验证 | 可控 |
| 许可 | 商业订阅 (成本不可控) | ⚠️ GitHub license 字段 null (需联系作者确认) | 无限制 |
| 集成成本 | 低 (API 调用) | 中 (自托管推理) | 高 (训练/标注) |
| 数据合规 | 数据出境风险 (医院 PHI) | 可私有化部署 | 完全私有化 |
| 成熟度 | 生产级 (论文+API) | 论文级 (代码可用) | 不确定 |

## 2. 关键决策因素 (对 xhaip)

1. **医院 PHI 合规** → 私有化部署是硬约束; Corti 商业 API 存在数据出境风险 → **Corti 不适合作为主选**
2. **中文医学语音** → MultiMed 有中文但医学领域覆盖未验证; 实测成本未知
3. **xhaip 当前阶段** → 语音是 P3 级增强 (在评测/进化/病历之后), 需求优先级低

## 3. 推荐路径

```
阶段 A (现在, 零成本): 架构预留 — 定义 STTProvider 抽象 (同 LLMProvider 模式)
阶段 B (有需求时): MultiMed 自托管 PoC — 中文医学 ASR 基准实测 (CER/WER)
阶段 C (PoC 通过): 接入 haip/clinical/notes.py 事实提取 (语音 → 文本 → Facts)
阶段 D (可选): Corti API 作为云端备选 (非 PHI 场景)
```

**结论**: 不建议现在实施。优先完成 STTProvider 抽象预留 (S 工作量), 待评测/进化能力稳定后按需启动 MultiMed PoC。

## 4. 前置依赖

- `haip/clinical/notes.py` (FactsR 移植) 已就绪 — 语音文本可直接接入事实提取
- 需要新增: `haip/speech/` 抽象层 (STTProvider ABC + Mock + MultiMed 适配器)
