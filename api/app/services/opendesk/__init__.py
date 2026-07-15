"""openDesk service package.

Sub-modules contain integrations with:
- OX App Suite (mail, calendar, contacts) via SOAP (`oxadmin`) + JSON API
- Nextcloud (OneDrive target) via OCS Admin + WebDAV
"""

from app.services.opendesk.ox import OXAdmin, OXConnection
from app.services.opendesk.nextcloud import NextcloudAdmin, NextcloudConnection

__all__ = [
    "OXAdmin",
    "OXConnection",
    "NextcloudAdmin",
    "NextcloudConnection",
]
