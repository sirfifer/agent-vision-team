# Dogfooding Validation Checklist

**Date**: ___________
**Tester**: ___________
**Extension Version**: 0.1.0

## Instructions

Complete this checklist while testing the Collab Intelligence extension in VS Code. Mark each item with [x] when verified.

---

## Pre-Test Setup

- [ ] MCP servers started (`./scripts/start-mcp-servers.sh`)
- [ ] Both servers healthy (KG:3101, Quality:3102)
- [ ] Extension built (`./scripts/build-extension.sh`)
- [ ] Test data populated (`./scripts/populate-test-data.sh`)

---

## Extension Activation

- [ ] Opened `extension/` folder in VS Code
- [ ] Pressed F5 to launch Extension Development Host
- [ ] New window opened titled "[Extension Development Host]"
- [ ] Opened `agent-vision-team` folder in Extension Host
- [ ] Activity Bar shows "Collab Intelligence" icon
- [ ] Status bar shows "Collab: Active" (or "Connecting...")
- [ ] No error notifications displayed

**Notes**:
_____________________________________________________________________________

---

## Memory Browser

- [ ] Sidebar shows "Memory Browser" section
- [ ] Three tier groups visible:
  - [ ] Vision Standards (immutable) (1)
  - [ ] Architecture (human-approved) (1)
  - [ ] Quality (automated) (1)
- [ ] Can expand Vision tier
- [ ] Entity "test_vision_standard" appears
- [ ] Tooltip shows observations when hovering
- [ ] Refresh button works (click and verify re-fetch)
- [ ] Search button opens input box
- [ ] Search for "test" returns results

**Notes**:
_____________________________________________________________________________

---

## Findings Panel

- [ ] Sidebar shows "Findings" section
- [ ] Findings displayed (or "No findings" if clean)
- [ ] Refresh button works
- [ ] Command Palette → "Collab Intelligence: Validate All Quality Gates"
- [ ] Notification shows gate summary
- [ ] Findings Panel updates after validation

**Notes**:
_____________________________________________________________________________

---

## Tasks Panel

- [ ] Sidebar shows "Tasks" section
- [ ] Task brief "example-001-add-feature.md" appears
- [ ] Create new task brief: `.claude/collab/task-briefs/test-task.md`
- [ ] Tasks Panel auto-refreshes (new task appears)
- [ ] Delete test task brief
- [ ] Tasks Panel auto-refreshes (task disappears)

**Notes**:
_____________________________________________________________________________

---

## Commands (All 7)

Test each command via Command Palette (Cmd+Shift+P / Ctrl+Shift+P):

- [ ] **Collab Intelligence: Refresh Memory Browser**
  Result: Memory Browser re-fetches entities

- [ ] **Collab Intelligence: Refresh Findings Panel**
  Result: Findings Panel re-fetches findings

- [ ] **Collab Intelligence: Refresh Tasks Panel**
  Result: Tasks Panel rescans directory

- [ ] **Collab Intelligence: Search Memory**
  Result: Input box appears, search works

- [ ] **Collab Intelligence: View Dashboard**
  Result: Dashboard webview opens

- [ ] **Collab Intelligence: Validate All Quality Gates**
  Result: Notification shows gate results

- [ ] **Collab Intelligence: Connect to MCP Servers**
  Result: Status bar updates, connection logs visible

**Notes**:
_____________________________________________________________________________

---

## Status Bar

- [ ] Left side shows: `$(shield) Collab: Active`
- [ ] Color is green (indicates healthy)
- [ ] Center shows: `N findings · Phase: active`
- [ ] Clicking status bar item triggers action (if implemented)

**Notes**:
_____________________________________________________________________________

---

## Error Handling

- [ ] Stop MCP servers (`./scripts/stop-mcp-servers.sh`)
- [ ] Reload extension window (Cmd+R / Ctrl+R)
- [ ] Status bar shows "Collab: Inactive" or "Collab: Error"
- [ ] Error notification: "MCP servers not available" or similar
- [ ] Extension does not crash
- [ ] TreeViews show empty or error state gracefully
- [ ] Restart servers (`./scripts/start-mcp-servers.sh`)
- [ ] Command → "Connect to MCP Servers"
- [ ] Status bar returns to "Active"
- [ ] TreeViews populate again

**Notes**:
_____________________________________________________________________________

---

## Overall Assessment

- [ ] **All critical tests passed**
- [ ] **Zero crashes during testing**
- [ ] **Extension is usable and functional**
- [ ] **UI is responsive and intuitive**

**Overall Result**: ⬜ PASS  /  ⬜ FAIL

**Critical Issues Found**:
_____________________________________________________________________________
_____________________________________________________________________________

**Non-Critical Issues**:
_____________________________________________________________________________
_____________________________________________________________________________

**Recommendations**:
_____________________________________________________________________________
_____________________________________________________________________________

---

## Sign-Off

**Tester Signature**: ___________
**Date Completed**: ___________
**Time Spent**: ___________ minutes
