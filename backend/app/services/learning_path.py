from __future__ import annotations

import uuid
from collections import deque

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgePoint, KnowledgeEdge, KnowledgeState, User
from app.algorithms.bkt import BKTTracker, BKTEvidence, MasteryLevel
from app.algorithms.spaced_repetition import SpacedRepetitionScheduler, SpacedRepetitionItem
from app.schemas.knowledge import LearningPathNode, LearningPathResponse


class LearningPathService:
    """
    学习路径管理器.

    基于知识图谱的依赖关系和BKT掌握度，动态生成个性化学习路径。
    """

    def __init__(self):
        self.bkt = BKTTracker()
        self.sr_scheduler = SpacedRepetitionScheduler()

    async def get_learning_path(self, db: AsyncSession, user_id: uuid.UUID) -> LearningPathResponse:
        all_kps = (await db.execute(select(KnowledgePoint).order_by(KnowledgePoint.difficulty))).scalars().all()

        kp_map = {kp.id: kp for kp in all_kps}

        edges = (await db.execute(select(KnowledgeEdge))).scalars().all()
        prerequisites: dict[uuid.UUID, set[uuid.UUID]] = {}
        for edge in edges:
            if edge.to_kp_id not in prerequisites:
                prerequisites[edge.to_kp_id] = set()
            prerequisites[edge.to_kp_id].add(edge.from_kp_id)

        states = (
            await db.execute(select(KnowledgeState).where(KnowledgeState.user_id == user_id))
        ).scalars().all()
        state_map = {s.kp_id: s for s in states}

        nodes: list[LearningPathNode] = []
        mastered_count = 0
        current_kp_id: uuid.UUID | None = None

        for kp in all_kps:
            state = state_map.get(kp.id)
            p_know = state.bkt_p_know if state else 0.2
            mastery = state.mastery_level if state else "unlearned"

            prereq_ids = prerequisites.get(kp.id, set())
            is_unlocked = True
            if prereq_ids:
                for prereq_id in prereq_ids:
                    prereq_state = state_map.get(prereq_id)
                    if not prereq_state or prereq_state.bkt_p_know < 0.60:
                        is_unlocked = False
                        break

            is_current = False
            if is_unlocked and mastery not in ("learned", "mastered") and current_kp_id is None:
                is_current = True
                current_kp_id = kp.id

            if mastery in ("learned", "mastered"):
                mastered_count += 1

            nodes.append(
                LearningPathNode(
                    kp_id=kp.id,
                    title=kp.title,
                    difficulty=kp.difficulty,
                    mastery_level=mastery,
                    bkt_p_know=p_know,
                    is_unlocked=is_unlocked,
                    is_current=is_current,
                )
            )

        return LearningPathResponse(
            nodes=nodes,
            total_kps=len(all_kps),
            mastered_count=mastered_count,
            current_kp_id=current_kp_id,
        )

    async def update_knowledge_state(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        kp_id: uuid.UUID,
        evidence: BKTEvidence,
    ) -> KnowledgeState:
        result = await db.execute(
            select(KnowledgeState).where(
                KnowledgeState.user_id == user_id,
                KnowledgeState.kp_id == kp_id,
            )
        )
        state = result.scalar_one_or_none()

        if state is None:
            state = KnowledgeState(
                user_id=user_id,
                kp_id=kp_id,
                bkt_p_know=0.2,
            )
            db.add(state)
            await db.flush()

        p_before = state.bkt_p_know
        p_after = self.bkt.update(p_before, evidence)

        state.bkt_p_know = p_after
        state.total_attempts += 1
        if evidence.correct:
            state.correct_attempts += 1

        if evidence.correct and state.total_attempts > 0:
            state.independent_completion_rate = state.correct_attempts / state.total_attempts

        mastery = self.bkt.classify_mastery(
            p_after, state.independent_completion_rate, state.deformation_pass_rate
        )
        state.mastery_level = mastery.value

        sr_item = SpacedRepetitionItem(
            kp_id=str(kp_id),
            p_know=p_after,
            mastery_level=mastery.value,
            memory_stability=state.memory_stability,
            review_interval_days=state.review_interval_days,
            last_reviewed_at=state.last_reviewed_at,
            next_review_at=state.next_review_at,
            total_reviews=state.total_attempts,
            consecutive_correct=state.correct_attempts,
        )
        score = 1.0 if evidence.correct else 0.0
        sr_item = self.sr_scheduler.schedule(sr_item, score)

        state.memory_stability = sr_item.memory_stability
        state.review_interval_days = sr_item.review_interval_days
        state.next_review_at = sr_item.next_review_at
        state.last_reviewed_at = sr_item.last_reviewed_at

        await db.commit()
        await db.refresh(state)
        return state

    async def get_next_kp(self, db: AsyncSession, user_id: uuid.UUID) -> uuid.UUID | None:
        path = await self.get_learning_path(db, user_id)
        for node in path.nodes:
            if node.is_current:
                return node.kp_id
        return None

    async def get_review_plan(self, db: AsyncSession, user_id: uuid.UUID) -> dict:
        states = (
            await db.execute(select(KnowledgeState).where(KnowledgeState.user_id == user_id))
        ).scalars().all()

        items = [
            SpacedRepetitionItem(
                kp_id=str(s.kp_id),
                p_know=s.bkt_p_know,
                mastery_level=s.mastery_level,
                memory_stability=s.memory_stability,
                review_interval_days=s.review_interval_days,
                last_reviewed_at=s.last_reviewed_at,
                next_review_at=s.next_review_at,
                total_reviews=s.total_attempts,
                consecutive_correct=s.correct_attempts,
            )
            for s in states
        ]

        plan = self.sr_scheduler.generate_daily_plan(items)

        return {
            "review_items": [{"kp_id": i.kp_id, "priority": "review"} for i in plan["review"]],
            "new_items": [{"kp_id": i.kp_id, "priority": "surface"} for i in plan["surface"]],
            "challenge_items": [{"kp_id": i.kp_id, "priority": "challenge"} for i in plan["challenge"]],
        }

    def validate_knowledge_graph_dag(self, edges: list[tuple[uuid.UUID, uuid.UUID]]) -> list[uuid.UUID]:
        graph: dict[uuid.UUID, set[uuid.UUID]] = {}
        in_degree: dict[uuid.UUID, int] = {}
        all_nodes: set[uuid.UUID] = set()

        for from_id, to_id in edges:
            all_nodes.add(from_id)
            all_nodes.add(to_id)
            if from_id not in graph:
                graph[from_id] = set()
            graph[from_id].add(to_id)
            in_degree[to_id] = in_degree.get(to_id, 0) + 1
            in_degree.setdefault(from_id, 0)

        queue = deque([n for n in all_nodes if in_degree.get(n, 0) == 0])
        sorted_nodes: list[uuid.UUID] = []

        while queue:
            node = queue.popleft()
            sorted_nodes.append(node)
            for neighbor in graph.get(node, set()):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_nodes) != len(all_nodes):
            cycle_nodes = all_nodes - set(sorted_nodes)
            return list(cycle_nodes)

        return []


learning_path_service = LearningPathService()
