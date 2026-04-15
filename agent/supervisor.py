from __future__ import annotations

from agent.state import WorkflowState


class SupervisorAgent:
    """Decides the next action based on workflow state."""

    def decide_next_action(self, state: WorkflowState) -> str:
        # Hard-stop if parse failed.
        if state.profile is None and state.next_action != "parse_profile":
            return "parse_profile"

        if state.next_action == "parse_profile":
            return "crawl"

        if state.next_action == "crawl":
            return "extract"

        if state.next_action == "extract":
            return "match"

        if state.next_action == "match":
            return "critic"

        if state.next_action == "critic":
            if state.retry_count < state.max_retries:
                joined = "\n".join(state.critic_feedback)
                if "重试提取" in joined:
                    state.retry_count += 1
                    state.retry_target = "extract"
                    return "extract"
                if "重跑匹配" in joined:
                    state.retry_count += 1
                    state.retry_target = "match"
                    return "match"
            return "report"

        if state.next_action == "report":
            return "end"

        return "end"
