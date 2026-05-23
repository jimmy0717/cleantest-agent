# CleanTest-Agent PPT 大纲（10 页，3 分钟汇报）

> 实验数据来自 2026-05-18 的 DeepSeek-V4-Flash 真实 API 实验，
> 见 `experiments/results/baseline_results.json` 与 `experiment_summary.md`。

---

## 第 1 页：封面（约 10 秒）

标题：CleanTest-Agent — A Multi-Agent Skill-Orchestrated System for Unit Test
Training Data Quality Assurance

- 作者：Yong Yang
- 单位：School of Software, Beihang University
- 邮箱：yang_qhd@buaa.edu.cn
- 课程：Software Requirements Analysis and System Design

讲解要点：
- 一句话定位：本项目设计并实现了一个多智能体技能编排系统，用于清洗单元测试
  训练数据中的噪声样本。

---

## 第 2 页：问题与动机（约 20 秒）

标题：Methods2Test 中 43.52% 的样本是噪声

左侧（背景）：
- AI 测试生成模型（CodeBERT、StarCoder、CodeLlama 等）依赖大规模数据集
- Methods2Test：91,385 个开源项目中 780,944 条 focal-method ↔ test-case 对
- CleanTest（FSE 2025 Distinguished Paper）发现 43.52% 的样本至少包含一种噪声

右侧（噪声分布饼图，原论文 Table 5 数据）：
- Unnecessary Annotations: 41.64%
- No Relevance: 12.70%
- Low Coverage: 3.95%
- Ambiguous Data Type: 3.08%
- Syntax Errors: 1.11%
- Empty Exception Handling: 0.68%
- Missing Implementation: 0.34%
- Non-English Literals: 0.16%

底部一句话：
> 在过滤噪声后训练，平均能让 CodeBERT/AthenaTest/StarCoder/CodeLlama-7B 的
> 分支覆盖率提升约 67% (Defects4J)。

讲解要点：
- 强调问题的严重性：将近一半的数据是有问题的。
- CleanTest 提出了规则过滤方法，但实现是耦合的脚本。

---

## 第 3 页：系统架构（约 25 秒）

标题：CleanTest-Agent: Pipeline-of-Skills

中央内容：架构图

```
User / Coding Assistant
     |  natural-language trigger
     v
Orchestrator Skill (cleantest-pipeline)
   |          |          |
   v          v          v
Filter 1    Filter 2    Filter 3
Syntax      Relevance   Coverage
AST +       Name match  Label scan
Aho-        + LLM       (default) /
Corasick    fallback    Qwen2.5-Coder
   |          |          |
   +----------+----------+
              v
   Clean dataset + noise report
```

要点标注：
- 每个 filter 都是一个独立的 Agent Skill（SKILL.md 协议）。
- 可与 CodeBuddy / Claude Code / Cursor 等 coding assistant 直接集成。

讲解要点：
- 把单体脚本拆成 4 个可组合、可独立调用、可独立测试的 Skill。
- 通过自然语言即可触发整个流水线。

---

## 第 4 页：核心方法 — Model-Driven（约 25 秒）

标题：Right Tool for Right Subtask

三列布局：

| Rules（确定性） | ML 模型（学习） | LLM（语义） |
|---|---|---|
| AST + Aho-Corasick + 正则 | Filter 3 label 模式扫描 JaCoCo 标签（默认）；Qwen2.5-Coder-0.5B 回归模型在 469K 样本上微调，作为无标签场景下的 model 模式 | DeepSeek-V4-Flash |
| 21,954 个注解模式，100% recall | $O(N)$ 单次扫描（label 模式） | 仅处理边界样本 |
| $0 成本，约 0.2 ms/样本 | $0 成本（label 模式） | ~12.7% 样本，约 3 s/样本 |

对比：纯 LLM 方案对所有样本调用 LLM，慢、贵、且准确率低。

讲解要点：
- 核心创新：不用一个 LLM 解决所有问题。
- 规则处理确定性模式（最快、最准、最便宜）。
- ML 模型处理可学习的回归任务。
- LLM 仅处理 ~12.7% 的边界 case。

---

## 第 5 页：关键优化 — Aho-Corasick（约 15 秒）

标题：Aho-Corasick：约 11.5× pipeline 加速

- Naïve：对 21,954 个模式逐一扫描 × 593,953 样本 → 约 30 min
- Aho-Corasick：单次自动机扫描 O(n + z) → 约 2.6 min（pipeline 整体）

视觉元素：自动机状态转换示意图 + 时间对比柱状图。

底部：两种实现的过滤结果完全一致（53.97% removed），属于纯性能优化。

讲解要点：
- 经典算法在工程实践中的价值。
- 正确性不变，速度提升约 11.5 倍（Filter 1 单阶段约 18.8×）。

---

## 第 6 页：实验设计（约 15 秒）

标题：Experiment Design — 4 Research Questions

- RQ1：CleanTest-Agent 是否复现了原始 CleanTest 的检测结果？
- RQ2：Model-Driven 与纯 LLM 相比表现如何？
- RQ3：Aho-Corasick 优化的实际加速比？
- RQ4：成本/速度对比？

对比方法：
1. Rule-based only（原始 CleanTest）
2. LLM zero-shot（DeepSeek-V4-Flash）
3. LLM few-shot（DeepSeek-V4-Flash）
4. Hybrid（本系统）：Rules + selective LLM（Filter 3 走 label 模式）

