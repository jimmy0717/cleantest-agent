# CleanTest-Agent PPT 大纲（10 页 · 3 分钟课堂汇报）

> 与 `report/main.tex` 和 `ppt/slides.md` 完全对齐。
> RQ2/RQ4 实验数据来自 2026-05-18 的 DeepSeek-V4-Flash 真实 API 实验
> （`experiments/results/baseline_results.json`、`experiment_summary.md`）。
> Filter 3 模型模式数据来自 A800 80GB 上微调 Qwen2.5-Coder-0.5B
> 的 hold-out 测试集（`experiments/results/coverage_run/qwen_0p5b_a800/`）。

作业要求覆盖检查（每页都至少命中其中一项）：

- [选题] P1, P2
- [智能模型驱动方法] P3, P4
- [实现技术细节] P4, P5
- [实验评估：智能模型驱动 vs 纯大模型] P6, P7, P8
- [亮点：新方法或对已有方法的改进] P4 (Reflection 5 条规则)、P5 (Aho-Corasick 加速)、P10 (Filter 3 微调 Qwen2.5-Coder-0.5B)
- [软件工程实践] P9

---

## 第 1 页：封面（约 10 秒）

标题：**CleanTest-Agent -- A Multi-Agent Skill-Orchestrated System
for Unit Test Training Data Quality Assurance**

- 作者：Yong Yang
- 单位：School of Software, Beihang University
- 邮箱：yang_qhd@buaa.edu.cn
- 课程：Software Requirements Analysis & System Design -- Final Project

讲解要点：
- 一句话定位：本项目把 CleanTest（FSE 2025）的单体清洗脚本，重新设计成
  一个可被 CodeBuddy / Claude Code / Cursor 自然语言触发的多智能体技能编排系统。

---

## 第 2 页：选题与动机（约 20 秒）

标题：**43.52% of Methods2Test Training Data Are Noise**

左侧（背景）：
- AI 测试生成模型（CodeBERT、AthenaTest、StarCoder、CodeLlama-7B 等）
  依赖大规模数据集，但训练数据本身有质量问题。
- Methods2Test：91,385 个开源项目，780,944 条 focal-method ↔ test-case 对。
- CleanTest（FSE 2025 Distinguished Paper）发现 43.52% 的样本至少包含一种噪声。
- 过滤噪声后，下游模型在 Defects4J 上的分支覆盖率平均提升约 67%。

右侧（噪声分布饼图，原论文 Table 5）：
- Unnecessary Annotations: 41.64%
- No Relevance: 12.70%
- Low Coverage: 3.95%
- Ambiguous Data Type: 3.08%
- Syntax Errors: 1.11%
- Empty Exception Handling: 0.68%
- Missing Implementation: 0.34%
- Non-English Literals: 0.16%

底部 -- 原 CleanTest 实现的痛点：
- 单体 Python 脚本，无测试，不可复用；
- 无法被现代 AI Coding Assistant 直接调用；
- 朴素字典匹配在 593 K 样本上跑约 30 分钟。

讲解要点：
- 强调数据质量问题的严重性（近一半样本有问题）。
- 指出原始 CleanTest 工程化不足，正是本项目的切入点。

---

## 第 3 页：系统架构（约 25 秒）

标题：**CleanTest-Agent: Pipeline-of-Skills**

中央内容：架构图

```
User / Coding Assistant (natural language)
                |
                v
   Orchestrator Skill (cleantest-pipeline)
        |          |          |
        v          v          v
   Filter 1   Filter 2    Filter 3
   Syntax     Relevance   Coverage
   AST +      NameMatch   label scan (default) /
   Aho-       + LLM       Qwen2.5-Coder-0.5B
   Corasick   fallback    (model mode)
        |          |          |
        +----------+----------+
                   v
        Clean Dataset + Noise Report
```

