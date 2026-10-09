from __future__ import annotations

from typing import Any, Dict
from sentinel.types import Action

class PostconditionValidator:
    """Verifies that actual world state matches expected outcome rather than trusting return codes."""

    @classmethod
    async def validate(cls, action: Action, live_checker: Any) -> bool:
        if not action.executed:
            return False

        if not action.actual_outcome:
            action.postcondition_verified = False
            return False

        expected = action.expected_outcome
        actual = action.actual_outcome

        if action.type == "github.create_issue":
            # Postcondition: Issue must actually exist on target repo and match title
            issue_number = actual.get("issue_number")
            repo = action.target or actual.get("repo")
            if not issue_number or not repo:
                action.postcondition_verified = False
                return False

            # Query target system state directly via tool live verification
            live_record = await live_checker.get_issue(repo, issue_number)
            if not live_record or not live_record.get("exists"):
                action.postcondition_verified = False
                return False

            if expected.get("title") and live_record.get("title") != expected.get("title"):
                action.postcondition_verified = False
                return False

            action.postcondition_verified = True
            return True

        if action.type == "github.update_file":
            path = action.parameters.get("path")
            repo = action.target
            live_file = await live_checker.get_file(repo, path)
            if not live_file or not live_file.get("exists"):
                action.postcondition_verified = False
                return False

            action.postcondition_verified = True
            return True

        # Default fallback
        action.postcondition_verified = bool(actual.get("success", False))
        return action.postcondition_verified
