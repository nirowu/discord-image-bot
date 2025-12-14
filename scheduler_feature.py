import asyncio
import time
from typing import Awaitable, Callable, Dict, Optional

import discord

from scheduler_storage import claim_due_messages, mark_failed, mark_sent, reschedule_repeat


ScheduledHandler = Callable[[discord.abc.Messageable, object, str], Awaitable[None]]

_REPEAT_SECONDS = {
    "minute": 60,
    "hour": 60 * 60,
    "day": 60 * 60 * 24,
}


async def dispatch_due_messages(
    bot: discord.Client,
    conn,
    *,
    now: Optional[int] = None,
    batch_size: int = 10,
    handlers: Optional[Dict[str, ScheduledHandler]] = None,
) -> int:
    if now is None:
        now = int(time.time())

    claimed = claim_due_messages(conn, now=now, limit=batch_size)
    if not claimed:
        return 0

    sent_count = 0
    for row in claimed:
        schedule_id = int(row["id"])
        channel_id = int(row["channel_id"])
        content = row["content"]
        kind = row.get("kind") or "text"
        repeat_interval = row.get("repeat_interval")

        channel = bot.get_channel(channel_id)
        if channel is None:
            mark_failed(conn, schedule_id, error=f"Channel {channel_id} not found")
            continue

        try:
            if kind == "text":
                await channel.send(content)
            else:
                if handlers is None or kind not in handlers:
                    raise RuntimeError(f"Unsupported schedule kind: {kind}")
                await handlers[kind](channel, conn, content)

            if repeat_interval:
                seconds = _REPEAT_SECONDS.get(repeat_interval)
                if seconds is None:
                    raise RuntimeError(f"Unsupported repeat interval: {repeat_interval}")

                next_run_at = int(row["run_at"]) + seconds
                while next_run_at <= now:
                    next_run_at += seconds

                reschedule_repeat(conn, schedule_id, sent_at=now, next_run_at=next_run_at)
                await channel.send(f"Sent at <t:{now}:F>. Next at <t:{next_run_at}:F>.")
            else:
                mark_sent(conn, schedule_id, sent_at=now)
            sent_count += 1
        except Exception as e:
            mark_failed(conn, schedule_id, error=str(e))

    return sent_count


def start_scheduler_loop(
    bot: discord.Client,
    conn,
    *,
    poll_interval_seconds: float = 5.0,
    handlers: Optional[Dict[str, ScheduledHandler]] = None,
) -> asyncio.Task:
    async def _loop():
        while not bot.is_closed():
            await dispatch_due_messages(bot, conn, handlers=handlers)
            await asyncio.sleep(poll_interval_seconds)

    return asyncio.create_task(_loop())