要点标注：
- 4 个独立的 Agent Skill（共用 SKILL.md 协议）：
  pipeline / syntax-filter / relevance-filter / coverage-filter。
- Filter 3 提供两种模式：**label 模式**（有 JaCoCo 标签时直接行扫描，
  默认走这条）；**model 模式**（无标签时走微调的 Qwen2.5-Coder-0.5B）。
- 兼容 CodeBuddy / Claude Code / Cursor。

讲解要点：
- 把单体脚本拆成 4 个可组合、可独立调用、可独立测试的 Skill。
- 通过自然语言即可触发整个流水线。

---

## 第 4 页：核心方法 -- Model-Driven（约 30 秒）

标题：**Right Tool for the Right Subtask + Reflection on Borderlines**

三列布局：

| Rules（确定性） | ML Model（学习） | LLM（语义） |
|---|---|---|
| AST + Aho-Corasick + 正则 | Filter 3 label-mode：JaCoCo 标签行扫描（默认）；model-mode：Qwen2.5-Coder-0.5B 在 469K 样本上微调 | DeepSeek-V4-Flash |
| 21,954 个注解模式，100% recall | $O(N)$ 单次扫描（label 模式）；微调 0.5B 参数（model 模式） | 仅处理边界样本 |
| ~0.2 ms/样本 | $0 成本（label 模式） | ~12.7% 样本，约 3 s/样本 |

下半部分 -- **Reflection 机制（Filter 2 的方法改进，亮点之一）**：
- 灵感来自课程 Lab 1 的 Reflection Agent 模式。
- 当 LLM 给出 IRRELEVANT 时，触发结构化 5 条规则自检：
  Call Graph（Tufano 2022 的扩展）、State Verification（Meszaros 2007）、
  Behavior Verification（Meszaros 2007）、Naming Equivalence、Counterfactual。
- 在 45 条零重叠样本上验证：7 条判决被翻转（15.6% 改判率），
  其中 5 条从误删中被救回（11.1% 救回率），
  人工核对 6/7 翻转正确（85.7% 正确率）。

设计模式：Strategy / Pipeline / Facade / Reflection（5 个滤波器选择 / 串联 / LLM-客户端封装 / 自纠错）。

讲解要点：
- 核心创新：不用一个 LLM 解决所有问题。
- 规则处理确定性模式（最快、最准、最便宜）；ML 处理可学习的回归任务；
  LLM 仅处理 ~12.7% 的边界 case，并且在边界上额外做一次 5 条规则的反思。

---

## 第 5 页：关键优化 -- Aho-Corasick（约 15 秒）

标题：**Aho-Corasick：Pipeline 加速约 11.5×（Filter 1 单阶段约 18.8×）**

| | Naïve | Aho-Corasick |
|---|---|---|
| 复杂度 | $O(N \cdot K \cdot L)$ | $O(N \cdot (L + Z))$ |
| K = 21,954 模式 | 每条样本扫所有模式 | 单次自动机扫描 |
| Filter 1 时间（593K） | ~30 min | ~1.6 min |
| 整个 Pipeline | ~31 min | ~2.6 min |
| 过滤结果 | 53.97% removed | 53.97% removed（完全一致） |

视觉元素：自动机状态转换示意图 + 时间对比柱状图。

讲解要点：
- 经典算法在工程实践中的价值。
- 正确性不变，速度提升约 11.5 倍（Filter 1 单阶段约 18.8×）。

---

## 第 6 页：实验设计（约 15 秒）

标题：**Experiment Design -- 4 Research Questions**

- **RQ1**：CleanTest-Agent 是否复现了原始 CleanTest 的检测结果？
- **RQ2**：Model-Driven 与纯 LLM 相比表现如何？
- **RQ3**：Aho-Corasick 优化的实际加速比？
- **RQ4**：成本/速度对比？

