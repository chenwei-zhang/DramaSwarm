# -*- coding: utf-8 -*-
"""
观众 Agent 池 — 模拟社交媒体用户群体

基于规则生成观众评论（粉丝/路人/黑粉/理中客），可选接入 LLM。
"""

from __future__ import annotations

import random
from typing import Any

from swarmsim.crisis.models import PRAction, CrisisAction, AgentMessage


# ── 观众类型定义 ──

AUDIENCE_TYPES = ["粉丝", "路人", "理中客", "黑粉"]
AUDIENCE_RATIOS = [0.4, 0.3, 0.2, 0.1]

# ── 评论模板 ──

REACTION_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "粉丝": {
        PRAction.APOLOGIZE: [
            "我的爱豆知错能改，永远支持！",
            "加油！谁都会犯错，原谅{actor}！",
            "{actor}已经很努力了，大家别再骂了",
        ],
        PRAction.STATEMENT: [
            "相信{actor}！等真相大白！",
            "支持维权！{actor}加油！",
            "粉了这么多年，我信{actor}的人品",
        ],
        PRAction.SILENCE: [
            "{actor}为什么不说话啊，急死了",
            "别沉默了快回应吧呜呜",
        ],
        PRAction.COUNTERATTACK: [
            "{actor}霸气！就该怼回去！",
            "支持反击！造谣的才该封杀！",
        ],
        PRAction.PLAY_VICTIM: [
            "心疼{actor}，明明是受害者",
            "保护我方{actor}！太心疼了",
        ],
        PRAction.HIDE: [
            "{actor}好好休息，等你回来",
            "先避避风头也好，别看评论了",
        ],
        PRAction.CHARITY: [
            "{actor}一直都很善良！支持公益！",
            "这才是真正的{actor}，善良的人",
        ],
        "default": [
            "永远支持{actor}！",
            "{actor}加油！真爱粉永不脱粉！",
        ],
    },
    "路人": {
        PRAction.APOLOGIZE: [
            "道歉态度还行，看看后续吧",
            "知错能改善莫大焉，先观望",
        ],
        PRAction.STATEMENT: [
            "发个声明就完了？没说服力",
            "等事实说话，不站队",
        ],
        PRAction.SILENCE: [
            "不说话就是默认了吧",
            "沉默是金？还是心虚？",
        ],
        PRAction.COUNTERATTACK: [
            "越描越黑了",
            "这么硬刚只会更惨",
        ],
        PRAction.HIDE: [
            "躲得了初一躲不了十五",
            "避风头去了，过阵子又出来",
        ],
        "default": [
            "吃瓜吃瓜，不站队",
            "让子弹飞一会儿",
        ],
    },
    "理中客": {
        PRAction.APOLOGIZE: [
            "道歉是第一步，关键看后续行动",
            "态度可以，但需要拿出诚意",
        ],
        PRAction.STATEMENT: [
            "声明内容缺乏实质证据",
            "公关痕迹太重，建议直接上证据",
        ],
        PRAction.SILENCE: [
            "不回应是最差的公关策略",
            "信息真空只会让谣言更多",
        ],
        PRAction.COUNTERATTACK: [
            "法律维权是对的，但语气太冲",
            "反击不如拿出事实证据",
        ],
        PRAction.LAWSUIT: [
            "支持法律途径解决",
            "用法律说话是对的",
        ],
        "default": [
            "大家理性讨论，别被带节奏",
            "等官方通报吧",
        ],
    },
    "黑粉": {
        PRAction.APOLOGIZE: [
            "鳄鱼的眼泪，谁信啊",
            "道歉有用要警察干嘛？封杀！",
        ],
        PRAction.STATEMENT: [
            "洗白声明，呵呵",
            "公关稿写得好，事实呢？",
        ],
        PRAction.SILENCE: [
            "心虚了不敢说话了吧",
            "默认了，封杀！",
        ],
        PRAction.COUNTERATTACK: [
            "还敢嘴硬？越洗越黑",
            "死不认错，更加恶心",
        ],
        PRAction.PLAY_VICTIM: [
            "戏精本精，卖惨专业户",
            "演技真好，戏里戏外都在演",
        ],
        PRAction.CHARITY: [
            "公益洗白？太明显了吧",
            "做点好事就想抵消？做梦",
        ],
        "default": [
            "凉凉预定，坐等封杀",
            "抵制{actor}，拒绝劣迹艺人",
        ],
    },
}


