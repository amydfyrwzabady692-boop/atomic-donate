import asyncio
from collections import Counter

from channels.layers import get_channel_layer

presence = Counter()
_lock = asyncio.Lock()
_pending = {}


async def add_role(role: str) -> None:
    if role in ("alert", "gif"):
        async with _lock:
            presence[role] += 1
        await _flush_pending()


async def drop_role(role: str) -> None:
    if role in ("alert", "gif"):
        async with _lock:
            presence[role] = max(0, presence[role] - 1)


def _roles_complete(state: dict) -> bool:
    need_alert = presence["alert"] > 0
    need_gif = presence["gif"] > 0
    if not need_alert and not need_gif:
        return False
    return (state["alert"] or not need_alert) and (state["gif"] or not need_gif)


async def mark_ready(donation_id, role: str) -> None:
    if not donation_id or role not in ("alert", "gif"):
        return
    key = str(donation_id)
    async with _lock:
        state = _pending.setdefault(
            key, {"alert": False, "gif": False, "sent": False, "task": None, "id": donation_id}
        )
        state[role] = True
        if _roles_complete(state) and not state["sent"]:
            state["sent"] = True
            task = state.get("task")
            if task:
                task.cancel()
            _pending.pop(key, None)
            ready_id = donation_id
        else:
            ready_id = None
            if not state.get("task"):
                state["task"] = asyncio.create_task(_timeout_reveal(key, donation_id))
    if ready_id is not None:
        await _broadcast_reveal(ready_id)


async def _flush_pending() -> None:
    ready = []
    async with _lock:
        for key, state in list(_pending.items()):
            if state.get("sent") or not _roles_complete(state):
                continue
            state["sent"] = True
            task = state.get("task")
            if task:
                task.cancel()
            _pending.pop(key, None)
            ready.append(state.get("id") or key)
    for donation_id in ready:
        await _broadcast_reveal(donation_id)


async def _timeout_reveal(key: str, donation_id) -> None:
    try:
        await asyncio.sleep(45)
    except asyncio.CancelledError:
        return
    async with _lock:
        state = _pending.get(key)
        if not state or state.get("sent"):
            return
        state["sent"] = True
        _pending.pop(key, None)
    await _broadcast_reveal(donation_id)


async def _broadcast_reveal(donation_id) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    await layer.group_send(
        "overlays",
        {"type": "donation.event", "payload": {"type": "reveal", "id": donation_id}},
    )