对比方法（4 类）：
1. Rule-based only（原始 CleanTest 等价）
2. LLM zero-shot（DeepSeek-V4-Flash）
3. LLM few-shot（DeepSeek-V4-Flash）
4. **Hybrid（本系统）**：Rules + selective LLM；Filter 3 label 模式

数据集：
- 主实验：Methods2Test 中分层抽样的 500 条样本，DeepSeek 真实 API 验证。
- Filter 3 模型模式：`filter_train.csv` 469,174 行，80/10/10 stratified 切分，
  在单卡 A800 80GB 上 bf16 微调 Qwen2.5-Coder-0.5B。

讲解要点：
- 4 个 RQ 对应四个维度：复现性、方法对比、性能、成本/效率。
- 真实 API + 真实 GPU 训练，非模拟数据。

---

## 第 7 页：实验结果（约 25 秒）

标题：**Results -- Rules + Selective LLM 显著优于 Pure LLM**

| Method | Prec. | Recall | F1 | Time (500 条) |
|--------|-------|--------|------|-----------|
| Rule-based | 1.000 | 1.000 | 1.000 | 0.11 s |
| LLM zero-shot | 0.505 | 0.221 | 0.307 | 1,487 s |
| LLM few-shot | 0.534 | 0.303 | 0.387 | 1,642 s |
| **Hybrid (ours)** | **0.974** | **0.956** | **0.965** | **< 60 s** |

关键数字：
- F1：0.965 vs. 0.387（约 +149%）。
- 速度：0.11 s vs. 1,642 s（约 13,000–15,000× 倍）。
- LLM zero-shot 漏检率约 77.9%（FN 180/231）；
  其中 87.8% 漏检都是 unnecessary-annotations 类。

讲解要点：
- 真实实验证明 LLM 在字典匹配类任务上表现极差。
- 规则系统具备万倍级别的速度优势。
- 混合方法兼顾准确性与语义理解。

---

## 第 8 页：Case Study -- 为什么纯 LLM 失败（约 20 秒）

标题：**Why Pure LLM Falls Short**

左侧 -- 真实样本（来自 500 条实验集）：
```java
@PostMapping(path = "/account/new")
public ResponseEntity<?> createAccount(
    @Valid @RequestBody final AccountDto account, ...) {
    ...
}
```

右侧 -- 两种方法的判断：

| | Rule-based | LLM zero-shot |
|---|---|---|
| 结果 | NOISE | CLEAN |
| 原因 | Aho-Corasick 命中 @PostMapping | "看起来是正常的 Spring Controller" |
| 时间 | < 0.01 ms | ~3,000 ms |
| 成本 | 0 | API token |

根因：LLM 评估的是代码*质量*，而不是*作为训练数据是否合适*。
要让 LLM 知道 "@PostMapping 在测试生成训练任务里属于 unnecessary"，
需要把 21,954 个模式都塞进 prompt----几乎不可能。

讲解要点：
- 用具体例子让听众直观理解方法差异。
- LLM "看起来合理"但实际判错。

---

## 第 9 页：软件工程实践（约 15 秒）

标题：**Software Engineering in Practice**

四个关键实践：

需求分析：
- 3 个用例、9 条功能需求 + 6 条非功能需求、追溯矩阵；
- UML use-case / activity / sequence diagram 各一张。

模块化架构：
- 4 个可组合 Agent Skill（共用 SKILL.md 协议）；
- 5 个设计模式：Strategy / Pipeline / Facade / Observer / Reflection。

测试与 CI/CD：
- 36 个 pytest 测试用例，100% 通过；
- pytest + flake8 + mypy；
- GitHub Actions 在 Python 3.10 / 3.11 / 3.12 上跑测试矩阵。

课程实验法对应（亮点）：
- Lab 1 Reflection 模式 → Filter 2 自纠错的 5 条规则；
- Lab 2 DSL 验证 → "rule-first, LLM only on residual" 的同构思想；
- Lab 3 形式化验证 → AST 结构性检查与字典完备性。

