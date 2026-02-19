Do these 7 steps in order. Do each one, report the result, then move to the next.

Step 1: Write the text "direct-write-ok" to cap-write-test.txt
Step 2: Edit cap-write-test.txt changing "direct-write-ok" to "direct-edit-ok"
Step 3: Run: echo "bash-execution-verified" > cap-bash-test.txt
Step 4: Call mcp__collab-kg__search_nodes with query "capability-verification-probe" and write the response to cap-mcp-kg.txt
Step 5: Call mcp__collab-quality__validate and write the response to cap-mcp-quality.txt
Step 6: Call mcp__collab-governance__get_governance_status and write the response to cap-mcp-governance.txt
Step 7: Write capability-results.txt with exactly these lines (use ok or fail for each):
FILE_WRITE=ok
FILE_EDIT=ok
BASH=ok
MCP_KG=ok
MCP_QUALITY=ok
MCP_GOVERNANCE=ok
