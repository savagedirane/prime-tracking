"""
Tiny in-process TTL cache for the public tracking endpoint.

Tracking data only changes when an admin adds a milestone (or edits/deletes
the shipment), so caching reads for a short window removes the vast majority
of database hits on the hottest endpoint without any staleness that matters.

Scope: per-process memory ("memory://"). This is the right call for the
current single-instance deployment; when you scale to multiple workers or
instances, set TRACK_CACHE_TTL as-is (each worker caches independently —
still correct, just less efficient) or swap this module for Redis and have
the write paths PUBLISH invalidations. The interface below was kept
deliberately small so that swap is ~20 lines.
"""
import os
import threading

from cachetools import TTLCache

_ttl = float(os.environ.get("TRACK_CACHE_TTL", "60"))
_maxsize = int(os.environ.get("TRACK_CACHE_MAXSIZE", "4096"))

_cache = TTLCache(maxsize=_maxsize, ttl=_ttl)
_lock = threading.Lock()


def get_cached(tracking_number: str):
    """Return the cached value for a tracking number, or None."""
    with _lock:
        return _cache.get(tracking_number)


def set_cached(tracking_number: str, value) -> None:
    with _lock:
        _cache[tracking_number] = value


def invalidate(tracking_number: str) -> None:
    """Drop the cache entry after any write that changes a shipment's
    public data (milestone added, shipment edited, deleted, restored)."""
    with _lock:
        _cache.pop(tracking_number, None)