class AudienceAgent:
    """单个观众 Agent"""

    # 语义相似的动作分组（同一组重复评论概率降低）
    SIMILAR_ACTION_GROUPS: list[set[PRAction]] = [
        {PRAction.SILENCE, PRAction.HIDE},
        {PRAction.APOLOGIZE, PRAction.CHARITY},
        {PRAction.STATEMENT, PRAction.GO_ON_SHOW},
    ]

    def __init__(self, persona_type: str, persons: list[str]):
        self.persona_type = persona_type
        self.bias: dict[str, float] = {}

        # 简易记忆：最近评论过的 (动作类型, 目标明星) 组合
        self._comment_history: list[tuple[PRAction, str]] = []
        self._max_history = 5

        # 根据观众类型设定对明星的偏好
        for person in persons:
            if persona_type == "粉丝":
                # 粉丝随机偏爱某一位
                self.bias[person] = random.uniform(0.3, 0.8)
            elif persona_type == "黑粉":
                self.bias[person] = random.uniform(-0.8, -0.3)
            elif persona_type == "理中客":
                self.bias[person] = random.uniform(-0.1, 0.1)
            else:  # 路人
                self.bias[person] = random.uniform(-0.3, 0.3)

        # 粉丝特别偏爱某一位
        if persona_type == "粉丝" and persons:
            fav = random.choice(persons)
            self.bias[fav] = random.uniform(0.7, 1.0)

    def _is_repetitive(self, action: PRAction, actor: str) -> bool:
        """检查是否对类似动作已评论过"""
        for past_action, past_actor in self._comment_history:
            if past_actor != actor:
                continue
            if past_action == action:
                return True
            # 检查语义相似
            for group in self.SIMILAR_ACTION_GROUPS:
                if past_action in group and action in group:
                    return True
        return False

    def react_to_action(
        self, action: CrisisAction, day: int
    ) -> AgentMessage | None:
        """对一条明星动作生成评论"""
        actor = action.actor
        bias = self.bias.get(actor, 0.0)

        # 记忆驱动：如果之前已对类似动作评论过，降低评论概率
        comment_prob = 0.3 + abs(bias) * 0.5
        if self._is_repetitive(action.action, actor):
            comment_prob *= 0.3  # 大幅降低重复评论概率
        if random.random() > comment_prob:
            return None

        # 选择模板
        templates = REACTION_TEMPLATES.get(self.persona_type, {})
        action_templates = templates.get(action.action, templates.get("default", []))
        if not action_templates:
            return None

        template = random.choice(action_templates)
        content = template.format(actor=actor)

        # 情绪判断
        if bias > 0.3:
            sentiment = "positive"
        elif bias < -0.3:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        msg = AgentMessage(
            sender=f"audience_{self.persona_type}_{id(self) % 1000}",
            content=content,
            day=day,
            sentiment=sentiment,
            source="audience",
        )

        # 记录评论历史
        self._comment_history.append((action.action, actor))
        if len(self._comment_history) > self._max_history:
            self._comment_history.pop(0)

        return msg


class AudiencePool:
    """管理一批观众 Agent"""

    def __init__(self, persons: list[str], pool_size: int = 30):
        self.persons = persons
        self.agents: list[AudienceAgent] = []

        # 按比例生成观众
        for i in range(pool_size):
            r = random.random()
            cumulative = 0.0
            chosen_type = AUDIENCE_TYPES[-1]
            for atype, ratio in zip(AUDIENCE_TYPES, AUDIENCE_RATIOS):
                cumulative += ratio
                if r < cumulative:
                    chosen_type = atype
                    break
            self.agents.append(AudienceAgent(chosen_type, persons))

    async def generate_reactions(
        self,
        day: int,
        actions: list[CrisisAction],
        state: dict,
    ) -> list[AgentMessage]:
        """根据当天明星动作生成观众评论

        每个 audience agent 对每条 action 独立生成评论。
        """
        reactions = []
        for agent in self.agents:
            for action in actions:
                msg = agent.react_to_action(action, day)
                if msg:
                    reactions.append(msg)
        return reactions

    def get_sentiment_summary(self) -> dict[str, Any]:
        """返回观众情绪概览"""
        type_counts: dict[str, int] = {}
        for agent in self.agents:
            type_counts[agent.persona_type] = type_counts.get(agent.persona_type, 0) + 1
        return {
            "pool_size": len(self.agents),
            "type_distribution": type_counts,
        }

    def get_person_bias(self, person: str) -> dict[str, float]:
        """获取观众群体对某人的平均偏好"""
        if not self.agents:
            return {"average_bias": 0.0, "support_ratio": 0.0}
        biases = [a.bias.get(person, 0.0) for a in self.agents]
        avg = sum(biases) / len(biases)
        support = sum(1 for b in biases if b > 0.3) / len(biases)
        return {"average_bias": round(avg, 2), "support_ratio": round(support, 2)}
