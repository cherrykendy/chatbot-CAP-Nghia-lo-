from __future__ import annotations

import math
import os
from typing import List

try:
    from rank_bm25 import BM25Okapi
except ImportError:  # pragma: no cover
    class BM25Okapi:  # type: ignore
        def __init__(self, corpus, k1: float = 1.5, b: float = 0.75) -> None:
            self.corpus = corpus
            self.k1 = k1
            self.b = b
            self.doc_freqs = []
            self.idf = {}
            self.avgdl = sum(len(doc) for doc in corpus) / max(len(corpus), 1)
            doc_counts = {}
            for doc in corpus:
                freqs = {}
                for token in doc:
                    freqs[token] = freqs.get(token, 0) + 1
                self.doc_freqs.append(freqs)
                for token in freqs:
                    doc_counts[token] = doc_counts.get(token, 0) + 1
            for token, freq in doc_counts.items():
                numerator = len(corpus) - freq + 0.5
                denominator = freq + 0.5
                self.idf[token] = math.log(1 + numerator / denominator)

        def get_scores(self, query_tokens):
            scores = []
            for freqs in self.doc_freqs:
                score = 0.0
                dl = sum(freqs.values())
                for token in query_tokens:
                    if token not in freqs:
                        continue
                    idf = self.idf.get(token, 0.0)
                    freq = freqs[token]
                    denom = freq + self.k1 * (1 - self.b + self.b * dl / max(self.avgdl, 1e-9))
                    score += idf * (freq * (self.k1 + 1)) / denom
                scores.append(score)
            return scores

from .schema import Candidate, Intent, ScriptPack

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None  # type: ignore

try:  # pragma: no cover - chạy khi có numpy
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore


def _tokenize(text: str) -> List[str]:
    return [t for t in text.lower().split() if t]


class NLUIndex:
    def __init__(self, use_embedding: bool | None = None) -> None:
        if use_embedding is None:
            flag = os.getenv("USE_EMBEDDING", "false").lower()
            use_embedding = flag in {"1", "true", "yes"}
        self.use_embedding = use_embedding and SentenceTransformer is not None and np is not None
        self.embedder = None
        self.script_pack = ScriptPack(intents=[])
        self._bm25: BM25Okapi | None = None
        self._documents: List[str] = []
        self._embeddings: np.ndarray | None = None

    def build(self, pack: ScriptPack) -> None:
        self.script_pack = pack
        documents: List[List[str]] = []
        self._documents = []
        for intent in pack.intents:
            text_parts = intent.synonyms + intent.examples
            if not text_parts:
                text_parts = [intent.id.replace("_", " ")]
            joined = " \n ".join(text_parts)
            documents.append(_tokenize(joined))
            self._documents.append(joined)
        self._bm25 = BM25Okapi(documents)

        if self.use_embedding:
            if SentenceTransformer is None or np is None:
                raise RuntimeError("sentence-transformers chưa được cài đặt")
            self.embedder = SentenceTransformer("paraphrase-MiniLM-L6-v2")
            self._embeddings = np.array(self.embedder.encode(self._documents, convert_to_numpy=True))
        else:
            self.embedder = None
            self._embeddings = None

    def rank(self, text: str, top_k: int = 3) -> List[Candidate]:
        if self._bm25 is None:
            raise RuntimeError("Chưa xây dựng NLU index")
        tokens = _tokenize(text)
        bm25_scores = self._bm25.get_scores(tokens)
        max_bm25 = max(bm25_scores) if len(bm25_scores) else 0.0
        candidates: List[Candidate] = []

        embed_scores = None
        if self.embedder is not None and self._embeddings is not None and np is not None:
            query_vec = self.embedder.encode([text], convert_to_numpy=True)
            norms = np.linalg.norm(self._embeddings, axis=1) * np.linalg.norm(query_vec, axis=1)[0]
            cosine = (self._embeddings @ query_vec.T).reshape(-1)
            with np.errstate(divide="ignore", invalid="ignore"):
                cosine = np.where(norms == 0, 0.0, cosine / norms)
            embed_scores = cosine

        for idx, intent in enumerate(self.script_pack.intents):
            bm25_score = bm25_scores[idx]
            normalized_bm25 = bm25_score / max_bm25 if max_bm25 > 0 else 0.0
            final_score = normalized_bm25
            if embed_scores is not None:
                normalized_embed = (embed_scores[idx] + 1) / 2
                final_score = 0.6 * normalized_bm25 + 0.4 * normalized_embed
            candidates.append(
                Candidate(
                    intent_id=intent.id,
                    file=intent.source_file,
                    score=float(final_score),
                    can_interrupt=intent.can_interrupt,
                    domain=intent.domain,
                )
            )

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:top_k]

    def intent_by_id(self, intent_id: str) -> Intent | None:
        return self.script_pack.intent_by_id(intent_id)

    def all_intents(self) -> List[Intent]:
        return list(self.script_pack.intents)