数据集：Methods2Test 中分层抽样的 500 条样本，真实 API 验证。

讲解要点：
- 四个 RQ 对应四个维度：复现性、方法对比、性能、效率。
- 真实 API 验证，非模拟数据。

---

## 第 7 页：实验结果（约 25 秒）

标题：Results — Rules + Selective LLM 显著优于 Pure LLM

| Method | Prec. | Recall | F1 | Time (500 条) |
|--------|-------|--------|------|-----------|
| Rule-based | 1.000 | 1.000 | 1.000 | 0.11 s |
| LLM zero-shot | 0.505 | 0.221 | 0.307 | 1,487 s |
| LLM few-shot | 0.534 | 0.303 | 0.387 | 1,642 s |
| Hybrid (ours) | 0.974 | 0.956 | 0.965 | < 60 s |

关键数字：
- F1：0.965 vs 0.387（约 +149%）
- 速度：0.11 s vs 1,642 s（约 13,000–15,000× 倍）
- LLM zero-shot 漏检率约 77.9%（recall 仅 0.221）

讲解要点：
- 真实实验证明 LLM 在字典匹配类任务上表现极差。
- 规则系统具备万倍级别的速度优势。
- 混合方法兼顾准确性与语义理解。

---

## 第 8 页：Case Study — 为什么纯 LLM 失败（约 20 秒）

标题：Why Pure LLM Falls Short

左侧 — 真实样本（来自 500 条实验集）：
```java
@ApiOperation(value = "Get all users")
@GetMapping("/api/users")
public List<User> getAllUsers() {
    return userRepository.findAll();
}
```

右侧 — 两种方法的判断：

| | Rule-based | LLM zero-shot |
|---|---|---|
| 结果 | NOISE | CLEAN |
| 原因 | Aho-Corasick 命中 @ApiOperation | "看起来是正常的 Spring 注解" |
| 时间 | < 0.01 ms | ~3,000 ms |
| 成本 | 0 | API token |

根因：LLM 不知道"该领域里 @ApiOperation 是 unnecessary annotation"这一
判定标准——这需要把 21,954 个模式都塞进 prompt，几乎不可能。

讲解要点：
- 用具体例子让听众直观理解方法差异。
- LLM"看起来合理"但实际判错。

---

## 第 9 页：软件工程实践（约 15 秒）

标题：Software Engineering in Practice

四个关键实践（用图标位 + 简短描述）：

需求分析：
- 3 个用例、9 条功能需求 + 6 条非功能需求、追溯矩阵

模块化架构：
- 4 个可组合 Agent Skill；SKILL.md 协议；Strategy + Pipeline 设计模式

测试与 CI/CD：
- 36 个 pytest 测试用例，pytest + flake8 + mypy；
- GitHub Actions 在 Python 3.10/3.11/3.12 上跑测试矩阵

真实实验评估：
- 4 个 RQ；DeepSeek-V4-Flash 真实 API 验证；消融实验

讲解要点：
- 体现课程核心：需求分析、系统设计、测试策略。
- 这些原则在 AI 时代依然不可替代。

---

## 第 10 页：总结（约 10 秒）

标题：Conclusion

主要贡献：
1. 用 Skill 编排架构重新组织了测试数据清洗流水线（4 个可组合 Skill）。
2. 提出 Rules + Selective LLM 的混合检测方法（F1 = 0.965，纯 LLM 仅 0.387）。
3. 用 Aho-Corasick 把 Filter 1 提速约 18.8×、整个 pipeline 提速约 11.5×。
4. 在 Filter 2 的 LLM 阶段引入 5 条规则的 Reflection 检查，
   抢救 5/45（11.1%）的边界样本，人工核对正确率 6/7（85.7%）。

核心结论：
> Systematic software design beats "just ask the LLM" — proven with
> real-API experiments and a reproducible CI/CD pipeline.

Thank you. Questions?

Contact: yang_qhd@buaa.edu.cn

---

## 3 分钟讲解时间分配

| 时间段 | 页码 | 核心话术 |
|--------|------|---------|
| 0:00–0:10 | P1 | "我的项目是 CleanTest-Agent，一个用于清洗单元测试训练数据的多智能体系统。" |
| 0:10–0:30 | P2 | "Methods2Test 里 43% 是噪声；过滤后模型分支覆盖率平均提升约 67%。" |
| 0:30–0:55 | P3 | "我们把清洗流水线拆成 4 个 Agent Skill，并通过自然语言触发。" |
| 0:55–1:20 | P4 | "核心方法论：规则处理确定性模式，ML 处理回归预测，LLM 只处理 ~12.7% 边界 case。" |
| 1:20–1:35 | P5 | "Aho-Corasick 把整体匹配速度提升约 11.5 倍。" |
| 1:35–1:50 | P6 | "我们设计了 4 个 RQ，用真实 DeepSeek API 验证。" |
| 1:50–2:15 | P7 | "结果：纯 LLM F1 仅 0.387，本系统 0.965，速度快约 15,000 倍。" |
| 2:15–2:35 | P8 | "举个例子：LLM 看到 @ApiOperation 觉得正常，但其实是噪声——它记不住 21,954 个模式。" |
| 2:35–2:50 | P9 | "项目严格遵循软件工程实践：需求分析、模块化设计、36 个测试用例、真实实验验证。" |
| 2:50–3:00 | P10 | "总结：系统化设计在 AI 时代依然不可替代，已被真实实验证明。谢谢！" |
