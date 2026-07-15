"""Routers package."""

from app.routers import audit, errors, health, jobs, oauth, tenants, users

__all__ = ["health", "tenants", "users", "oauth", "jobs", "errors", "audit"]
