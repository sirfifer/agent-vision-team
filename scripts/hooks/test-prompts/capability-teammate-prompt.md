You are running a capability verification test for Agent Teams teammates.

Your job: Create a task for a teammate that exercises all capabilities. Use TaskCreate to create the task.

Create ONE task with subject "Capability verification probe" and this description:

---
Exercise each capability below and report results.

1. FILE WRITE: Write "teammate-write-ok" to team-cap-write-test.txt
2. FILE EDIT: Edit team-cap-write-test.txt to change "teammate-write-ok" to "teammate-edit-ok"
3. BASH: Run `echo "teammate-bash-verified" > team-cap-bash-test.txt`
4. MCP KG: Call the tool mcp__collab-kg__search_nodes with query "teammate-capability-probe". Write raw response to team-cap-mcp-kg.txt
5. MCP QUALITY: Call the tool mcp__collab-quality__validate. Write raw response to team-cap-mcp-quality.txt
6. MCP GOVERNANCE: Call the tool mcp__collab-governance__get_governance_status. Write raw response to team-cap-mcp-governance.txt
7. SUMMARY: Write team-capability-results.txt with:
   FILE_WRITE=ok or fail
   FILE_EDIT=ok or fail
   BASH=ok or fail
   MCP_KG=ok or fail
   MCP_QUALITY=ok or fail
   MCP_GOVERNANCE=ok or fail

The MCP tools use their full names starting with mcp__. Call them directly. If an MCP tool errors or is unavailable, mark it "fail".
---

After creating the task, wait for it to be completed by a teammate. Then verify team-capability-results.txt exists.

Important:
- Use TaskCreate to create the task (this will trigger governance hooks).
- The teammate will pick up and execute the task.
- Wait for the teammate to complete before finishing.