讲解要点：
- 体现课程核心：需求分析、系统设计、测试策略、课程实验整合。
- 这些原则在 AI 时代依然不可替代----本项目的 F1=0.965 vs 纯 LLM 0.387 就是证据。

---

## 第 10 页：总结（约 15 秒）

标题：**Conclusion -- Four Contributions**

1. **Skill 编排架构**：把 CleanTest 单体脚本重新组织成 4 个
   可组合 Agent Skill（基于 SKILL.md 协议），可被 CodeBuddy /
   Claude Code / Cursor 自然语言触发。
2. **Hybrid 检测方法**（rules + selective LLM）：
   F1 = 0.965 vs 纯 LLM 0.387；速度快约 13,000–15,000×。
3. **Aho-Corasick 优化**：Filter 1 提速约 18.8×、整个 pipeline
   约 11.5×，过滤结果完全一致。
4. **Filter 2 Reflection 机制 + Filter 3 模型模式（本期实验亮点）**：
   - Filter 2：5 条规则自纠错，抢救 5/45（11.1%）边界样本，
     人工核对 6/7（85.7%）正确。
   - Filter 3：在单卡 A800 80GB 上微调 Qwen2.5-Coder-0.5B
     （469K 样本，stratified 80/10/10，3.32 h），在 hold-out
     46,921 样本测试集上 **MAE 0.0309 vs CodeGPT 0.0798（约
     2.6× lower）、Pearson r = 0.778、F1 = 0.857（τ = 0.10）**，
     替换原 CleanTest 论文的 CodeGPT 主干。

核心结论：

> Systematic software design beats "just ask the LLM" -- proven with
> real-API experiments and a reproducible CI/CD pipeline.

Thank you. Questions?

GitHub: <https://github.com/jimmy0717/cleantest-agent>
Contact: yang_qhd@buaa.edu.cn

---

## 3 分钟讲解时间分配

| 时间段 | 页码 | 核心话术 |
|--------|------|---------|
| 0:00–0:10 | P1 | "CleanTest-Agent，一个用于清洗单元测试训练数据的多智能体技能编排系统。" |
| 0:10–0:30 | P2 | "Methods2Test 里 43% 是噪声；过滤后下游模型分支覆盖率平均提升约 67%。" |
| 0:30–0:55 | P3 | "我们把单体清洗流水线拆成 4 个 Agent Skill，并通过自然语言触发；Filter 3 提供 label 模式（默认）和 Qwen2.5-Coder-0.5B 微调的 model 模式。" |
| 0:55–1:25 | P4 | "核心方法论：规则处理确定性模式，ML 处理回归预测，LLM 只处理 ~12.7% 边界 case；并且在边界上叠加 5 条规则的 Reflection 自纠错。" |
| 1:25–1:40 | P5 | "Aho-Corasick 把整体匹配速度提升约 11.5 倍，过滤结果完全一致。" |
| 1:40–1:55 | P6 | "我们设计了 4 个 RQ：复现性、方法对比、性能、成本，使用 DeepSeek 真实 API + A800 真实训练。" |
| 1:55–2:20 | P7 | "结果：纯 LLM F1 仅 0.387，Hybrid 0.965，速度快约 15,000 倍；77.9% 漏检都是注解类。" |
| 2:20–2:40 | P8 | "举例：LLM 看到 @PostMapping 觉得正常，但其实是噪声----它记不住 21,954 个模式。" |
| 2:40–2:55 | P9 | "项目严格遵循软件工程实践：需求分析、模块化、36 测试 100% 通过、CI/CD 矩阵；并把 Lab 1 Reflection 落地到 Filter 2。" |
| 2:55–3:00 | P10 | "四点贡献----Skill 架构、Hybrid 检测、AC 加速、Reflection + Qwen2.5-Coder-0.5B 微调（MAE 0.031 vs CodeGPT 0.080）。系统化设计在 AI 时代依然不可替代。谢谢！" |
