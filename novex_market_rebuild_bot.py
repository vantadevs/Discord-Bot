"""
NOVEX MARKET Discord Rebuild Bot
================================

Python 3.10+
Install:
    python -m pip install -U discord.py

Set your bot token:
    Windows PowerShell:
        $env:DISCORD_TOKEN="YOUR_BOT_TOKEN"
        $env:GUILD_ID="YOUR_SERVER_ID"
        python novex_market_rebuild_bot.py

    macOS/Linux:
        export DISCORD_TOKEN="YOUR_BOT_TOKEN"
        export GUILD_ID="YOUR_SERVER_ID"
        python novex_market_rebuild_bot.py

Invite the bot with these permissions:
    Manage Channels, Manage Roles, View Channels, Send Messages
Its bot role must be above the roles it needs to delete/manage.

IMPORTANT:
- This is destructive. Deleting channels also deletes their messages and history.
- Back up your server layout and anything important first.
- Run /preview_rebuild first.
- Only the server owner can run /rebuild_novex.
- The rebuild requires the exact confirmation phrase: REBUILD NOVEX MARKET
- @everyone, managed integration/bot roles, and roles at/above the bot's
  highest role are never deleted.
- Discord may prevent deletion of channels/roles the bot cannot manage.
- This script creates the layout and permissions; it does not implement
  ticket handling, verification, vouch automation, or live member counters.
"""

import os
import asyncio
from aiohttp import web
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID", "694270550524035112")
CONFIRMATION = "REBUILD NOVEX MARKET"

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN environment variable.")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Roles are listed from highest to lowest desired hierarchy.
ROLE_SPECS = [
    ("NOVEX Owner", 0xF1C40F, True, discord.Permissions(administrator=True)),
    ("NOVEX Management", 0xA855F7, True, discord.Permissions(
        manage_guild=True, manage_channels=True, manage_roles=True,
        manage_messages=True, kick_members=True, ban_members=True,
        moderate_members=True, view_audit_log=True
    )),
    ("NOVEX Staff", 0x06B6D4, True, discord.Permissions(
        manage_messages=True, view_audit_log=True
    )),
    ("NOVEX Moderator", 0x3B82F6, True, discord.Permissions(
        manage_messages=True, moderate_members=True
    )),
    ("NOVEX Support", 0x22D3EE, True, discord.Permissions.none()),
    ("NOVEX Reseller", 0xD946EF, False, discord.Permissions.none()),
    ("NOVEX Partner", 0x22C55E, False, discord.Permissions.none()),
    ("NOVEX VIP", 0xEAB308, False, discord.Permissions.none()),
    ("NOVEX Customer", 0x38BDF8, False, discord.Permissions.none()),
    ("Verified", 0x64748B, False, discord.Permissions.none()),
    ("Member", 0x94A3B8, False, discord.Permissions.none()),
    ("NOVEX Bots", 0x5865F2, False, discord.Permissions.none()),
]

STAFF_ROLES = {
    "NOVEX Owner", "NOVEX Management", "NOVEX Staff",
    "NOVEX Moderator", "NOVEX Support"
}

# Each category has a visibility policy:
# onboarding = visible to everyone; verified = visible to Verified and staff;
# stats = visible to everyone but read-only; staff = staff-only.
CATEGORY_SPECS = [
    ("💰・Products", "verified", [
        ("text", "🛒・script-services"),
        ("text", "🛒・discord-services"),
        ("text", "🛒・roblox-services"),
        ("text", "🛒・social-boost"),
        ("text", "🛒・app-services"),
        ("text", "❗・discounts"),
    ]),
    ("💸・Purchase", "verified", [
        ("text", "🚀・create-ticket"),
        ("text", "💵・how-to-purchase"),
        ("text", "📋・how-to-vouch"),
    ]),
    ("📊・SERVER STATS", "stats", [
        ("voice", "👥・All Members: update me"),
        ("voice", "👤・Members: update me"),
        ("voice", "🤖・Bots: update me"),
    ]),
    ("📊・Server Status", "stats", [
        ("voice", "🟢・Store: OPEN"),
        ("voice", "🔗・discord.gg/your-invite"),
    ]),
    ("🚀・Welcome", "onboarding", [
        ("text", "👋・welcome"),
        ("text", "📜・rules"),
        ("text", "📒・our-terms"),
        ("text", "✅・verify"),
    ]),
    ("📣・Important", "verified", [
        ("text", "📣・important-notices"),
    ]),
    ("👀・Legit", "verified", [
        ("text", "👀・am-i-legit"),
        ("text", "💰・vouch"),
    ]),
    ("☁️・Community", "verified", [
        ("text", "🌍・global-chat"),
        ("text", "📸・media"),
        ("text", "🤖・commands"),
    ]),
    ("🎥・Socials", "verified", [
        ("text", "🌐・website"),
        ("text", "🎥・socials"),
    ]),
    ("🤝・Partnership", "verified", [
        ("text", "📢・server-ad"),
        ("text", "🤝・partnership"),
    ]),
    ("🔒・NOVEX STAFF", "staff", [
        ("text", "💬・staff-chat"),
        ("text", "📢・staff-announcements"),
        ("text", "📋・staff-logs"),
        ("text", "🛒・order-logs"),
        ("text", "🎫・ticket-logs"),
        ("voice", "🔊・staff-voice"),
    ]),
]


