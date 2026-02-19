"""Domain vocabulary pool for E2E test harness project generation.

Each domain provides a realistic, self-contained project context with
domain-specific components, vision standards, and architecture patterns.
Vision templates always include the five canonical archetypes:
  1. Protocol-based DI requirement
  2. No singletons in production
  3. Every public API has integration tests
  4. Security/authorization standard
  5. Error handling standard (Result types, not exceptions)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

TemplateStr: TypeAlias = str
"""A template string that may contain ``{component}``, ``{domain}``, or
``{prefix}`` placeholders filled at generation time."""


@dataclass(frozen=True, slots=True)
class DomainTemplate:
    """Immutable definition of a project domain used to generate test projects."""

    name: str
    """Human-readable domain name, e.g. 'Pet Adoption Platform'."""

    prefix: str
    """Snake-case prefix for file/entity naming, e.g. 'pet_adoption'."""

    components: tuple[str, ...]
    """Three domain-specific service/component names."""

    vision_templates: tuple[TemplateStr, ...]
    """Five vision-standard templates (one per archetype).
    Placeholders: ``{domain}``, ``{prefix}``, ``{component}``."""

    architecture_templates: tuple[TemplateStr, ...]
    """Two or three architecture-pattern templates.
    Placeholders: ``{domain}``, ``{prefix}``, ``{component}``."""


# ---------------------------------------------------------------------------
# Domain pool  (8 domains)
# ---------------------------------------------------------------------------

DOMAIN_POOL: tuple[DomainTemplate, ...] = (
    # ------------------------------------------------------------------
    # 1. Pet Adoption Platform
    # ------------------------------------------------------------------
    DomainTemplate(
        name="Pet Adoption Platform",
        prefix="pet_adoption",
        components=("AnimalProfileService", "AdoptionMatchEngine", "ShelterGateway"),
        vision_templates=(
            "All {domain} services MUST use protocol-based dependency injection; "
            "no concrete initializers outside composition roots",
            "No singletons in production {domain} code; test doubles for {component} are acceptable",
            "Every public API endpoint in {domain} MUST have at least one "
            "integration test exercising the happy path and one error path",
            "All adoption records MUST be authorized through the shelter's "
            "permission scope before any data leaves {component}",
            "{domain} error handling MUST use Result types; "
            "thrown exceptions are forbidden outside infrastructure adapters",
        ),
        architecture_templates=(
            "{component} uses the ServiceRegistry pattern to resolve all {domain} dependencies at startup",
            "Inter-service communication in {domain} uses async event "
            "channels; no direct service-to-service calls in the hot path",
        ),
    ),
    # ------------------------------------------------------------------
    # 2. Restaurant Reservation System
    # ------------------------------------------------------------------
    DomainTemplate(
        name="Restaurant Reservation System",
        prefix="restaurant_reservation",
        components=("BookingService", "TableLayoutEngine", "WaitlistManager"),
        vision_templates=(
            "All {domain} services MUST accept dependencies via protocol "
            "conformance; constructor injection is the only allowed form",
            "No singleton instances in production {domain} modules; {component} test mocks are the sole exception",
            "Every public API in the {domain} MUST have integration tests "
            "covering reservation creation, modification, and cancellation",
            "Guest personal data MUST be filtered through the authorization "
            "layer before {component} returns any response",
            "All {domain} operations MUST return Result<T, DomainError>; "
            "exceptions are restricted to infrastructure boundaries",
        ),
        architecture_templates=(
            "{component} registers all {domain} dependencies in a centralized ServiceRegistry resolved once at boot",
            "{domain} components communicate via a command bus; synchronous cross-service calls are prohibited",
            "Table availability in {domain} is computed through a read-model projection updated by domain events",
        ),
    ),
    # ------------------------------------------------------------------
    # 3. Fitness Tracking App
    # ------------------------------------------------------------------
    DomainTemplate(
        name="Fitness Tracking App",
        prefix="fitness_tracking",
        components=("WorkoutEngine", "NutritionTracker", "ProgressAnalytics"),
        vision_templates=(
            "All {domain} components MUST depend on protocols, not concrete "
            "types; {component} follows protocol-based DI exclusively",
            "Singletons are banned in production {domain} code; "
            "in-memory fakes for {component} are permitted in tests only",
            "Every public endpoint exposed by {domain} MUST be covered by "
            "integration tests validating input, output, and auth",
            "Health data access in {domain} MUST pass through the authorization middleware before reaching {component}",
            "{domain} MUST use Result types for all fallible operations; "
            "throwing exceptions is forbidden outside IO adapters",
        ),
        architecture_templates=(
            "The {domain} ServiceRegistry owns the lifecycle of all "
            "services including {component}; no manual instantiation",
            "Real-time workout data in {domain} flows through a pub/sub "
            "channel; {component} subscribes without direct coupling",
        ),
    ),
    # ------------------------------------------------------------------
    # 4. Online Learning Platform
    # ------------------------------------------------------------------
    DomainTemplate(
        name="Online Learning Platform",
        prefix="online_learning",
        components=("CourseManager", "AssessmentEngine", "EnrollmentGateway"),
        vision_templates=(
            "All {domain} services MUST use protocol-based dependency "
            "injection; {component} MUST NOT instantiate its own dependencies",
            "No singletons in production {domain} code; stub implementations of {component} are allowed in test suites",
            "Every public API in {domain} MUST have integration tests "
            "covering enrollment, assessment submission, and grading paths",
            "Student records in {domain} MUST be gated by role-based authorization before {component} exposes any data",
            "{domain} error handling MUST use typed Result values; "
            "exceptions are only permitted at the HTTP adapter boundary",
        ),
        architecture_templates=(
            "{component} is resolved through the {domain} ServiceRegistry; "
            "manual construction outside tests is a build error",
            "Cross-module communication in {domain} uses domain events dispatched through an in-process event bus",
            "{domain} read models for dashboards are maintained as "
            "projections from the event stream, never queried directly",
        ),
    ),
    # ------------------------------------------------------------------
    # 5. Smart Home Automation
    # ------------------------------------------------------------------
    DomainTemplate(
        name="Smart Home Automation",
        prefix="smart_home",
        components=("DeviceOrchestrator", "RuleEngine", "SensorGateway"),
        vision_templates=(
            "All {domain} services MUST receive dependencies through "
            "protocol injection; {component} may not resolve its own deps",
            "Singletons are prohibited in production {domain} modules; "
            "test harness doubles for {component} are the only exception",
            "Every public API in {domain} MUST have integration tests "
            "including device command, rule evaluation, and sensor read paths",
            "All device commands in {domain} MUST be authorized by the "
            "home-owner permission model before reaching {component}",
            "{domain} MUST propagate errors as Result types; "
            "thrown exceptions are confined to hardware driver adapters",
        ),
        architecture_templates=(
            "The {domain} ServiceRegistry manages the full lifecycle of {component} and all peer services at startup",
            "Device state changes in {domain} are broadcast via an "
            "observable event stream; {component} reacts without polling",
        ),
    ),
    # ------------------------------------------------------------------
    # 6. Inventory Management System
    # ------------------------------------------------------------------
    DomainTemplate(
        name="Inventory Management System",
        prefix="inventory_mgmt",
        components=("StockLedger", "ProcurementService", "WarehouseRouter"),
        vision_templates=(
            "All {domain} services MUST use protocol-based DI; "
            "{component} receives all collaborators through its initializer",
            "No singleton instances in production {domain} code; "
            "in-memory {component} fakes are reserved for test isolation",
            "Every public API in {domain} MUST have integration tests "
            "covering stock adjustments, procurement, and routing decisions",
            "Inventory mutations in {domain} MUST pass through the "
            "authorization layer; {component} never bypasses access control",
            "{domain} error handling uses Result<T, InventoryError>; "
            "exceptions are forbidden outside transport-layer adapters",
        ),
        architecture_templates=(
            "{component} and all {domain} services are registered in a "
            "centralized ServiceRegistry resolved at application boot",
            "Warehouse-to-warehouse transfers in {domain} use an async "
            "message queue; {component} consumes transfer events",
        ),
    ),
    # ------------------------------------------------------------------
    # 7. Event Ticketing Platform
    # ------------------------------------------------------------------
    DomainTemplate(
        name="Event Ticketing Platform",
        prefix="event_ticketing",
        components=("TicketIssuanceService", "VenueCapacityEngine", "PaymentGateway"),
        vision_templates=(
            "All {domain} services MUST depend on protocols, not "
            "implementations; {component} uses constructor injection only",
            "Singletons are banned in production {domain} code; mock {component} instances are allowed in tests",
            "Every public API in {domain} MUST have integration tests "
            "for ticket purchase, refund, and capacity enforcement",
            "Payment and PII data in {domain} MUST be authorized via "
            "scoped tokens before {component} processes any request",
            "{domain} MUST return Result types from all domain operations; "
            "exceptions are limited to third-party payment SDK boundaries",
        ),
        architecture_templates=(
            "The {domain} ServiceRegistry holds all service instances "
            "including {component}; lazy resolution is not permitted",
            "Ticket availability in {domain} is communicated through a "
            "CQRS read model; {component} publishes domain events on write",
        ),
    ),
    # ------------------------------------------------------------------
    # 8. Fleet Management System
    # ------------------------------------------------------------------
    DomainTemplate(
        name="Fleet Management System",
        prefix="fleet_mgmt",
        components=("VehicleTracker", "RouteOptimizer", "MaintenanceScheduler"),
        vision_templates=(
            "All {domain} services MUST accept dependencies via protocol "
            "types; {component} MUST NOT create its own collaborators",
            "No singletons in production {domain} code; test-only doubles of {component} are acceptable",
            "Every public API in {domain} MUST have integration tests "
            "covering vehicle tracking, route planning, and maintenance ops",
            "GPS and driver data in {domain} MUST be authorized through "
            "fleet-level permissions before {component} returns results",
            "{domain} MUST use Result types for all fallible operations; "
            "exceptions are only allowed in external telemetry adapters",
        ),
        architecture_templates=(
            "{component} is managed by the {domain} ServiceRegistry; "
            "all services are fully resolved before the first request",
            "Real-time telemetry in {domain} flows through an event "
            "stream; {component} processes events without direct coupling",
            "Route computations in {domain} are offloaded to a background worker pool coordinated by {component}",
        ),
    ),
)


def get_domain_pool() -> tuple[DomainTemplate, ...]:
    """Return the full domain pool.

    This function exists so that callers import a stable API rather than
    reaching for the module-level constant directly.
    """
    return DOMAIN_POOL
