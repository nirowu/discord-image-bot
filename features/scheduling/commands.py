import time
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands

from .dispatcher import start_scheduler_loop
from .storage import (
    cancel_scheduled_message,
    create_scheduled_message,
    init_scheduler_db,
    list_scheduled_messages,
)
from .time_utils import (
    ScheduleTimeError,
    compute_next_occurrence_from_hour_minute,
    compute_run_at_from_components,
)


SCHEDULE_MAX_MINUTES = 60 * 24 * 7  # 7 days


def setup_scheduling(bot: discord.Client) -> None:
    """
    Register scheduling slash commands and start the background scheduler loop.
    Expects `bot` to have `.tree` (CommandTree) and `.conn` (sqlite3 connection).
    """
    tree = bot.tree
    conn = bot.conn

    init_scheduler_db(conn)

    async def _send_image_search(channel, conn_arg, query: str):
        from search import search_best_match

        matches = search_best_match(conn_arg, query, limit=1)
        if not matches:
            await channel.send("No matching image found.")
            return
        row = matches[0]
        await channel.send(file=discord.File(row["file_path"]))

    start_scheduler_loop(
        bot,
        conn,
        handlers={"image_search": _send_image_search},
    )

    mode_choices = [
        app_commands.Choice(name="Text", value="text"),
        app_commands.Choice(name="Image (fuzzy search)", value="image_search"),
    ]

    @tree.command(name="schedule", description="Schedule a message to be sent later")
    @app_commands.describe(
        minutes="Send after N minutes (1-10080)",
        content="Text to send (or fuzzy-search query if mode=image)",
        mode="Send text or post an image",
        channel="Target channel (default: current channel)",
    )
    @app_commands.choices(mode=mode_choices)
    async def schedule_cmd(
        interaction: discord.Interaction,
        minutes: app_commands.Range[int, 1, SCHEDULE_MAX_MINUTES],
        content: str,
        mode: Optional[app_commands.Choice[str]] = None,
        channel: Optional[discord.TextChannel] = None,
    ):
        resolved_channel_id = channel.id if channel is not None else interaction.channel_id
        if resolved_channel_id is None:
            await interaction.response.send_message(
                "Cannot determine target channel (try using the channel option).",
                ephemeral=True,
            )
            return

        channel_id = str(resolved_channel_id)
        now = int(time.time())
        run_at = now + int(minutes) * 60
        kind = (mode.value if mode is not None else "text")

        schedule_id = create_scheduled_message(
            conn,
            channel_id=channel_id,
            kind=kind,
            content=content,
            run_at=run_at,
            repeat_interval=None,
            created_by=str(interaction.user.id) if interaction.user else None,
        )
        await interaction.response.send_message(
            f"Scheduled ({'image' if kind == 'image_search' else 'text'}) (id={schedule_id}) "
            f"for <t:{run_at}:F> in <#{channel_id}>.",
            ephemeral=True,
        )

    @tree.command(name="schedule_at", description="Schedule a message at a specific date/time (minute precision)")
    @app_commands.describe(
        month="Month (1-12)",
        day="Day (1-31)",
        hour="Hour (0-23)",
        minute="Minute (0-59)",
        content="Text to send (or fuzzy-search query if mode=image)",
        mode="Send text or post an image",
        channel="Target channel (default: current channel)",
    )
    @app_commands.choices(mode=mode_choices)
    async def schedule_at_cmd(
        interaction: discord.Interaction,
        month: app_commands.Range[int, 1, 12],
        day: app_commands.Range[int, 1, 31],
        hour: app_commands.Range[int, 0, 23],
        minute: app_commands.Range[int, 0, 59],
        content: str,
        mode: Optional[app_commands.Choice[str]] = None,
        channel: Optional[discord.TextChannel] = None,
    ):
        resolved_channel_id = channel.id if channel is not None else interaction.channel_id
        if resolved_channel_id is None:
            await interaction.response.send_message(
                "Cannot determine target channel (try using the channel option).",
                ephemeral=True,
            )
            return

        now_dt = datetime.now().astimezone()
        try:
            run_at = compute_run_at_from_components(
                month=int(month),
                day=int(day),
                hour=int(hour),
                minute=int(minute),
                now=now_dt,
            )
        except ScheduleTimeError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        channel_id = str(resolved_channel_id)
        kind = (mode.value if mode is not None else "text")
        schedule_id = create_scheduled_message(
            conn,
            channel_id=channel_id,
            kind=kind,
            content=content,
            run_at=run_at,
            repeat_interval=None,
            created_by=str(interaction.user.id) if interaction.user else None,
        )

        await interaction.response.send_message(
            f"Scheduled ({'image' if kind == 'image_search' else 'text'}) (id={schedule_id}) "
            f"for <t:{run_at}:F> in <#{channel_id}>.",
            ephemeral=True,
        )

    @tree.command(name="schedule_repeat", description="Repeat sending text or posting an image on a fixed interval")
    @app_commands.describe(
        hour="Start hour (0-23)",
        minute="Start minute (0-59)",
        interval="Repeat interval",
        content="Text to send (or fuzzy-search query if mode=image)",
        mode="Send text or post an image",
        channel="Target channel (default: current channel)",
    )
    @app_commands.choices(
        interval=[
            app_commands.Choice(name="Every minute", value="minute"),
            app_commands.Choice(name="Every hour", value="hour"),
            app_commands.Choice(name="Every day", value="day"),
        ],
        mode=mode_choices,
    )
    async def schedule_repeat_cmd(
        interaction: discord.Interaction,
        hour: app_commands.Range[int, 0, 23],
        minute: app_commands.Range[int, 0, 59],
        interval: app_commands.Choice[str],
        content: str,
        mode: Optional[app_commands.Choice[str]] = None,
        channel: Optional[discord.TextChannel] = None,
    ):
        resolved_channel_id = channel.id if channel is not None else interaction.channel_id
        if resolved_channel_id is None:
            await interaction.response.send_message(
                "Cannot determine target channel (try using the channel option).",
                ephemeral=True,
            )
            return

        now_dt = datetime.now().astimezone()
        try:
            run_at = compute_next_occurrence_from_hour_minute(
                hour=int(hour),
                minute=int(minute),
                now=now_dt,
            )
        except ScheduleTimeError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        channel_id = str(resolved_channel_id)
        kind = (mode.value if mode is not None else "text")
        repeat_interval = interval.value

        schedule_id = create_scheduled_message(
            conn,
            channel_id=channel_id,
            kind=kind,
            content=content,
            run_at=run_at,
            repeat_interval=repeat_interval,
            created_by=str(interaction.user.id) if interaction.user else None,
        )

        await interaction.response.send_message(
            f"Scheduled repeat ({'image' if kind == 'image_search' else 'text'}) (id={schedule_id}) "
            f"starting <t:{run_at}:F> every {repeat_interval} in <#{channel_id}>.",
            ephemeral=True,
        )

    @tree.command(name="schedule_list", description="List scheduled messages in this channel")
    @app_commands.describe(limit="Max items to show (1-20)")
    async def schedule_list_cmd(
        interaction: discord.Interaction,
        limit: app_commands.Range[int, 1, 20] = 10,
    ):
        if interaction.channel_id is None:
            await interaction.response.send_message(
                "This command must be used in a channel.",
                ephemeral=True,
            )
            return

        channel_id = str(interaction.channel_id)
        rows = list_scheduled_messages(conn, channel_id=channel_id, limit=int(limit))
        if not rows:
            await interaction.response.send_message("No pending scheduled messages.", ephemeral=True)
            return

        lines = []
        for r in rows:
            kind = r.get("kind") or "text"
            repeat = r.get("repeat_interval")
            preview = (r["content"][:60] + "…") if len(r["content"]) > 60 else r["content"]
            prefix = "img" if kind == "image_search" else "text"
            repeat_part = f" repeat={repeat}" if repeat else ""
            lines.append(f"- {prefix} id={r['id']} at <t:{r['run_at']}:F>{repeat_part}: {preview}")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @tree.command(name="schedule_cancel", description="Cancel a scheduled message by id")
    @app_commands.describe(schedule_id="The schedule id to cancel")
    async def schedule_cancel_cmd(
        interaction: discord.Interaction,
        schedule_id: int,
    ):
        ok = cancel_scheduled_message(
            conn,
            schedule_id=int(schedule_id),
            requester_id=str(interaction.user.id) if interaction.user else None,
        )
        if ok:
            await interaction.response.send_message(f"Canceled schedule id={schedule_id}.", ephemeral=True)
        else:
            await interaction.response.send_message(
                "Unable to cancel (not found, not pending, or not created by you).",
                ephemeral=True,
            )

