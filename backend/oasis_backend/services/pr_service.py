"""
PR Service: pre-push Gatekeeper evaluation, authenticated push & PR opening, and webhook tracking.
"""

from __future__ import annotations
import hashlib
import hmac
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
import httpx
from oasis_agent.git_ops.client import GitClient
from oasis_agent.github_api import GitHubClientManager, PullRequestManager
from oasis_agent.models import GitDiffSummary, IssueContext
from oasis_agent.llm.prompts import PR_DESCRIPTION_PROMPT
from oasis_backend.config import settings
from oasis_backend.database.repositories.pr_repo import PullRequestRepository
from oasis_backend.models.agent import GatekeeperVerdictResponse
from oasis_backend.models.pr import PRStatusResponse, PushPRResponse
from oasis_backend.services.agent_gateway import AgentGatewayService
from oasis_backend.services.auth_service import AuthService
from oasis_backend.services.scoring_service import ScoringService
from oasis_backend.services.workspace_service import WorkspaceService


class PRService:
    def __init__(
        self,
        pr_repo: PullRequestRepository,
        workspace_service: WorkspaceService,
        agent_gateway: AgentGatewayService,
        auth_service: AuthService,
        scoring_service: ScoringService,
    ):
        self.pr_repo = pr_repo
        self.workspace_service = workspace_service
        self.agent_gateway = agent_gateway
        self.auth_service = auth_service
        self.scoring_service = scoring_service

    async def evaluate_and_push(
        self,
        user_id: int,
        workspace_id: str,
        custom_commit_message: Optional[str] = None,
        dry_run: bool = False,
        force: bool = False,
    ) -> PushPRResponse:
        """
        1. Collects workspace diff.
        2. Evaluates meaningfulness via oasis-agent Gatekeeper.
        3. If rejected and not forced -> halts, returns rejection details.
        4. If approved (or force=True) -> commits, pushes branch to GitHub, opens PR with user's OAuth token.
        """
        session, local_path = self.workspace_service.get_workspace_or_404(workspace_id, user_id)
        git_client = GitClient(local_path)

        # 1. Collect diff
        base_branch = "main"
        for cand in ["main", "master"]:
            try:
                git_client._run(["rev-parse", "--verify", cand])
                base_branch = cand
                break
            except Exception:
                pass

        diff_summary: GitDiffSummary = git_client.get_diff(base=base_branch)
        if not diff_summary.diff_content.strip():
            diff_summary = git_client.get_diff()

        if not diff_summary.diff_content.strip():
            verdict = GatekeeperVerdictResponse(
                meaningful=False,
                confidence=1.0,
                reasoning="Diff is completely empty. Please modify code in the Monaco editor before pushing.",
                recommended_action="REJECT",
                rejection_reason="No code modifications detected in workspace.",
            )
            return PushPRResponse(
                success=False,
                status="rejected",
                gatekeeper=verdict,
                gatekeeper_verdict=verdict,
            )

        # Load issue context
        issue_file = local_path / ".oasis-agent" / "issue.json"
        if issue_file.exists():
            issue_ctx = IssueContext.model_validate_json(issue_file.read_text(encoding="utf-8"))
        else:
            issue_ctx = IssueContext(
                repo_url=session.repo_url,
                repo_name=session.repo_full_name,
                issue_number=session.issue_number,
                title=f"Issue #{session.issue_number}",
                body="Target issue context.",
            )

        # 2. Gatekeeper meaningfulness evaluation
        verdict = self.agent_gateway.evaluate_diff(
            local_path=local_path,
            issue_ctx=issue_ctx,
            diff_summary=diff_summary,
        )

        # 3. Check decision (allow override if force=True)
        if (not verdict.meaningful or verdict.recommended_action != "APPROVE_AND_PR") and not force:
            status = "flagged_human_review" if verdict.recommended_action == "FLAG_FOR_HUMAN_REVIEW" else "rejected"
            return PushPRResponse(
                success=False,
                status=status,
                gatekeeper=verdict,
                gatekeeper_verdict=verdict,
            )

        # Dry run return
        if dry_run:
            return PushPRResponse(
                success=True,
                status="dry_run",
                branch_name=session.branch_name,
                gatekeeper=verdict,
                gatekeeper_verdict=verdict,
            )

        # 4. Gatekeeper APPROVED (or bypassed via Push Anyway): stage, commit, push, and open PR
        user_token = self.auth_service.get_decrypted_user_token(user_id)
        if not user_token:
            raise PermissionError("User GitHub OAuth token missing or expired. Please re-authenticate.")

        # Stage and commit
        git_client.stage_all()
        commit_msg = custom_commit_message or f"fix(#{session.issue_number}): resolve {issue_ctx.title}"
        if force and (not verdict.meaningful or verdict.recommended_action != "APPROVE_AND_PR"):
            commit_msg += " [push-anyway bypass]"
        try:
            git_client.commit(commit_msg)
        except Exception:
            pass  # Already committed

        # Push branch
        git_client.push(session.branch_name, token=user_token)

        # Generate PR Description using LLM
        gatekeeper_label = "Approved by oasis-agent Meaningfulness Gatekeeper" if (verdict.meaningful and verdict.recommended_action == "APPROVE_AND_PR") else "Overridden via Push Anyway (Author bypass)"
        pr_body = (
            f"### Overview\nResolves #{session.issue_number}: {issue_ctx.title}\n\n"
            f"### Gatekeeper Review\n"
            f"- **Evaluation**: {gatekeeper_label}\n"
            f"- **Confidence**: {int(verdict.confidence * 100)}%\n"
            f"- **Reasoning**: {verdict.reasoning}\n\n"
            f"### Changes\n"
            f"+{diff_summary.insertions} / -{diff_summary.deletions} across {len(diff_summary.files_changed)} files."
        )

        try:
            prompt = PR_DESCRIPTION_PROMPT.format(
                issue_number=session.issue_number,
                issue_title=issue_ctx.title,
                issue_body=issue_ctx.body,
                diff_summary=f"+{diff_summary.insertions} / -{diff_summary.deletions}",
                test_results="Not executed",
            )
            llm_body, _ = self.agent_gateway.llm_client.complete(
                prompt=prompt,
                task_type="pr_description_generation",
            )
            if llm_body and len(llm_body.strip()) > 20:
                pr_body = llm_body
        except Exception:
            pass

        # Create PR via GitHub API with User Token
        gh_mgr = GitHubClientManager(token=user_token)
        pr_mgr = PullRequestManager(gh_mgr)
        pr_title = f"Fixes #{session.issue_number}: {issue_ctx.title}"

        pr_number, pr_url = pr_mgr.create_pull_request(
            repo_full_name=session.repo_full_name,
            title=pr_title,
            body=pr_body,
            head_branch=session.branch_name,
            base_branch=base_branch,
        )

        pr_id = f"pr_{uuid.uuid4().hex[:12]}"
        self.pr_repo.create(
            pr_id=pr_id,
            workspace_id=workspace_id,
            user_id=user_id,
            repo_full_name=session.repo_full_name,
            pr_number=pr_number,
            pr_url=pr_url,
            head_branch=session.branch_name,
            base_branch=base_branch,
            gatekeeper_verdict=verdict.model_dump(),
            status="open",
            ci_status="pending",
        )

        return PushPRResponse(
            success=True,
            status="approved_pr_opened",
            pr_url=pr_url,
            pr_number=pr_number,
            branch_name=session.branch_name,
            gatekeeper=verdict,
            gatekeeper_verdict=verdict,
            ci_status="pending",
        )

    def verify_webhook_signature(self, payload_body: bytes, signature_header: Optional[str]) -> bool:
        """Verifies GitHub X-Hub-Signature-256 HMAC."""
        if not settings.github_webhook_secret:
            return True  # If not configured, bypass
        if not signature_header or not signature_header.startswith("sha256="):
            return False
        expected = hmac.new(
            settings.github_webhook_secret.encode("utf-8"),
            payload_body,
            hashlib.sha256,
        ).hexdigest()
        actual = signature_header.split("sha256=")[-1]
        return hmac.compare_digest(expected, actual)

    async def handle_github_webhook(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handles incoming GitHub webhook events:
        - pull_request (closed: merged or closed without merge)
        - check_run / status (CI check updates)
        """
        if event_type == "pull_request":
            action = payload.get("action")
            pr_data = payload.get("pull_request", {})
            pr_number = pr_data.get("number")
            repo_full_name = payload.get("repository", {}).get("full_name")
            is_merged = pr_data.get("merged", False)

            if not repo_full_name or not pr_number:
                return {"handled": False, "reason": "Missing repo or PR number"}

            match = self.pr_repo.get_by_repo_and_number(repo_full_name, pr_number)
            if not match:
                return {"handled": False, "reason": f"PR {repo_full_name}#{pr_number} not tracked"}

            pr_rec, user_id = match

            if action == "closed":
                if is_merged:
                    self.pr_repo.update_status(pr_rec.pr_id, "merged", merged=True)
                    # Trigger scoring!
                    stars = payload.get("repository", {}).get("stargazers_count", 50)
                    gk = pr_rec.gatekeeper or {}
                    conf = gk.get("confidence", 0.85)
                    insertions = pr_data.get("additions", 15)
                    deletions = pr_data.get("deletions", 5)

                    cnt = self.scoring_service.award_merged_pr(
                        user_id=user_id,
                        pr_id=pr_rec.pr_id,
                        gatekeeper_confidence=conf,
                        insertions=insertions,
                        deletions=deletions,
                        repo_stars=stars,
                    )
                    return {
                        "handled": True,
                        "action": "merged_and_scored",
                        "score_awarded": cnt.total_score,
                    }
                else:
                    self.pr_repo.update_status(pr_rec.pr_id, "closed")
                    return {"handled": True, "action": "closed_without_merge"}

        elif event_type in ["check_run", "status"]:
            # Surface CI check results
            repo_full_name = payload.get("repository", {}).get("full_name")
            status_val = "pending"
            if event_type == "check_run":
                conclusion = payload.get("check_run", {}).get("conclusion")
                status_val = "success" if conclusion == "success" else ("failure" if conclusion else "pending")
            elif event_type == "status":
                state = payload.get("state")
                status_val = "success" if state == "success" else ("failure" if state in ["failure", "error"] else "pending")

            return {"handled": True, "event": event_type, "ci_status": status_val}

        return {"handled": False, "reason": f"Unhandled event type '{event_type}'"}

    async def poll_pr_status(self, pr_id: str, github_token: Optional[str] = None) -> Optional[PRStatusResponse]:
        """Polling fallback for tracking PR merge status without webhooks."""
        pr = self.pr_repo.get_by_id(pr_id)
        if not pr:
            return None
        if pr.status in ["merged", "closed"]:
            return pr

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Oasis-Platform",
        }
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    f"https://api.github.com/repos/{pr.repo_full_name}/pulls/{pr.pr_number}",
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    is_merged = data.get("merged", False)
                    state = data.get("state", "open")

                    if state == "closed":
                        new_status = "merged" if is_merged else "closed"
                        self.pr_repo.update_status(pr.pr_id, new_status, merged=is_merged)
                        if is_merged:
                            # Award score
                            stars = data.get("base", {}).get("repo", {}).get("stargazers_count", 50)
                            gk = pr.gatekeeper or {}
                            conf = gk.get("confidence", 0.85)
                            insertions = data.get("additions", 15)
                            deletions = data.get("deletions", 5)

                            # Fetch user id
                            match = self.pr_repo.get_by_repo_and_number(pr.repo_full_name, pr.pr_number)
                            if match:
                                _, u_id = match
                                self.scoring_service.award_merged_pr(
                                    user_id=u_id,
                                    pr_id=pr.pr_id,
                                    gatekeeper_confidence=conf,
                                    insertions=insertions,
                                    deletions=deletions,
                                    repo_stars=stars,
                                )
                        return self.pr_repo.get_by_id(pr_id)
            except Exception:
                pass

        return pr
