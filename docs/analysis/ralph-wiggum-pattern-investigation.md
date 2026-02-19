# Ralph Wiggum Pattern Investigation

## Autonomous Iteration Loops for Claude Code: Applicability to AVT

**Investigation Date**: 2026-02-18
**Status**: Investigation Complete; Selective Adoption Recommended
**Scope**: Ralph Wiggum plugin pattern vs. AVT session-scoped governance

---

## 1. What Is the Ralph Wiggum Pattern?

The [Ralph Wiggum plugin](https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum) is Anthropic's official Claude Code plugin for autonomous, long-running iterative development. Named after the Simpsons character, it embodies a philosophy of relentless iteration: keep trying, unbothered by setbacks.

At its core, Ralph is a `while true` loop implemented via a **Stop hook**:

1. User runs `/ralph-loop "prompt" --max-iterations N --completion-promise "DONE"`
2. Claude works on the task, then tries to exit
3. The Stop hook intercepts the exit, increments an iteration counter, and feeds the **same prompt** back
4. Claude sees its previous work through modified files and git history
5. Loop terminates when: completion promise detected, max iterations reached, or `/cancel-ralph`

State persists in `.claude/ralph-loop.local.md` as YAML frontmatter (iteration count, max, completion promise, timestamp) with the original prompt as the body.

**Key insight**: The prompt never changes between iterations. Claude discovers what to do next by reading its own prior file changes and git history, not by remembering conversation context.

### Sources

