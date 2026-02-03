# Troubleshooting Log

This file contains problems encountered, approaches tried, and what ultimately worked. Curated by the KG Librarian subagent.

## Format

Each entry should include:
- **Date**: When the issue was encountered
- **Problem**: Description of the issue
- **Component**: Which component(s) were affected
- **Tried**: Approaches that didn't work
- **Solution**: What ultimately resolved the issue
- **KG Reference**: Link to observations in the KG

---

## Example Entry

**Date**: 2024-01-20

**Problem**: Tests failing intermittently in AuthService

**Component**: AuthService, TokenValidator

**Tried**:
- Increasing test timeouts (didn't help)
- Mocking time-based functions (still flaky)
- Adding delays between test cases (unreliable)

**Solution**: The issue was shared mutable state in the TokenValidator singleton. Refactored TokenValidator to be a protocol with instance-based implementations. Each test now gets a fresh instance.

**Root Cause**: Singleton pattern violated our "no singletons in production code" vision standard. The test failures were exposing the architectural issue.

**KG Reference**: Observation added to `TokenValidator` entity: "Refactored from singleton to protocol-based DI on 2024-01-20 to fix test flakiness"

---

*This file is automatically curated by the KG Librarian. Manual edits should be synced back to the KG.*
