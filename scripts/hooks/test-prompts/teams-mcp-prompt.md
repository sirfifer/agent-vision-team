You are testing Agent Teams MCP access. You have access to MCP servers via user-scope configuration.

Your task:

1. Call search_nodes("test-connectivity") on the collab-kg MCP server.
2. Call get_governance_status() on the collab-governance MCP server.
3. Call validate() on the collab-quality MCP server.

For each call, record:
- Whether it succeeded or failed
- The type of response received (real data vs error)
- A brief summary of what was returned

Write all results to mcp-test-results.txt in the following format:

```
KG: [SUCCESS/FAIL] - [brief description of response]
GOVERNANCE: [SUCCESS/FAIL] - [brief description of response]
QUALITY: [SUCCESS/FAIL] - [brief description of response]
```

This is a connectivity test. The specific data returned does not matter; what matters is that each MCP server responds with real data (not errors or hallucinated results).
