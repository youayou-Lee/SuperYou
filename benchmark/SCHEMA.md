# Benchmark JSON Schema 文档

本文档详细说明了Legal RAG Benchmark使用的JSON数据结构。

## 概述

Benchmark遵循JSON Schema规范（参见 `schema.json`），支持三类题型的评测数据。

## 根结构

```json
{
  "benchmark_type": "fact_exact | evidence_set | conflict_gap",
  "description": "string - 题目集描述",
  "document": "string - 来源文档名称",
  "questions": [...],
  "evaluation_criteria": {...}
}
```

## 三种题型结构

### 1. fact_exact (事实型)

用于精确事实提取的题目，如金额、日期、人名等。

#### 示例

```json
{
  "id": "fact_001",
  "type": "fact_exact",
  "question": "成龙飞总共给了多少钱给陈明飞用于办理学位？",
  "expected": {
    "amount_total": 42000
  },
  "required_evidence": [
    {
      "page": 2,
      "must_include": "42000元",
      "section": "qa_pair",
      "speaker": "answer",
      "is_critical": true
    }
  ],
  "scoring": {
    "numeric_exact": true,
    "citation_required": true
  },
  "metadata": {
    "difficulty": "easy",
    "category": "monetary",
    "tags": ["金额", "收款", "学位办理"]
  }
}
```

#### expected 字段类型

| 字段 | 类型 | 说明 |
|------|------|------|
| amount_total | number | 总金额 |
| amount_breakdown | array | 金额明细 |
| date | string (ISO) | 日期 YYYY-MM-DD |
| date_range | object | 日期范围 {start, end} |
| count | integer | 数量 |
| text_answer | string | 文本答案 |
| boolean_answer | boolean | 是/否答案 |
| entity | string | 实体（人名/地点/机构） |

#### scoring 字段类型

| 字段 | 类型 | 说明 |
|------|------|------|
| numeric_exact | boolean | 数字是否精确匹配 |
| date_exact | boolean | 日期是否精确匹配 |
| citation_required | boolean | 是否需要引用 |

### 2. evidence_set (证据集合型)

用于测试多证据聚合能力的题目。

#### 示例

```json
{
  "id": "evidence_001",
  "type": "evidence_set",
  "question": "有哪些证据表明陈明飞承诺退款给成龙飞？",
  "expected": {
    "evidence_count_min": 2,
    "key_points": [
      "承诺如果办理不成功会将42000元退回给成龙飞",
      "2020年8月30日左右告知无法办理并承诺退款"
    ]
  },
  "required_evidence": [...],
  "scoring": {
    "evidence_recall_min": 0.8,
    "evidence_precision_min": 0.7,
    "citation_required": true
  }
}
```

#### expected 字段类型

| 字段 | 类型 | 说明 |
|------|------|------|
| evidence_count_min | integer | 最少证据数量 |
| key_points | array[string] | 关键信息点列表 |

#### scoring 字段类型

| 字段 | 类型 | 范围 | 说明 |
|------|------|------|------|
| evidence_recall_min | number | 0-1 | 最小召回率阈值 |
| evidence_precision_min | number | 0-1 | 最小精确度阈值 |
| citation_required | boolean | - | 是否需要引用 |

### 3. conflict_gap (冲突/缺口型)

用于测试系统是否会在信息缺失时编造内容。

#### 示例

```json
{
  "id": "conflict_gap_001",
  "question": "42000元具体用到哪里了？请详细说明...",
  "should_abstain": true,
  "hallucination_penalty": "high",
  "required_quote": "具体请了谁吃饭...都忘记了",
  "evidence_location": {
    "page": 4,
    "lines": "105-107"
  },
  "expected_behavior": "System must refuse to provide specific details...",
  "scoring": {
    "abstention_required": true,
    "hallucination_check": "must_not_invent_details",
    "quote_required": true
  }
}
```

#### 特殊字段

| 字段 | 类型 | 说明 |
|------|------|------|
| should_abstain | boolean | 是否应拒答 |
| hallucination_penalty | string | 幻觉惩罚等级 |
| required_quote | string | 必须引用的原话 |
| additional_quotes | array[string] | 其他可引用的原话 |
| evidence_location | object | 证据位置 {page, lines} |
| expected_behavior | string | 期望行为描述 |

## 通用字段说明

### required_evidence 数组

每个证据项包含：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | integer | 是 | 页码 |
| must_include | string | 是 | 必须包含的文本 |
| section | string | 否 | 区块类型 (qa_pair/header) |
| speaker | string | 否 | 说话者 (question/answer) |
| is_critical | boolean | 否 | 是否为关键证据 |

### metadata 对象

| 字段 | 类型 | 说明 |
|------|------|------|
| difficulty | string | 难度: easy/medium/hard |
| category | string | 分类: monetary/temporal/factual等 |
| tags | array[string] | 标签列表 |
| notes | string | 额外说明 |

## 评测指标计算

### fact_exact 指标

```
score = exact_match * 0.7 + citation_correctness * 0.3
```

### evidence_set 指标

```
recall = retrieved_key_evidence / total_key_evidence
precision = relevant_evidence / total_retrieved
score = (recall >= min_recall ? 0.5 : 0) + 
        (precision >= min_precision ? 0.3 : 0) + 
        (citation_provided ? 0.2 : 0)
```

### conflict_gap 指标

```
score = (correct_abstention ? 0.4 : 0) + 
        (no_hallucination ? 0.4 : 0) + 
        (quote_included ? 0.2 : 0)
```

## 使用示例

### Python

```python
from benchmark.test_runner import BenchmarkRunner

runner = BenchmarkRunner('path/to/benchmark')
summary = runner.run_benchmark(rag_system, question_type='fact_exact')
print(summary['overall_percentage'])
```

### 命令行

```bash
# 运行所有测试
uv run pytest benchmark/

# 运行特定类型
uv run python benchmark/test_runner.py --type fact_exact
```

## 版本控制

Schema版本: 1.0.0  
最后更新: 2024-02-12  
维护者: RAGFlow Team