- [Official plugin README](https://github.com/anthropics/claude-code/blob/main/plugins/ralph-wiggum/README.md)
- [DeepWiki technical analysis](https://deepwiki.com/anthropics/claude-code/4.5-ralph-wiggum-plugin)
- [Original technique by Geoffrey Huntley](https://ghuntley.com/ralph/)

---

## 2. Why People Use It

### The Context Window Problem

Claude Code auto-compacts conversation history when usage reaches ~83.5% of the 200K token window (~167K usable tokens after the ~33K reserved buffer). During compaction, earlier messages get replaced with condensed summaries. This causes meaningful data degradation:

- Specific variable names and exact error messages disappear
- Nuanced early-session decisions become generic summaries
- The agent increasingly relies on its own summaries, risking drift from the original goal

Ralph sidesteps this by giving each iteration a **fresh context** with the original prompt. File state carries forward instead of conversation history.

### Demonstrated Results

- Y Combinator hackathon: 6 repositories generated overnight
- A $50K contract completed for $297 in API costs
- A programming language ("cursed") developed over 3 months using this approach
- Effective for migrations, refactors, dependency updates, test suites

### Best Use Cases

- Well-defined tasks with clear, objective completion criteria
- Tasks with automatic verification (tests, linters, build checks)
- Greenfield projects where iteration cost is low
- Mechanical work: dependency migrations, large-scale renames, test conversions

### Poor Use Cases

- Tasks requiring human judgment or design decisions
- Ambiguous requirements without objective completion criteria
- Security-critical code (auth, encryption, payments)
- Production debugging

Source: [Tessl analysis](https://tessl.io/blog/unpacking-the-unpossible-logic-of-ralph-wiggumstyle-ai-coding/)

---

## 3. AVT Governance Compatibility Analysis

### How Our System Works (Quick Summary)

AVT uses **session-scoped governance** with five hooks:

| Hook Event | Matcher | Purpose |
|-----------|---------|---------|
| PostToolUse | `TaskCreate` | Pairs every task with governance review; creates holistic review flag |
| PreToolUse | `ExitPlanMode` | Blocks plan exit until governance review called |
| PreToolUse | `Write\|Edit\|Bash\|Task` | Blocks mutation tools during holistic review |
| TeammateIdle | (all) | Prevents idle with pending governance obligations |
| TaskCompleted | (all) | Prevents completion if governance review pending/blocked |

The **session_id** is the linchpin: flag files (`.avt/.holistic-review-pending-{session_id}`), governed task grouping, settle/debounce logic, and the holistic review pipeline all key on it.

### Conflicts with Vanilla Ralph

| Issue | Severity | Detail |
|-------|----------|--------|
| Session ID changes on restart | **HIGH** | Each Ralph iteration may get a new session_id, breaking session-scoped governance (holistic review flags, governed task grouping, settle checker logic) |
| Stop hook collision | **MEDIUM** | Ralph uses the Stop hook; AVT doesn't currently use Stop, but adding one creates ordering/priority questions with future hooks |
| Holistic review timing | **MEDIUM** | If Ralph creates tasks across iterations, they span different sessions, bypassing group review (MIN_TASKS_FOR_REVIEW=2 within same session) |
| Flag file orphaning | **LOW** | Session restart orphans `.avt/.holistic-review-pending-{old_session_id}` (mitigated by 5-min stale cleanup) |

### What IS Compatible

| Aspect | Detail |
|--------|--------|
| PreToolUse hooks | Write/Edit/Bash/Task gates check flag files, not session continuity |
| PostToolUse on TaskCreate | Fires per-task regardless of session |
| Git-based state | Ralph's file + git mechanism aligns with AVT's checkpoint pattern |
| MCP servers | KG, Quality, Governance are stateless per-request; no session affinity |
| TaskCompleted gate | Checks governance DB by task ID, not session ID |

---

## 4. Verdict: Do Not Install Vanilla Ralph; Adopt Its Core Insights

**Vanilla Ralph Wiggum conflicts with our governance model.** The session_id reset would break holistic review grouping, orphan flag files, and allow tasks to bypass collective review.

However, Ralph's core insights are valuable and can be integrated natively into our Agent Teams architecture without the plugin itself.

---

## 5. What to Adopt

### 5a. Anti-Compaction Checkpoints for Teammates

**Problem**: Long-running teammates accumulate context until auto-compaction degrades it unpredictably.

**Solution**: Teammates write critical context to disk at natural task boundaries (after sub-components complete, after review verdicts arrive, after tests pass). This is Ralph's "file state as memory" insight applied within a single governed session.

**Implementation**: Add instructions to worker/teammate agent definitions (`.claude/agents/worker.md`) directing them to write intermediate state to `.avt/session-state-{session_id}.md` at natural boundaries. No new scripts required; this is a prompt-level change.

### 5b. Ralph-Style Prompt Discipline for Task Briefs

**Problem**: Task briefs sometimes lack explicit completion criteria, self-correction instructions, and escalation conditions.

**Solution**: Adopt Ralph's prompt best practices in task brief templates:

- **Completion criteria**: Objective, verifiable conditions (not "make it good")
- **Self-correction protocol**: What to do when tests fail, when review blocks, when stuck
- **Escape hatch**: After N attempts, document what's blocking and escalate

This is pure prompt engineering; no code changes needed, just updating task brief conventions.

### 5c. Strategic Compaction at Governance Boundaries

**Problem**: Auto-compaction can fire mid-thought, losing critical context about governance verdicts or review findings.

**Solution**: After holistic review completes and the PreToolUse gate unblocks, the gate's `additionalContext` can suggest that the agent compact now (a natural boundary) rather than waiting for auto-compaction to fire at an inconvenient moment.

**Implementation**: A small addition to `scripts/hooks/holistic-review-gate.sh` that includes a compaction suggestion in the unblock message when the session has been running long.

---

## 6. What NOT to Adopt

| Pattern | Why Not |
|---------|---------|
| Stop hook loop mechanism | Breaks session-scoped governance; Agent Teams already provides better multi-task orchestration |
| Unattended overnight execution | Governance model requires review checkpoints; Ralph's "walk away" philosophy conflicts |
| Single-prompt-repeat pattern | Our tasks need evolving context (governance verdicts, review findings); repeating the same prompt loses this |
| Unlimited iterations | No max-iteration safety net is incompatible with our drift detection model |

---

## 7. Future Considerations

If Anthropic adds **session continuity across Stop hook restarts** (same session_id preserved), vanilla Ralph becomes much more compatible with our governance model. Worth monitoring Claude Code release notes for this.

If context windows expand significantly (beyond 200K), the compaction problem that Ralph solves becomes less acute, reducing the value of the pattern overall.

The Ralph Orchestrator project ([github.com/mikeyobrien/ralph-orchestrator](https://github.com/mikeyobrien/ralph-orchestrator)) adds multi-task coordination on top of Ralph. If it evolves to support session-scoped grouping, it could become a viable alternative to Agent Teams for some workflows.

---

## References

- [Anthropic Ralph Wiggum Plugin](https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum)
- [Plugin README](https://github.com/anthropics/claude-code/blob/main/plugins/ralph-wiggum/README.md)
- [DeepWiki: Plugin Technical Details](https://deepwiki.com/anthropics/claude-code/4.5-ralph-wiggum-plugin)
- [Context Buffer Management](https://claudefa.st/blog/guide/mechanics/context-buffer-management)
- [Tessl: Unpacking Ralph Wiggum-Style AI Coding](https://tessl.io/blog/unpacking-the-unpossible-logic-of-ralph-wiggumstyle-ai-coding/)
- [VentureBeat: Ralph Wiggum in AI](https://venturebeat.com/technology/how-ralph-wiggum-went-from-the-simpsons-to-the-biggest-name-in-ai-right-now)
- [The Register: Ralph Wiggum Loop Coverage](https://www.theregister.com/2026/01/27/ralph_wiggum_claude_loops/)
- [Medium: Reshaping AI Development](https://jinlow.medium.com/claude-codes-new-autonomous-execution-the-ralph-wiggum-pattern-that-s-reshaping-ai-development-3cb9c13d169b)
- [Awesome Claude: Ralph Wiggum](https://awesomeclaude.ai/ralph-wiggum)
