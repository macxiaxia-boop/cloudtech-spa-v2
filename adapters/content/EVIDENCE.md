# CloudTech V4 — content adapters EVIDENCE

## 真实 LLM 调用: 0

所有模块使用 Python stdlib mock + difflib，零网络调用。

## 算法说明

| 模块 | 算法 | 局限性 |
|------|------|--------|
| `StructureAnalyzer` | 正则关键词匹配启发式 | 依赖预定义关键词，覆盖有限 |
| `SimilarityQC` | `difflib.SequenceMatcher` + n-gram Jaccard | 字符级相似度，不能捕捉语义相似 |
| `OriginalScriptGenerator` | 模板字符串拼接 + 长度启发式 | 无语义理解，纯占位符 |

## 相似度阈值

- `< 0.30` → pass (原创性良好)
- `0.30–0.60` → revise (建议润色)
- `> 0.60` → reject (需大幅重写)

**注意**: difflib 是启发式算法，**远不如专业 QC**（MinHash / embedding cosine / LLM judge）。严禁将 mock 结果用于生产判断。

## Production Ready: NO

- 非语义级别相似度检测
- 模板拼装 ≠ 真正的原创写作
- 无抄袭数据库比对

## 下一步真实化路径

1. **StructureAnalyzer** → 接 Claude/GPT 做结构提取（带 JSON schema 输出约束）
2. **OriginalScriptGenerator** → 接 Claude/GPT 做风格迁移 + 受众适配
3. **SimilarityQC** → 接 embedding cosine（text2vec-large / bge）做语义相似度；或接 MinHashLSH 做大规模模糊去重
4. **Director** → 条件分支：短文本走 mock，快；长文本/高风险走 LLM judge，慢但准
