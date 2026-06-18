"""Offline tests for persistent memory.

Uses an in-memory SQLite engine (StaticPool so all sessions share one DB) and a
deterministic bag-of-words fake embedder, so no PostgreSQL or OpenAI is needed.
Covers the four memory types, vector search, and the cross-session recall
scenario: analyze NVIDIA, then later "compare with AMD" must surface NVIDIA.
"""

import re

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from alphamind.memory.service import MemoryService


class FakeEmbedder:
    """Hashing bag-of-words embedder: shared tokens → positive cosine similarity."""

    dim = 96

    def _vec(self, text):
        v = [0.0] * self.dim
        for tok in re.findall(r"[a-z0-9]+", text.lower()):
            v[hash(tok) % self.dim] += 1.0
        return v

    def embed_query(self, text):
        return self._vec(text)

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]


@pytest.fixture
def service():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
    )
    return MemoryService(engine=engine, embedder=FakeEmbedder())


def test_user_profile_memory(service):
    service.upsert_user_profile("u1", name="Het", risk_tolerance="aggressive", preferences={"sectors": "tech"})
    service.upsert_user_profile("u1", preferences={"horizon": "long"})  # merge
    p = service.get_user_profile("u1")
    assert p.name == "Het" and p.risk_tolerance == "aggressive"
    assert p.preferences == {"sectors": "tech", "horizon": "long"}
    assert service.get_user_profile("nobody") is None


def test_company_memory(service):
    service.upsert_company_memory("NVDA", name="NVIDIA Corp", sector="Tech", notes={"summary": "AI leader"})
    c = service.get_company_memory("nvda")
    assert c.name == "NVIDIA Corp" and c.notes["summary"] == "AI leader"


def test_research_history_order_and_filter(service):
    service.add_research_record(ticker="AAPL", summary="Apple steady", recommendation="HOLD", user_id="u1")
    service.add_research_record(ticker="NVDA", summary="Nvidia growth", recommendation="BUY", user_id="u1")
    hist = service.get_research_history(user_id="u1", limit=10)
    assert [r.ticker for r in hist] == ["NVDA", "AAPL"]  # most recent first
    assert [r.ticker for r in service.get_research_history(ticker="AAPL")] == ["AAPL"]


def test_conversation_history(service):
    service.add_message(thread_id="t1", role="user", content="Analyze NVIDIA", user_id="u1")
    service.add_message(thread_id="t1", role="assistant", content="BUY: strong AI demand", user_id="u1")
    msgs = service.get_conversation("t1")
    assert [m.role for m in msgs] == ["user", "assistant"]
    assert msgs[1].content.startswith("BUY")


def test_vector_search_finds_relevant(service):
    service.add_research_record(ticker="NVDA", summary="NVIDIA dominates AI data center GPUs", user_id="u1")
    service.add_research_record(ticker="KO", summary="Coca Cola beverages stable dividend", user_id="u1")
    hits = service.vector.search("AI GPU data center growth", user_id="u1", k=2)
    assert hits and hits[0].ticker == "NVDA"
    assert hits[0].score > 0


def test_cross_session_recall_nvidia_then_amd(service):
    # Turn 1: analyze NVIDIA (persisted to memory).
    service.add_research_record(
        ticker="NVDA", summary="NVIDIA is the AI semiconductor leader with strong data center growth",
        recommendation="BUY", user_id="u1",
    )
    service.upsert_company_memory("NVDA", name="NVIDIA Corp", notes={"summary": "AI chip leader, BUY"})

    # Turn 2 (later): "Compare with AMD" — the system must remember NVIDIA.
    ctx = service.recall("Compare this with AMD semiconductors", user_id="u1")
    assert ctx.has_content()
    blob = ctx.format()
    assert "NVDA" in blob or "NVIDIA" in blob
    # NVIDIA reachable via recency (recent_research) and/or semantic hit.
    assert any(r.ticker == "NVDA" for r in ctx.recent_research) or \
           any(h.ticker == "NVDA" for h in ctx.semantic_hits)


def test_recall_dedup_drops_semantic_already_in_recent(service):
    service.add_research_record(ticker="NVDA", summary="NVIDIA AI growth story", user_id="u1")
    ctx = service.recall("NVIDIA AI growth", user_id="u1")
    recent_ids = {str(r.id) for r in ctx.recent_research}
    assert all(not (h.kind == "research" and h.ref_id in recent_ids) for h in ctx.semantic_hits)
