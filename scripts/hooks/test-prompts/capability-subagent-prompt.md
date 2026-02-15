You are running a capability verification test for Task tool subagents.

Your job: Spawn a SINGLE subagent using the Task tool that exercises all capabilities listed below. Do NOT do the work yourself. The subagent must do it.

Spawn the subagent with this prompt (pass it exactly):

---
Exercise each capability below and report results.

1. FILE WRITE: Write "subagent-write-ok" to sub-cap-write-test.txt
2. FILE EDIT: Edit sub-cap-write-test.txt to change "subagent-write-ok" to "subagent-edit-ok"
3. BASH: Run `echo "subagent-bash-verified" > sub-cap-bash-test.txt`
4. MCP KG: Call the tool mcp__collab-kg__search_nodes with query "subagent-capability-probe". Write raw response to sub-cap-mcp-kg.txt
5. MCP QUALITY: Call the tool mcp__collab-quality__validate. Write raw response to sub-cap-mcp-quality.txt
6. MCP GOVERNANCE: Call the tool mcp__collab-governance__get_governance_status. Write raw response to sub-cap-mcp-governance.txt
7. SUMMARY: Write sub-capability-results.txt with:
   FILE_WRITE=ok or fail
   FILE_EDIT=ok or fail
   BASH=ok or fail
   MCP_KG=ok or fail
   MCP_QUALITY=ok or fail
   MCP_GOVERNANCE=ok or fail

The MCP tools use their full names starting with mcp__. Call them directly. If an MCP tool errors or is unavailable, mark it "fail".
---

After the subagent completes, verify that sub-capability-results.txt exists and report its contents.

Important:
- Use the Task tool to spawn the subagent, NOT TaskCreate.
- Do NOT do the capability work yourself. The subagent must do ALL of it.
- Wait for the subagent to complete before finishing.
