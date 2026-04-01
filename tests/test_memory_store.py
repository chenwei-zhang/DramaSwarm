# -*- coding: utf-8 -*-
"""
记忆系统单元测试

覆盖：InMemoryStore 的增删查改、重要性排序、遗忘曲线
"""

import pytest
from datetime import datetime, timedelta

from swarmsim.memory.base import MemoryEntry, InMemoryStore


@pytest.fixture
def store():
    return InMemoryStore()


def _make_entry(agent_id="agent_1", content="test", importance=0.5, hours_ago=0):
    return MemoryEntry(
        id=f"{agent_id}_{content}_{hours_ago}",
        agent_id=agent_id,
        timestamp=datetime.now() - timedelta(hours=hours_ago),
        content=content,
        source="test",
        importance=importance,
        tags=["test"],
    )


class TestInMemoryStore:
    def test_add_and_get(self, store):
        entry = _make_entry(content="hello")
        store.add(entry)
        got = store.get(entry.id)
        assert got is not None
        assert got.content == "hello"

    def test_get_nonexistent(self, store):
        assert store.get("nonexistent") is None

    def test_get_by_agent(self, store):
        store.add(_make_entry(agent_id="a1", content="msg1"))
        store.add(_make_entry(agent_id="a1", content="msg2"))
        store.add(_make_entry(agent_id="a2", content="msg3"))

        a1_memories = store.get_by_agent("a1")
        assert len(a1_memories) == 2
        a2_memories = store.get_by_agent("a2")
        assert len(a2_memories) == 1

    def test_get_recent(self, store):
        store.add(_make_entry(content="old", hours_ago=10))
        store.add(_make_entry(content="new1", hours_ago=1))
        store.add(_make_entry(content="new2", hours_ago=0))

        recent = store.get_recent("agent_1", n=2)
        assert len(recent) == 2
        assert recent[0].content == "new2"

    def test_get_important(self, store):
        store.add(_make_entry(content="trivial", importance=0.1))
        store.add(_make_entry(content="critical", importance=0.95))
        store.add(_make_entry(content="moderate", importance=0.5))

        important = store.get_important("agent_1", n=2)
        assert len(important) == 2
        assert important[0].content == "critical"
        assert important[1].content == "moderate"

    def test_search(self, store):
        store.add(_make_entry(content="道歉声明"))
        store.add(_make_entry(content="反击谣言"))
        store.add(_make_entry(content="公益慈善"))

        results = store.search("agent_1", "道歉")
        assert len(results) == 1
        assert "道歉" in results[0].content

    def test_delete(self, store):
        entry = _make_entry(content="to_delete")
        store.add(entry)
        assert store.get(entry.id) is not None
        assert store.delete(entry.id) is True
        assert store.get(entry.id) is None
        assert store.delete(entry.id) is False

    def test_clear_agent(self, store):
        store.add(_make_entry(agent_id="a1", content="m1"))
        store.add(_make_entry(agent_id="a1", content="m2"))
        store.add(_make_entry(agent_id="a2", content="m3"))

        count = store.clear_agent("a1")
        assert count == 2
        assert store.get_by_agent("a1") == []
        assert len(store.get_by_agent("a2")) == 1

    def test_decay_importance(self, store):
        store.add(_make_entry(content="memory1", importance=0.8))
        store.add(_make_entry(content="memory2", importance=0.3))

        store.decay_importance("agent_1", days_passed=5, rate=0.05)

        memories = store.get_by_agent("agent_1")
        for m in memories:
            if m.content == "memory1":
                assert m.importance == pytest.approx(0.55, abs=0.01)
            elif m.content == "memory2":
                assert m.importance == pytest.approx(0.05, abs=0.01)

    def test_decay_importance_never_negative(self, store):
        store.add(_make_entry(content="low_imp", importance=0.1))
        store.decay_importance("agent_1", days_passed=100, rate=0.05)

        memories = store.get_by_agent("agent_1")
        for m in memories:
            assert m.importance >= 0.0

    def test_to_dict_roundtrip(self, store):
        entry = _make_entry(content="roundtrip", importance=0.7)
        d = entry.to_dict()
        restored = MemoryEntry.from_dict(d)
        assert restored.id == entry.id
        assert restored.content == entry.content
        assert restored.importance == entry.importance
