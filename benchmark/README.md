# Legal RAG Benchmark

基于讯问笔录场景的RAG系统评测基准。

## 概述

本benchmark参照 `docs/rag-讯问-询问笔录.md` 设计文档创建，用于评测法律案件场景下的RAG系统质量。

## 设计原则

1. **可核验性**: 所有答案必须提供证据引用（页码/段落定位）
2. **数字/时间零容错**: 金额和日期必须精确匹配
3. **冲突显式化**: 对不确定和冲突信息必须明确说明
4. **召回优先、再精排**: 采用混合检索策略

## 目录结构

```
benchmark/
├── README.md              # 本文档
├── SCHEMA.md             # JSON Schema说明
├── schema.json           # Benchmark数据结构定义
├── questions/
│   ├── fact_exact.json       # 事实型题目
│   ├── evidence_set.json     # 证据集合型题目
│   └── conflict_gap.json    # 冲突/缺口型题目
└── test_runner.py       # 测试运行器
```

## 三类题型

### 1. 事实型 (fact_exact)

唯一答案，硬判分。评测内容包括：
- 金额（如：总收款42000元，退款18000元，欠款24000元）
- 日期（如：2020-06-05, 2020-08-31）
- 人员信息
- 是/否问题（如：是否认罪认罚）

**评分标准**：
- `numeric_exact`: 数字/日期精确匹配
- `citation_required`: 必须提供正确引用

### 2. 证据集合型 (evidence_set)

答案需要多条证据聚合。示例问题：
- "有哪些证据表明其承诺退款/已退款/仍欠款？"
- "有哪些证据涉及资金用途说明？"

**评分标准**：
- `evidence_recall@K`: 关键证据召回率
- `evidence_precision`: 证据精确度
- `citation_coverage`: 引用覆盖度

### 3. 冲突/缺口型 (conflict_gap)

评测系统是否会编造信息。示例问题：
- "42000元具体用到哪里了？给了谁？买了什么？"
- 正确答案：应明确说明"不清楚/忘记了"，引用原话

**评分标准**：
- `abstention_correctness`: 正确拒答率
- `hallucination_rate`: 幻觉率（必须为0）

## 使用方法

```bash
# 运行全部测试
uv run pytest benchmark/

# 运行特定类型测试
uv run pytest benchmark/ -k "fact_exact"

# 查看详细输出
uv run pytest benchmark/ -v -s
```

## 样本数据

Benchmark基于以下样本数据：
- `SampleData/output.md`: 讯问笔录（约8页）

包含的关键信息：
- 被讯问人：陈明飞
- 涉案金额：42000元（收款）→ 18000元（退款）→ 24000元（欠款）
- 涉案时间：2020年6月-11月
- 涉案地点：清远市清城区

## 评测指标说明

| 指标 | 类型 | 说明 |
|------|------|------|
| exact_match | 事实型 | 数字/日期完全匹配 |
| citation_accuracy | 通用 | 引用页码正确率 |
| evidence_recall@K | 证据型 | TopK结果中关键证据召回率 |
| evidence_precision | 证据型 | 召回结果中相关证据占比 |
| abstention_correctness | 冲突型 | 正确拒答比例 |
| hallucination_rate | 冲突型 | 编造信息的比例（应为0） |

## 回归测试机制

每次修改以下内容时必须运行benchmark：
- Embedding模型
- Reranker模型
- Prompt模板
- 切块策略
- 检索策略

**阻断条件**: 任何"事实型"题目得分从100%下降

## 参考

- 设计文档: `docs/rag-讯问-询问笔录.md`
- RAGFlow项目: https://ragflow.io/

## 贡献指南

添加新题目时请遵循：
1. 选择合适的题型类型
2. 提供准确的expected答案
3. 标注required_evidence（页码+关键文本）
4. 指定scoring标准

## 许可证

与主项目保持一致
