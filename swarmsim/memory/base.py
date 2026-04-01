"""
Memory Management Module - 记忆管理模块

提供 Agent 记忆的持久化、检索和关联功能。
"""

import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    agent_id: str
    timestamp: datetime
    content: str
    source: str
    importance: float
    tags: list[str]
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
            "source": self.source,
            "importance": self.importance,
            "tags": self.tags,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryEntry":
        """从字典创建"""
        return cls(
            id=data["id"],
            agent_id=data["agent_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            content=data["content"],
            source=data["source"],
            importance=data["importance"],
            tags=data["tags"],
            metadata=data.get("metadata", {})
        )


class MemoryStore:
    """
    记忆存储基类

    提供记忆的增删查改接口。
    """

    def add(self, memory: MemoryEntry) -> None:
        """添加记忆"""
        raise NotImplementedError

    def get(self, memory_id: str) -> MemoryEntry | None:
        """获取单条记忆"""
        raise NotImplementedError

    def get_by_agent(
        self,
        agent_id: str,
        limit: int = 100
    ) -> list[MemoryEntry]:
        """获取 Agent 的所有记忆"""
        raise NotImplementedError

    def search(
        self,
        agent_id: str,
        query: str,
        limit: int = 10
    ) -> list[MemoryEntry]:
        """搜索记忆"""
        raise NotImplementedError

    def get_recent(
        self,
        agent_id: str,
        n: int = 5
    ) -> list[MemoryEntry]:
        """获取最近的记忆"""
        raise NotImplementedError

    def get_important(
        self,
        agent_id: str,
        n: int = 5
    ) -> list[MemoryEntry]:
        """获取最重要的记忆（按 importance 排序）"""
        raise NotImplementedError

    def decay_importance(
        self,
        agent_id: str,
        days_passed: int = 1,
        rate: float = 0.05,
    ) -> None:
        """遗忘曲线：降低所有记忆的重要性"""
        raise NotImplementedError

    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        raise NotImplementedError

    def clear_agent(self, agent_id: str) -> int:
        """清除 Agent 的所有记忆"""
        raise NotImplementedError


class InMemoryStore(MemoryStore):
    """
    内存存储

    适合开发和测试，数据不持久化。
    """

    def __init__(self):
        self._memories: dict[str, MemoryEntry] = {}
        self._agent_index: dict[str, list[str]] = {}

    def add(self, memory: MemoryEntry) -> None:
        """添加记忆到内存"""
        self._memories[memory.id] = memory

        if memory.agent_id not in self._agent_index:
            self._agent_index[memory.agent_id] = []
        self._agent_index[memory.agent_id].append(memory.id)

    def get(self, memory_id: str) -> MemoryEntry | None:
        """获取单条记忆"""
        return self._memories.get(memory_id)

    def get_by_agent(
        self,
        agent_id: str,
        limit: int = 100
    ) -> list[MemoryEntry]:
        """获取 Agent 的所有记忆"""
        memory_ids = self._agent_index.get(agent_id, [])
        memories = [
            self._memories[mid] for mid in memory_ids
            if mid in self._memories
        ]
        # 按时间排序
        memories.sort(key=lambda m: m.timestamp, reverse=True)
        return memories[:limit]

    def search(
        self,
        agent_id: str,
        query: str,
        limit: int = 10
    ) -> list[MemoryEntry]:
        """搜索记忆"""
        query_lower = query.lower()
        results = []

        for memory in self.get_by_agent(agent_id):
            if query_lower in memory.content.lower():
                results.append(memory)
                if len(results) >= limit:
                    break

        return results

    def get_recent(
        self,
        agent_id: str,
        n: int = 5
    ) -> list[MemoryEntry]:
        """获取最近的记忆"""
        return self.get_by_agent(agent_id, limit=n)

    def get_important(
        self,
        agent_id: str,
        n: int = 5
    ) -> list[MemoryEntry]:
        """获取最重要的记忆（按 importance 排序）"""
        memory_ids = self._agent_index.get(agent_id, [])
        memories = [
            self._memories[mid] for mid in memory_ids
            if mid in self._memories
        ]
        memories.sort(key=lambda m: m.importance, reverse=True)
        return memories[:n]

    def decay_importance(
        self,
        agent_id: str,
        days_passed: int = 1,
        rate: float = 0.05,
    ) -> None:
        """遗忘曲线：降低所有记忆的重要性"""
        for memory in self.get_by_agent(agent_id, limit=1000):
            memory.importance = max(0.0, memory.importance - rate * days_passed)

    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        if memory_id in self._memories:
            memory = self._memories[memory_id]
            # 从索引中移除
            if memory.agent_id in self._agent_index:
                self._agent_index[memory.agent_id].remove(memory_id)
            # 删除记忆
            del self._memories[memory_id]
            return True
        return False

    def clear_agent(self, agent_id: str) -> int:
        """清除 Agent 的所有记忆"""
        if agent_id not in self._agent_index:
            return 0

        count = 0
        for memory_id in self._agent_index[agent_id][:]:
            if self.delete(memory_id):
                count += 1

        return count


class SQLiteStore(MemoryStore):
    """
    SQLite 持久化存储

    适合生产环境，数据持久化到磁盘。
    """

    def __init__(self, db_path: str | Path = "swarmsim/memory/memories.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    importance REAL NOT NULL,
                    tags TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_id
                ON memories(agent_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON memories(timestamp DESC)
            """)
            conn.commit()

    def add(self, memory: MemoryEntry) -> None:
        """添加记忆到数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memories
                (id, agent_id, timestamp, content, source, importance, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.id,
                memory.agent_id,
                memory.timestamp.isoformat(),
                memory.content,
                memory.source,
                memory.importance,
                json.dumps(memory.tags),
                json.dumps(memory.metadata)
            ))
            conn.commit()

    def get(self, memory_id: str) -> MemoryEntry | None:
        """获取单条记忆"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_memory(row)
        return None

    def get_by_agent(
        self,
        agent_id: str,
        limit: int = 100
    ) -> list[MemoryEntry]:
        """获取 Agent 的所有记忆"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM memories
                WHERE agent_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (agent_id, limit))
            return [self._row_to_memory(row) for row in cursor.fetchall()]

    def search(
        self,
        agent_id: str,
        query: str,
        limit: int = 10
    ) -> list[MemoryEntry]:
        """搜索记忆"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM memories
                WHERE agent_id = ? AND content LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (agent_id, f"%{query}%", limit))
            return [self._row_to_memory(row) for row in cursor.fetchall()]

    def get_recent(
        self,
        agent_id: str,
        n: int = 5
    ) -> list[MemoryEntry]:
        """获取最近的记忆"""
        return self.get_by_agent(agent_id, limit=n)

    def get_important(
        self,
        agent_id: str,
        n: int = 5
    ) -> list[MemoryEntry]:
        """获取最重要的记忆（按 importance 排序）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM memories
                WHERE agent_id = ?
                ORDER BY importance DESC
                LIMIT ?
            """, (agent_id, n))
            return [self._row_to_memory(row) for row in cursor.fetchall()]

    def decay_importance(
        self,
        agent_id: str,
        days_passed: int = 1,
        rate: float = 0.05,
    ) -> None:
        """遗忘曲线：降低所有记忆的重要性"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE memories
                SET importance = MAX(0, importance - ?)
                WHERE agent_id = ?
            """, (rate * days_passed, agent_id))
            conn.commit()

    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM memories WHERE id = ?",
                (memory_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def clear_agent(self, agent_id: str) -> int:
        """清除 Agent 的所有记忆"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM memories WHERE agent_id = ?",
                (agent_id,)
            )
            conn.commit()
            return cursor.rowcount

    def _row_to_memory(self, row: tuple) -> MemoryEntry:
        """将数据库行转换为 MemoryEntry"""
        return MemoryEntry(
            id=row[0],
            agent_id=row[1],
            timestamp=datetime.fromisoformat(row[2]),
            content=row[3],
            source=row[4],
            importance=row[5],
            tags=json.loads(row[6]),
            metadata=json.loads(row[7]) if row[7] else {}
        )


# 全局记忆存储实例
_global_store: MemoryStore | None = None


def get_memory_store(use_persistent: bool = False) -> MemoryStore:
    """获取全局记忆存储实例"""
    global _global_store

    if _global_store is None:
        if use_persistent:
            _global_store = SQLiteStore()
        else:
            _global_store = InMemoryStore()

    return _global_store


def reset_memory_store() -> None:
    """重置全局记忆存储"""
    global _global_store
    _global_store = None
