"""Governance reviewer — orchestrates AI review via claude --print."""

import json
import os
import subprocess
import tempfile
from typing import Optional

from .models import Decision, Finding, ReviewVerdict, Verdict


class GovernanceReviewer:
    """Runs claude --print with governance-reviewer context for AI-powered review."""

    def review_decision(
        self,
        decision: Decision,
        vision_standards: list[dict],
        architecture: list[dict],
    ) -> ReviewVerdict:
        """Review a single decision against vision and architecture standards."""
        prompt = self._build_decision_prompt(decision, vision_standards, architecture)
        raw = self._run_claude(prompt, timeout=60)
        return self._parse_verdict(raw, decision_id=decision.id)

    def review_plan(
        self,
        task_id: str,
        plan_summary: str,
        plan_content: str,
        decisions: list[Decision],
        reviews: list[ReviewVerdict],
        vision_standards: list[dict],
        architecture: list[dict],
    ) -> ReviewVerdict:
        """Review a complete plan with full accumulated context."""
        prompt = self._build_plan_prompt(
            plan_summary,
            plan_content,
            decisions,
            reviews,
            vision_standards,
            architecture,
        )
        raw = self._run_claude(prompt, timeout=120)
        return self._parse_verdict(raw, plan_id=task_id)

    def review_task_group(
        self,
        tasks: list[dict],
        transcript_excerpt: str,
        vision_standards: list[dict],
        architecture: list[dict],
    ) -> ReviewVerdict:
        """Review a group of tasks holistically for collective vision/architecture compliance.

        Individual tasks may look fine in isolation, but together they might
        introduce an unauthorized architectural shift (e.g., 5 tasks that
        collectively build an ORM layer that violates vision standards).

        Args:
            tasks: List of dicts with 'subject', 'description', 'impl_id'
            transcript_excerpt: Recent agent reasoning from transcript JSONL
            vision_standards: Vision-tier entities from the KG
            architecture: Architecture-tier entities from the KG

        Returns:
            ReviewVerdict with holistic assessment
        """
        prompt = self._build_group_review_prompt(
            tasks, transcript_excerpt, vision_standards, architecture
        )
        raw = self._run_claude(prompt, timeout=120)
        return self._parse_verdict(raw)

    def review_completion(
        self,
        task_id: str,
        summary_of_work: str,
        files_changed: list[str],
        decisions: list[Decision],
        reviews: list[ReviewVerdict],
        vision_standards: list[dict],
    ) -> ReviewVerdict:
        """Review completed work for final governance check."""
        prompt = self._build_completion_prompt(
            summary_of_work, files_changed, decisions, reviews, vision_standards
        )
        raw = self._run_claude(prompt, timeout=90)
        return self._parse_verdict(raw, plan_id=task_id)

    def _run_claude(self, prompt: str, timeout: int = 60) -> str:
        """Run claude --print and return the raw output.

        Uses temp files for input/output to avoid CLI argument length limits
        and pipe buffering issues.

        When the ``GOVERNANCE_MOCK_REVIEW`` environment variable is set,
        returns a deterministic "approved" verdict without invoking the
        ``claude`` binary.  Used by the E2E test harness.
        """
        if os.environ.get("GOVERNANCE_MOCK_REVIEW"):
            return json.dumps({
                "verdict": "approved",
                "findings": [],
                "guidance": "Mock review: auto-approved for E2E testing.",
                "standards_verified": ["mock"],
            })

        input_fd, input_path = tempfile.mkstemp(prefix="avt-gov-", suffix="-input.md")
        output_fd, output_path = tempfile.mkstemp(prefix="avt-gov-", suffix="-output.md")

        try:
            # Write prompt to temp input file
            with os.fdopen(input_fd, "w") as f:
                f.write(prompt)
            # input_fd is now closed by os.fdopen

            # Close output_fd so subprocess can write to it
            os.close(output_fd)

            # Run claude with file-based I/O
            with open(input_path) as fin, open(output_path, "w") as fout:
                result = subprocess.run(
                    ["claude", "--print"],
                    stdin=fin,
                    stdout=fout,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout,
                )

            if result.returncode != 0:
                return json.dumps(
                    {
                        "verdict": "needs_human_review",
                        "findings": [
                            {
                                "tier": "quality",
                                "severity": "logic",
                                "description": f"Reviewer process failed: {result.stderr[:500]}",
                                "suggestion": "Review manually",
                            }
                        ],
                        "guidance": "Automated review failed. Manual review required.",
                        "standards_verified": [],
                    }
                )

            # Read output from temp file
            with open(output_path) as f:
                return f.read()

        except subprocess.TimeoutExpired:
            return json.dumps(
                {
                    "verdict": "needs_human_review",
                    "findings": [],
                    "guidance": "Review timed out. Manual review required.",
                    "standards_verified": [],
                }
            )
        except FileNotFoundError:
            return json.dumps(
                {
                    "verdict": "needs_human_review",
                    "findings": [],
                    "guidance": "claude CLI not found. Manual review required.",
                    "standards_verified": [],
                }
            )
        finally:
            # Clean up temp files
            for p in (input_path, output_path):
                try:
                    os.unlink(p)
                except OSError:
                    pass

    def _parse_verdict(
        self,
        raw: str,
        decision_id: Optional[str] = None,
        plan_id: Optional[str] = None,
    ) -> ReviewVerdict:
        """Parse claude --print output into a ReviewVerdict."""
        # Try to extract JSON from the response
        json_str = self._extract_json(raw)
        if json_str:
            try:
                data = json.loads(json_str)
                findings = [
                    Finding(
                        tier=f.get("tier", "quality"),
                        severity=f.get("severity", "logic"),
                        description=f.get("description", ""),
                        suggestion=f.get("suggestion", ""),
                        strengths=f.get("strengths", []),
                        salvage_guidance=f.get("salvage_guidance", ""),
                    )
                    for f in data.get("findings", [])
                ]
                verdict_str = data.get("verdict", "needs_human_review")
                try:
                    verdict = Verdict(verdict_str)
                except ValueError:
                    verdict = Verdict.NEEDS_HUMAN_REVIEW

                return ReviewVerdict(
                    decision_id=decision_id,
                    plan_id=plan_id,
                    verdict=verdict,
                    findings=findings,
                    guidance=data.get("guidance", ""),
                    strengths_summary=data.get("strengths_summary", ""),
                    standards_verified=data.get("standards_verified", []),
                )
            except (json.JSONDecodeError, KeyError):
                pass

        # Fallback: couldn't parse structured response
        return ReviewVerdict(
            decision_id=decision_id,
            plan_id=plan_id,
            verdict=Verdict.NEEDS_HUMAN_REVIEW,
            findings=[],
            guidance=f"Could not parse structured review. Raw response:\n{raw[:1000]}",
            standards_verified=[],
        )

    def _extract_json(self, text: str) -> Optional[str]:
        """Extract a JSON object from text that may contain markdown or other content."""
        # Try the whole string first
        text = text.strip()
        if text.startswith("{"):
            return text

        # Look for ```json ... ``` blocks
        import re

        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Look for first { to last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]

        return None

    def _build_decision_prompt(
        self,
        decision: Decision,
        vision_standards: list[dict],
        architecture: list[dict],
    ) -> str:
        standards_text = self._format_standards(vision_standards)
        arch_text = self._format_architecture(architecture)
        alts_text = "\n".join(
            f"  - {a.option}: rejected because {a.reason_rejected}"
            for a in decision.alternatives_considered
        )

        return f"""You are a governance reviewer. Evaluate this decision against the project's vision and architecture standards.

## Vision Standards
{standards_text}

## Architecture Patterns
{arch_text}

## Decision to Review
- **Agent**: {decision.agent}
- **Category**: {decision.category.value}
- **Summary**: {decision.summary}
- **Detail**: {decision.detail}
- **Components affected**: {', '.join(decision.components_affected)}
- **Alternatives considered**:
{alts_text or '  (none provided)'}
- **Confidence**: {decision.confidence.value}

## Instructions

Apply PIN (Positive, Innovative, Negative) methodology in your review:

### 1. POSITIVE: Identify Strengths
- What aspects of this decision are sound and well-reasoned?
- Which standards does the decision naturally align with?
- What should be preserved regardless of the verdict?

### 2. INNOVATIVE: Acknowledge Good Thinking
- What creative or thoughtful aspects does this decision show?
- Are there elements that demonstrate understanding of the project's patterns?

### 3. NEGATIVE: Assess Concerns (if any)
- Does this decision CONFLICT with any vision standard? If yes, verdict is "blocked".
- Does it deviate unjustifiably from architecture patterns? If yes, verdict is "blocked".
- If the category is "deviation" or "scope_change", verdict should be "needs_human_review".
- If the decision aligns with standards, verdict is "approved".

For EVERY finding, include what related work can be preserved and what is specifically problematic.

Respond with ONLY a JSON object (no markdown, no explanation outside the JSON):
{{
  "verdict": "approved" | "blocked" | "needs_human_review",
  "strengths_summary": "1-2 sentences on what the decision gets right overall",
  "findings": [
    {{
      "tier": "vision" | "architecture" | "quality",
      "severity": "vision_conflict" | "architectural" | "logic",
      "description": "what specifically is problematic",
      "suggestion": "concrete fix that preserves the good parts",
      "strengths": ["what is sound about the related work"],
      "salvage_guidance": "what can be preserved and how to pivot the problematic part"
    }}
  ],
  "guidance": "acknowledge strengths, then direct specific changes",
  "standards_verified": ["list of standards that were checked and passed"]
}}"""

    def _build_plan_prompt(
        self,
        plan_summary: str,
        plan_content: str,
        decisions: list[Decision],
        reviews: list[ReviewVerdict],
        vision_standards: list[dict],
        architecture: list[dict],
    ) -> str:
        standards_text = self._format_standards(vision_standards)
        arch_text = self._format_architecture(architecture)

        decisions_text = "\n".join(
            f"  - [{d.category.value}] {d.summary} (confidence: {d.confidence.value})"
            for d in decisions
        )
        reviews_text = "\n".join(
            f"  - Decision {r.decision_id}: {r.verdict.value} — {r.guidance[:100]}"
            for r in reviews
        )

        return f"""You are a governance reviewer. Evaluate this complete plan against vision and architecture standards.

## Vision Standards
{standards_text}

## Architecture Patterns
{arch_text}

## Prior Decisions for This Task
{decisions_text or '(none)'}

## Prior Reviews
{reviews_text or '(none)'}

## Plan to Review
**Summary**: {plan_summary}

**Full Plan**:
{plan_content}

## Instructions

Apply PIN (Positive, Innovative, Negative) methodology:

### 1. POSITIVE: What's Right About This Plan
- Which parts align with vision standards?
- What structural decisions are sound?
- What would be lost if the agent started over completely?

### 2. INNOVATIVE: Creative Elements
- What aspects show good understanding of the project?
- Any novel but valid approaches worth preserving?

### 3. NEGATIVE: Concerns (if any)
1. Verify the plan aligns with ALL applicable vision standards.
2. Verify the plan follows established architecture patterns.
3. Check that prior decision reviews have been respected (no blocked decisions reimplemented).
4. Identify any gaps, risks, or concerns.

For blocked verdicts: your guidance MUST specify which parts of the plan are sound and should be preserved, and which specific parts need revision.

Respond with ONLY a JSON object:
{{
  "verdict": "approved" | "blocked" | "needs_human_review",
  "strengths_summary": "what the plan gets right, so the agent knows what to preserve",
  "findings": [
    {{
      "tier": "vision" | "architecture" | "quality",
      "severity": "vision_conflict" | "architectural" | "logic",
      "description": "what specifically is problematic",
      "suggestion": "minimal change to fix while preserving good work",
      "strengths": ["what is sound in the related area"],
      "salvage_guidance": "what to keep, what to change"
    }}
  ],
  "guidance": "acknowledge strengths, then direct specific changes",
  "standards_verified": ["list of verified standards"]
}}"""

    def _build_completion_prompt(
        self,
        summary_of_work: str,
        files_changed: list[str],
        decisions: list[Decision],
        reviews: list[ReviewVerdict],
        vision_standards: list[dict],
    ) -> str:
        standards_text = self._format_standards(vision_standards)
        decisions_text = "\n".join(
            f"  - [{d.category.value}] {d.summary}" for d in decisions
        )
        reviews_text = "\n".join(
            f"  - Decision {r.decision_id}: {r.verdict.value}" for r in reviews
        )

        return f"""You are a governance reviewer. Evaluate this completed work.

## Vision Standards
{standards_text}

## Decisions Made During This Task
{decisions_text or '(none)'}

## Review Verdicts
{reviews_text or '(none)'}

## Completed Work
**Summary**: {summary_of_work}
**Files changed**: {', '.join(files_changed)}

## Instructions

Apply PIN methodology to your final review:

### Assessment
1. **Strengths**: What did this work accomplish well? Acknowledge completed standards alignment.
2. **Concerns**: Check that all decisions were reviewed. Check that no blocked decisions were implemented anyway. Verify alignment with vision standards.
3. **Guidance**: If blocking, specify exactly what needs to change and what is already correct.

Respond with ONLY a JSON object:
{{
  "verdict": "approved" | "blocked" | "needs_human_review",
  "strengths_summary": "what the completed work achieves well",
  "findings": [
    {{
      "tier": "vision" | "architecture" | "quality",
      "severity": "vision_conflict" | "architectural" | "logic",
      "description": "what specifically is problematic",
      "suggestion": "concrete fix",
      "strengths": ["what is sound about the related work"],
      "salvage_guidance": "what to preserve"
    }}
  ],
  "guidance": "acknowledge completed work strengths before directing any needed changes",
  "standards_verified": ["list of verified standards"]
}}"""

    def _build_group_review_prompt(
        self,
        tasks: list[dict],
        transcript_excerpt: str,
        vision_standards: list[dict],
        architecture: list[dict],
    ) -> str:
        standards_text = self._format_standards(vision_standards)
        arch_text = self._format_architecture(architecture)

        tasks_text = "\n".join(
            f"  {i+1}. **{t['subject']}**: {t.get('description', '')[:200]}"
            for i, t in enumerate(tasks)
        )

        return f"""You are a governance reviewer performing a HOLISTIC review. You are evaluating multiple tasks as a GROUP, not individually.

## Why This Review Matters

Individual tasks may each look reasonable in isolation. But together, they may represent:
- An unauthorized architectural shift (e.g., 5 tasks that collectively build an ORM layer)
- Scope creep beyond the original intent
- A pattern that conflicts with vision standards when viewed collectively
- Work that duplicates or contradicts existing architecture

Your job is to identify what these tasks COLLECTIVELY represent and whether that collective intent aligns with project standards.

## Vision Standards
{standards_text}

## Architecture Patterns
{arch_text}

## Tasks Under Review (as a group)
{tasks_text}

## Agent's Recent Reasoning (from transcript)
{transcript_excerpt}

## Instructions

Apply PIN (Positive, Innovative, Negative) methodology to your holistic assessment:

### 1. POSITIVE: What's Sound
- Which individual tasks are well-scoped and aligned?
- What does the task decomposition get right?
- Are there tasks that should proceed unchanged?

### 2. INNOVATIVE: Good Collective Thinking
- Does the task group show thoughtful decomposition?
- Are there smart dependency orderings or logical groupings?

### 3. NEGATIVE: Collective Concerns
1. **COLLECTIVE INTENT**: In one sentence, what do these tasks collectively aim to accomplish?
2. **Vision Check**: Does the collective intent conflict with any vision standard? A single task adding a "model" is fine; five tasks collectively building an ORM layer might violate "No ORM" standards.
3. **Architecture Check**: Does the collective intent introduce unauthorized architectural patterns?
4. **Scope Check**: Are these tasks proportional, or do they represent scope creep?
5. **Cross-Task Analysis**: Are any tasks problematic only when considered with their siblings?

For blocked verdicts: your guidance MUST list which specific tasks are problematic and which are sound. The agent should know which tasks to keep, which to revise, and which to remove.

Respond with ONLY a JSON object (no markdown, no explanation outside the JSON):
{{
  "verdict": "approved" | "blocked" | "needs_human_review",
  "strengths_summary": "which tasks and aspects of the decomposition are sound",
  "findings": [
    {{
      "tier": "vision" | "architecture" | "quality",
      "severity": "vision_conflict" | "architectural" | "logic",
      "description": "what was found when evaluating tasks AS A GROUP",
      "suggestion": "how to fix it while preserving the sound tasks",
      "strengths": ["which related tasks/aspects are fine"],
      "salvage_guidance": "which tasks to keep, which to revise, which to remove"
    }}
  ],
  "guidance": "acknowledge sound tasks and good decomposition, then direct specific changes needed",
  "standards_verified": ["list of standards that were checked and passed"]
}}"""

    def _format_standards(self, standards: list[dict]) -> str:
        if not standards:
            return "(no vision standards found in KG)"
        lines = []
        for s in standards:
            name = s.get("name", "unknown")
            obs = "; ".join(s.get("observations", []))
            lines.append(f"- **{name}**: {obs}")
        return "\n".join(lines)

    def _format_architecture(self, architecture: list[dict]) -> str:
        if not architecture:
            return "(no architecture entities found in KG)"
        lines = []
        for a in architecture:
            name = a.get("name", "unknown")
            etype = a.get("entityType", "")
            obs = "; ".join(a.get("observations", [])[:3])
            lines.append(f"- **{name}** ({etype}): {obs}")
        return "\n".join(lines)
