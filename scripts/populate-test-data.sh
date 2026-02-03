#!/bin/bash
#
# Populate Test Data for Dogfooding
# Adds sample entities to the Knowledge Graph for testing the extension
#

set -e

echo "=== Populating Test Data ==="
echo ""

# Create vision-tier entity
echo "Creating vision-tier test entity..."
curl -s -X POST http://localhost:3101/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "create_entities",
      "arguments": {
        "entities": [{
          "name": "test_vision_standard",
          "entityType": "vision_standard",
          "observations": [
            "protection_tier: vision",
            "All tests must pass before commit",
            "Code coverage must exceed 80%",
            "No silent dismissals of findings"
          ]
        }]
      }
    }
  }' | jq -r '.result.created // "Error"' && echo "  ✓ Vision entity created" || echo "  ✗ Failed to create vision entity"

# Create architecture-tier entity
echo "Creating architecture-tier test entity..."
curl -s -X POST http://localhost:3101/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "create_entities",
      "arguments": {
        "entities": [{
          "name": "test_arch_component",
          "entityType": "pattern",
          "observations": [
            "protection_tier: architecture",
            "Uses protocol-based dependency injection",
            "Follows MVC pattern",
            "Services registered in ServiceRegistry"
          ]
        }]
      }
    }
  }' | jq -r '.result.created // "Error"' && echo "  ✓ Architecture entity created" || echo "  ✗ Failed to create architecture entity"

# Create quality-tier entity
echo "Creating quality-tier test entity..."
curl -s -X POST http://localhost:3101/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "create_entities",
      "arguments": {
        "entities": [{
          "name": "test_quality_note",
          "entityType": "component",
          "observations": [
            "protection_tier: quality",
            "Extension activation logic needs optimization",
            "Consider lazy-loading providers"
          ]
        }]
      }
    }
  }' | jq -r '.result.created // "Error"' && echo "  ✓ Quality entity created" || echo "  ✗ Failed to create quality entity"

echo ""
echo "=== Test Data Populated Successfully ==="
echo ""
echo "Entities created:"
echo "  - test_vision_standard (vision tier)"
echo "  - test_arch_component (architecture tier)"
echo "  - test_quality_note (quality tier)"
echo ""
echo "These should now appear in the Memory Browser when you refresh."
