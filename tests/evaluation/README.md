# Retrieval Evaluation

`app.rag.evaluation` 提供可复用的 `recall_at_k`、`reciprocal_rank` 和
`evaluate_retrieval`。本目录保留固定查询、相关 chunk ID 标注和指标断言，避免把
临时人工观感写成准确率结论。

运行：

    uv run --cache-dir .uv-cache --extra dev pytest -p no:cacheprovider tests/evaluation -q

指标定义：

- Recall@K = Top-K 命中的相关 chunk 数 / 全部相关 chunk 数
- MRR = 每个查询首个相关结果排名倒数的平均值

扩展真实数据集时，每条 case 至少包含 `query`、`relevant_chunk_ids`，并固定所用
Embedding 模型、Chroma 数据快照、Top-K 和距离阈值，保证结果可复现。
