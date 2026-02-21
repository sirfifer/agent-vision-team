"""Audit subsystem for the Collaborative Intelligence System.

Hook-piggybacked, fan-belt architecture: no daemon, no long-running process.
The system's own hook activity drives audit event emission and processing.
"""
