"""E2E test harness project generator.

Public API::

    from e2e.generator import generate_project, GeneratedProject

"""

from e2e.generator.domain_templates import DomainTemplate, get_domain_pool
from e2e.generator.project_generator import GeneratedProject, generate_project

__all__ = [
    "DomainTemplate",
    "GeneratedProject",
    "generate_project",
    "get_domain_pool",
]
