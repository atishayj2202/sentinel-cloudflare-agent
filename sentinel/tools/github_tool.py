from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from sentinel.config import config

logger = logging.getLogger("sentinel.tools.github")

class GitHubTool:
    """GitHub integration with MCP-compatible API and injectable fault simulation."""

    def __init__(self) -> None:
        self.token = config.GITHUB_TOKEN
        self.default_repo = config.GITHUB_DEFAULT_REPO
        # In-memory repository store for sandbox / deterministic execution
        self._mock_issues: Dict[str, Dict[int, Dict[str, Any]]] = {}
        self._mock_files: Dict[str, Dict[str, str]] = {}
        # Fault injection state
        self.fault_countdown: int = 0
        self.fault_error_code: int = 503

        # Seed with initial repository context
        self._mock_files[self.default_repo] = {
            "README.md": "# Sentinel\nAutonomous Self-Verifying Agent",
            "wrangler.jsonc": '{"name": "sentinel-agent"}',
        }

    def inject_transient_fault(self, count: int = 1, code: int = 503) -> None:
        """Inject failures for next N requests to demonstrate durable workflow recovery."""
        self.fault_countdown = count
        self.fault_error_code = code

    async def get_issue(self, repo: str, issue_number: int) -> Dict[str, Any]:
        """Check live issue state for postcondition verification."""
        repo = repo or self.default_repo
        if repo in self._mock_issues and issue_number in self._mock_issues[repo]:
            issue = self._mock_issues[repo][issue_number]
            return {
                "exists": True,
                "number": issue_number,
                "title": issue["title"],
                "body": issue["body"],
                "state": issue.get("state", "open"),
            }
        return {"exists": False}

    async def get_file(self, repo: str, path: str) -> Dict[str, Any]:
        """Check file state."""
        repo = repo or self.default_repo
        if repo in self._mock_files and path in self._mock_files[repo]:
            return {
                "exists": True,
                "path": path,
                "content": self._mock_files[repo][path],
            }
        return {"exists": False}

    async def create_issue(
        self, repo: str, title: str, body: str, labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create an issue with fault simulation check."""
        repo = repo or self.default_repo

        # Check injected fault
        if self.fault_countdown > 0:
            self.fault_countdown -= 1
            logger.warning(
                f"[FAULT INJECTION] github.create_issue simulated {self.fault_error_code} Service Unavailable"
            )
            raise RuntimeError(
                f"GitHub API Error {self.fault_error_code}: Service Unavailable (Simulated Fault)"
            )

        if repo not in self._mock_issues:
            self._mock_issues[repo] = {}

        issue_num = len(self._mock_issues[repo]) + 101
        self._mock_issues[repo][issue_num] = {
            "title": title,
            "body": body,
            "labels": labels or ["sentinel-verified"],
            "state": "open",
        }

        return {
            "success": True,
            "repo": repo,
            "issue_number": issue_num,
            "html_url": f"https://github.com/{repo}/issues/{issue_num}",
            "title": title,
        }

github_tool = GitHubTool()
