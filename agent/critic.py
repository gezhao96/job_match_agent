from __future__ import annotations

from agent.state import WorkflowState


class CriticAgent:
    """Lightweight quality gate for extraction/match outputs."""

    def review(self, state: WorkflowState) -> WorkflowState:
        feedback: list[str] = []

        if not state.job_infos:
            feedback.append("未提取到岗位信息，建议回退至抓取或提取阶段。")

        recruitment_count = sum(1 for info in state.job_infos if info.is_recruitment_related)
        if state.job_infos and recruitment_count == 0:
            feedback.append("提取结果全部判定为非招聘内容，建议重试提取。")

        # 信息完整度：如果多数岗位缺失关键字段，建议重试提取。
        incomplete = 0
        for info in state.job_infos:
            if not info.is_recruitment_related:
                continue
            if not (info.company_name and info.job_title and (info.requirements or info.summary)):
                incomplete += 1

        if recruitment_count > 0 and incomplete / max(recruitment_count, 1) > 0.6:
            feedback.append("岗位关键信息缺失比例较高，建议重试提取。")

        # 评分一致性检查：高分但不推荐、低分但强推荐。
        inconsistent = 0
        for item in state.matched_items:
            score = item.match.match_score
            rec = item.match.recommendation
            if (score >= 80 and rec != "强推荐") or (score < 55 and rec == "强推荐"):
                inconsistent += 1

        if inconsistent > 0:
            feedback.append(f"发现 {inconsistent} 条评分与推荐等级不一致，建议重跑匹配。")

        state.critic_feedback = feedback
        return state
