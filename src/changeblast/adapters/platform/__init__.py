"""Platform intelligence adapters module."""

from changeblast.adapters.platform.android import AndroidPlatformAdapter
from changeblast.adapters.platform.ios import IOSPlatformAdapter

__all__ = ["AndroidPlatformAdapter", "IOSPlatformAdapter"]
