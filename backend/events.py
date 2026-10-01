"""
In-process pub/sub powering the Server-Sent Events (SSE) live-update stream.

Every SSE client watching a tracking number holds a thread-safe Queue here.
Admin writes (milestone added, shipment edited/deleted/restored, coordinates
geocoded) publish a fresh JSON snapshot, and every watcher receives it
instantly — no polling.

Scope: per-process ("memory://"), same trade-off as cache.py. With a single
instance (current deployment) every watcher is notified. If you scale to
multiple workers, swap publish/subscribe for Redis pub/sub (~30 lines, same
interface) so writes on one worker reach watchers on another.
"""
import queue
import threading
from collections import defaultdict

_subs: dict[str, set] = defaultdict(set)
_lock = threading.Lock()


def subscribe(tracking_number: str):
    """Register a watcher; returns its queue to iterate for events."""
    q = queue.Queue()
    with _lock:
        _subs[tracking_number].add(q)
    return q


def unsubscribe(tracking_number: str, q) -> None:
    with _lock:
        watchers = _subs.get(tracking_number)
        if watchers:
            watchers.discard(q)
            if not watchers:
                _subs.pop(tracking_number, None)


def publish(tracking_number: str, snapshot_json: str) -> int:
    """Push a snapshot to all watchers of this tracking number.
    Returns how many watchers received it (0 is normal — nobody watching)."""
    with _lock:
        watchers = list(_subs.get(tracking_number, ()))
    for q in watchers:
        q.put(snapshot_json)  # unbounded queue — never blocks the writer
    return len(watchers)


def watcher_count(tracking_number: str) -> int:
    with _lock:
        return len(_subs.get(tracking_number, ()))
