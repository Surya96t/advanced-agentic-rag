"""
Re-ranking implementations for improving retrieval quality.

This package provides multiple re-ranking strategies:
- FlashRank: Fast local CPU-based re-ranking (no API calls)
- Cohere: Cloud-based re-ranking (requires API key, best accuracy)

Re-ranking is the second stage in a retrieval pipeline:
1. First-stage retrieval: Cast a wide net (get top-100 candidates)
2. Re-ranking: Precisely score and re-order candidates (return top-10)

Why re-rank?
- Retrieval models optimize for recall (find all relevant docs)
- Re-ranking models optimize for precision (rank best docs first)
- Re-ranking is more expensive, so only applied to top candidates

Learning Resources:
- FlashRank: https://github.com/PrithivirajDamodaran/FlashRank
- Cohere Rerank: https://docs.cohere.com/docs/reranking
- Cross-encoders: https://www.sbert.net/examples/applications/cross-encoder/README.html
"""

from app.retrieval.rerankers.base import Reranker
from app.retrieval.rerankers.flashrank import FlashRankReranker

__all__ = [
    "Reranker",
    "FlashRankReranker",
]