def staff_overwrites(guild: discord.Guild, roles: dict[str, discord.Role]):
    overwrites = {}
    for name in STAFF_ROLES:
        role = roles.get(name)
        if role:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                read_message_history=True,
                send_messages=True,
                connect=True,
                speak=True,
            )
    return overwrites


def category_overwrites(guild: discord.Guild, roles: dict[str, discord.Role], policy: str):
    everyone = guild.default_role
    overwrites = {}

    if policy == "onboarding":
        overwrites[everyone] = discord.PermissionOverwrite(
            view_channel=True, read_message_history=True, send_messages=True
        )
    elif policy == "stats":
        overwrites[everyone] = discord.PermissionOverwrite(
            view_channel=True, read_message_history=True, send_messages=False,
            connect=False
        )
    else:
        overwrites[everyone] = discord.PermissionOverwrite(
            view_channel=False, read_message_history=False, send_messages=False
        )
        verified = roles.get("Verified")
        member = roles.get("Member")
        if verified:
            overwrites[verified] = discord.PermissionOverwrite(
                view_channel=True, read_message_history=True, send_messages=True,
                connect=True, speak=True
            )
        if member:
            overwrites[member] = discord.PermissionOverwrite(
                view_channel=True, read_message_history=True, send_messages=True,
                connect=True, speak=True
            )

    if policy == "staff":
        # Remove any broad @everyone/member visibility; only staff roles get access.
        overwrites[everyone] = discord.PermissionOverwrite(view_channel=False)
        for name in ("Verified", "Member", "NOVEX Customer", "NOVEX VIP",
                     "NOVEX Reseller", "NOVEX Partner"):
            role = roles.get(name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=False)

    overwrites.update(staff_overwrites(guild, roles))
    return overwrites


def manageable_roles(guild: discord.Guild):
    me = guild.me
    if me is None:
        return []
    return [
        role for role in guild.roles
        if role != guild.default_role
        and not role.managed
        and role < me.top_role
    ]


async def get_counts(guild: discord.Guild):
    channels = len(guild.channels)
    roles = len(manageable_roles(guild))
    return channels, roles


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    if GUILD_ID:
        obj = discord.Object(id=int(GUILD_ID))
        bot.tree.copy_global_to(guild=obj)
        await bot.tree.sync(guild=obj)
        print(f"Commands synced to server {GUILD_ID}")
    else:
        await bot.tree.sync()
        print("Global commands synced; global slash commands can take time to appear.")


@bot.tree.command(name="preview_rebuild", description="Preview the NOVEX MARKET server rebuild.")
@app_commands.guild_only()
async def preview_rebuild(interaction: discord.Interaction):
    guild = interaction.guild
    if guild is None:
        return await interaction.response.send_message("Use this command inside your server.", ephemeral=True)
    if interaction.user.id != guild.owner_id:
        return await interaction.response.send_message("Only the server owner can preview this rebuild.", ephemeral=True)

    deletable_roles = manageable_roles(guild)
    planned_channels = sum(len(channels) + 1 for _, _, channels in CATEGORY_SPECS)
    embed = discord.Embed(
        title="NOVEX MARKET — Rebuild Preview",
        description=(
            "This is a destructive rebuild. Existing channel messages and history "
            "will be lost when channels are deleted.\n\n"
            f"**Channels/categories to create:** {planned_channels}\n"
            f"**Roles to create:** {len(ROLE_SPECS)}\n"
            f"**Existing channels/categories currently present:** {len(guild.channels)}\n"
            f"**Existing custom roles eligible for deletion:** {len(deletable_roles)}\n\n"
            f"To proceed, use `/rebuild_novex` and enter exactly:\n"
            f"`{CONFIRMATION}`"
        ),
        color=0x00CFFF,
    )
    embed.set_footer(text="Back up important content before rebuilding.")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="rebuild_novex", description="Delete the old layout and create the NOVEX MARKET layout.")
