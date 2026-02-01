# Solution Patterns

This file contains promoted patterns that have been used successfully 3+ times. Curated by the KG Librarian subagent.

## Format

Each pattern should include:
- **Pattern Name**: Clear, descriptive name
- **When to Use**: Scenarios where this pattern applies
- **Steps**: Concrete implementation steps
- **Example**: Reference to a working implementation
- **KG Reference**: Link to the pattern entity in the KG

---

## Example Pattern

**Pattern Name**: Protocol-Based Service Registration

**When to Use**: When adding a new service to the application that needs dependency injection

**Steps**:
1. Define a protocol for your service (e.g., `protocol AuthServiceProtocol { ... }`)
2. Create the concrete implementation conforming to the protocol
3. Register the service in `ServiceRegistry`:
   ```swift
   registry.register(AuthServiceProtocol.self) {
       AuthService(tokenValidator: $0.resolve(TokenValidatorProtocol.self))
   }
   ```
4. Inject the service via protocol in consuming components:
   ```swift
   init(authService: AuthServiceProtocol) { ... }
   ```

**Benefits**:
- Easy to mock for testing
- Clear dependency contracts
- Compile-time type safety
- Easy to swap implementations

**Example**: See `AuthService`, `TokenValidator`, `NetworkService` in the codebase

**KG Reference**: Entity `protocol_based_di_pattern` (architecture tier)

**Times Used**: 8 services now follow this pattern

---

*This file is automatically curated by the KG Librarian. Patterns are promoted after 3+ successful uses.*
