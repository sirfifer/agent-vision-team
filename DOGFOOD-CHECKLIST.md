# Dogfooding Validation Checklist

**Date**: ___________
**Tester**: ___________
**Extension Version**: 0.1.0

## Instructions

Complete this checklist while testing the Collab Intelligence extension in VS Code. Mark each item with [x] when verified.

---

## Pre-Test Setup

- [ ] MCP servers started (`./scripts/start-mcp-servers.sh`)
- [ ] All three servers healthy (KG:3101, Quality:3102, Governance:3103)
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
- [ ] Create new task brief: `.avt/task-briefs/test-task.md`
- [ ] Tasks Panel auto-refreshes (new task appears)
- [ ] Delete test task brief
- [ ] Tasks Panel auto-refreshes (task disappears)

**Notes**:
_____________________________________________________________________________

---

## Commands (All 12)

Test each command via Command Palette (Cmd+Shift+P / Ctrl+Shift+P):

- [ ] **Collab Intelligence: View Dashboard** (`collab.viewDashboard`)
  Result: Dashboard webview opens

- [ ] **Collab Intelligence: Refresh Memory Browser** (`collab.refreshMemory`)
  Result: Memory Browser re-fetches entities

- [ ] **Collab Intelligence: Search Memory** (`collab.searchMemory`)
  Result: Input box appears, search works

- [ ] **Collab Intelligence: Refresh Findings Panel** (`collab.refreshFindings`)
  Result: Findings Panel re-fetches findings

- [ ] **Collab Intelligence: Refresh Tasks Panel** (`collab.refreshTasks`)
  Result: Tasks Panel rescans directory

- [ ] **Collab Intelligence: Validate All Quality Gates** (`collab.validateAll`)
  Result: Notification shows gate results

- [ ] **Collab Intelligence: Connect to MCP Servers** (`collab.connectMcpServers`)
  Result: Status bar updates, connection logs visible

- [ ] **Collab Intelligence: Open Setup Wizard** (`collab.openSetupWizard`)
  Result: Dashboard opens with Setup Wizard overlay visible

- [ ] **Collab Intelligence: Open Workflow Tutorial** (`collab.openWorkflowTutorial`)
  Result: Dashboard opens with Workflow Tutorial overlay visible

- [ ] **Collab Intelligence: Run Research Prompt** (`collab.runResearch`)
  Result: Research prompt selection or creation flow starts

- [ ] **Collab Intelligence: Getting Started** (`collab.openWalkthrough`)
  Result: VS Code native walkthrough opens with 6 steps

- [ ] **Collab Intelligence: Create Task Brief** (`collab.createTaskBrief`)
  Result: Task brief creation flow starts

**Notes**:
_____________________________________________________________________________

---

## Actions View

- [ ] Sidebar shows "Actions" section
- [ ] Welcome content displays quick-action buttons:
  - [ ] "Open Dashboard" button
  - [ ] "Connect to Servers" button
  - [ ] "Setup Wizard" button
  - [ ] "Workflow Tutorial" button
- [ ] Each button triggers its corresponding command

**Notes**:
_____________________________________________________________________________

---

## Setup Wizard (9 Steps)

- [ ] Command Palette → "Collab Intelligence: Open Setup Wizard"
- [ ] Wizard overlay appears in Dashboard
- [ ] Step 1: Welcome — displays intro text
- [ ] Step 2: Vision Docs — vision document configuration
- [ ] Step 3: Architecture Docs — architecture document configuration
- [ ] Step 4: Quality Config — quality gate settings
- [ ] Step 5: Rules — project rules with enforce/prefer levels
- [ ] Step 6: Permissions — agent permission configuration
- [ ] Step 7: Settings — general project settings
- [ ] Step 8: KG Ingestion — knowledge graph document ingestion
- [ ] Step 9: Completion — summary and finish
- [ ] Can navigate forward/backward between steps
- [ ] Step indicators show progress
- [ ] Wizard can be closed/dismissed

**Notes**:
_____________________________________________________________________________

---

## Workflow Tutorial (10 Steps)

- [ ] Command Palette → "Collab Intelligence: Open Workflow Tutorial"
- [ ] Tutorial overlay appears in Dashboard
- [ ] Step 1: Welcome
- [ ] Step 2: Big Picture
- [ ] Step 3: Setup
- [ ] Step 4: Starting Work
- [ ] Step 5: Behind the Scenes
- [ ] Step 6: Monitoring
- [ ] Step 7: Knowledge Graph
- [ ] Step 8: Quality Gates
- [ ] Step 9: Tips
- [ ] Step 10: Ready
- [ ] Can navigate forward/backward between steps
- [ ] Tutorial can be closed/dismissed

**Notes**:
_____________________________________________________________________________

---

## Governance Panel

- [ ] Dashboard shows Governance Panel (left side, 2/5 width)
- [ ] Governance stats counters displayed
- [ ] Vision standards list shown
- [ ] Architectural elements list shown
- [ ] Governed tasks with review status badges visible
- [ ] Blocker indicators display correctly

**Notes**:
_____________________________________________________________________________

---

## Research Prompts Panel

- [ ] Research Prompts Panel accessible from Dashboard (Session Bar button)
- [ ] Can create a new research prompt
- [ ] Can edit an existing research prompt
- [ ] Can delete a research prompt
- [ ] Schedule configuration works (periodic/exploratory modes)
- [ ] Can run a research prompt

**Notes**:
_____________________________________________________________________________

---

## Document Editor

- [ ] Can draft content for vision/architecture documents
- [ ] Format button triggers Claude CLI-based auto-formatting
- [ ] Formatted result appears for review
- [ ] Can save formatted document
- [ ] Error states handled gracefully

**Notes**:
_____________________________________________________________________________

---

## Status Bar

Two status bar items (both click through to the Dashboard):

- [ ] Health indicator (left, priority 100): `$(shield) Collab: Active`
  - [ ] Shows `$(warning) Collab: Warning` with warning background when degraded
  - [ ] Shows `$(error) Collab: Error` with error background on failure
  - [ ] Shows `$(circle-outline) Collab: Inactive` when disconnected
- [ ] Summary indicator (left, priority 99): `N workers · N findings · Phase: <phase>`
- [ ] Clicking either status bar item opens the Dashboard

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