@app_commands.describe(confirmation="Type REBUILD NOVEX MARKET exactly to confirm.")
@app_commands.guild_only()
async def rebuild_novex(interaction: discord.Interaction, confirmation: str):
    guild = interaction.guild
    if guild is None:
        return await interaction.response.send_message("Use this command inside your server.", ephemeral=True)
    if interaction.user.id != guild.owner_id:
        return await interaction.response.send_message("Only the server owner can rebuild the server.", ephemeral=True)
    if confirmation != CONFIRMATION:
        return await interaction.response.send_message(
            f"Confirmation did not match. Nothing was changed. Type `{CONFIRMATION}` exactly.",
            ephemeral=True,
        )

    me = guild.me
    if me is None or not me.guild_permissions.manage_channels or not me.guild_permissions.manage_roles:
        return await interaction.response.send_message(
            "I need **Manage Channels** and **Manage Roles** permissions, and my bot role must be high enough in the role list.",
            ephemeral=True,
        )

    await interaction.response.defer(ephemeral=True, thinking=True)

    failures = []
    # Delete existing channels first (including categories). Messages/history are deleted too.
    for channel in list(guild.channels):
        try:
            await channel.delete(reason="NOVEX MARKET rebuild requested by server owner")
        except (discord.Forbidden, discord.HTTPException) as exc:
            failures.append(f"Channel `{channel.name}`: {type(exc).__name__}")

    # Delete eligible custom roles. Never touch @everyone, managed roles or roles
    # equal to/above the bot's highest role.
    for role in manageable_roles(guild):
        try:
            await role.delete(reason="NOVEX MARKET rebuild requested by server owner")
        except (discord.Forbidden, discord.HTTPException) as exc:
            failures.append(f"Role `{role.name}`: {type(exc).__name__}")

    # Create roles in reverse order so the desired senior roles can be positioned
    # above junior roles where Discord allows it.
    created_roles = {}
    for name, colour, hoist, permissions in reversed(ROLE_SPECS):
        try:
            role = await guild.create_role(
                name=name,
                colour=discord.Colour(colour),
                hoist=hoist,
                mentionable=False,
                permissions=permissions,
                reason="NOVEX MARKET rebuild",
            )
            created_roles[name] = role
        except (discord.Forbidden, discord.HTTPException) as exc:
            failures.append(f"Create role `{name}`: {type(exc).__name__}")

    # Reposition roles in the declared top-to-bottom order, if possible.
    try:
        ordered = [created_roles[name] for name, *_ in ROLE_SPECS if name in created_roles]
        # Highest position first; keep below the bot's own top role.
        top_position = max(1, me.top_role.position - 1)
        positions = {}
        for index, role in enumerate(ordered):
            positions[role] = max(1, top_position - index)
        if positions:
            await guild.edit_role_positions(positions=positions, reason="NOVEX MARKET role hierarchy")
    except (discord.Forbidden, discord.HTTPException) as exc:
        failures.append(f"Role ordering: {type(exc).__name__}")

    # Build categories and channels.
    for category_name, policy, channel_specs in CATEGORY_SPECS:
        try:
            overwrites = category_overwrites(guild, created_roles, policy)
            category = await guild.create_category(
                category_name,
                overwrites=overwrites,
                reason="NOVEX MARKET rebuild",
            )
        except (discord.Forbidden, discord.HTTPException) as exc:
            failures.append(f"Create category `{category_name}`: {type(exc).__name__}")
            continue

        for channel_type, channel_name in channel_specs:
            try:
                if channel_type == "text":
                    await guild.create_text_channel(
                        channel_name, category=category,
                        reason="NOVEX MARKET rebuild",
                    )
                else:
                    await guild.create_voice_channel(
                        channel_name, category=category,
                        reason="NOVEX MARKET rebuild",
                    )
            except (discord.Forbidden, discord.HTTPException) as exc:
                failures.append(f"Create channel `{channel_name}`: {type(exc).__name__}")

    result = discord.Embed(
        title="NOVEX MARKET rebuild finished",
        description=(
            f"Created **{len(created_roles)} / {len(ROLE_SPECS)} roles**.\n"
            f"Attempted **{sum(len(channels) for _, _, channels in CATEGORY_SPECS)} channels** "
            f"across **{len(CATEGORY_SPECS)} categories**."
        ),
        color=0x00CFFF,
    )
    if failures:
        result.add_field(
            name=f"Items needing attention ({len(failures)})",
            value="\n".join(failures[:15])[:1024],
            inline=False,
        )
        result.set_footer(text="Check the bot role hierarchy and permissions for failed items.")
    else:
        result.set_footer(text="No API errors were reported. Review permissions and channel access.")
    await interaction.followup.send(embed=result, ephemeral=True)


async def health_check(request):
    """Render web-service health endpoint."""
    return web.json_response({
        "status": "ok",
        "service": "NOVEX MARKET Discord Bot",
        "discord_connected": bot.is_ready(),
    })


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Render web server listening on port {port}")
    return runner


async def main():
    runner = await start_web_server()
    try:
        await bot.start(TOKEN)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

