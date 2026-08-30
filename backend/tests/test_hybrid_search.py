"""Phase 5-2 混合检索测试：BM25 / RRF 融合（纯函数，不依赖 AI API Key）。"""
from app.rag.fusion import rrf_fusion


def test_rrf_fusion_prefers_items_in_both_lists() -> None:
    """两路共同命中的条目融合分应最高（排最前）。"""
    list_a = [(101, 0.9), (102, 0.8), (103, 0.5)]  # 向量路
    list_b = [(102, 8.0), (101, 5.0), (104, 3.0)]  # BM25 路
    fused = rrf_fusion([list_a, list_b])
    ranked = sorted(fused, key=lambda i: fused[i], reverse=True)
    assert ranked[0] in (101, 102)  # 双路命中的排最前
    assert 104 in fused  # 单路命中的也有分


def test_rrf_fusion_single_list() -> None:
    """单路时融合分等于自身 RRF 分，排序保持。"""
    fused = rrf_fusion([[(1, 0.9), (2, 0.7), (3, 0.1)]])
    ranked = sorted(fused, key=lambda i: fused[i], reverse=True)
    assert ranked == [1, 2, 3]


def test_rrf_fusion_scores_decrease_by_rank() -> None:
    """同一列表内排名越靠前融合分越高。"""
    fused = rrf_fusion([[(10, 1.0), (20, 0.5), (30, 0.1)]])
    assert fused[10] > fused[20] > fused[30]
