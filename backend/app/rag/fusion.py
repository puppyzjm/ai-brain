"""RRF（Reciprocal Rank Fusion）排名融合：合并多路检索排名。"""

RRF_K = 60


def rrf_fusion(ranked_lists: list[list[tuple[int, float]]]) -> dict[int, float]:
    """输入多路 [(id, score), ...]（各自已按分数降序），返回融合分 {id: rrf_score}。

    融合分 = Σ 1/(k + rank + 1)，与各路原始分数量纲无关，天然适合混合检索。
    """
    fused: dict[int, float] = {}
    for lst in ranked_lists:
        for rank, (doc_id, _score) in enumerate(lst):
            fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (RRF_K + rank + 1)
    return fused
