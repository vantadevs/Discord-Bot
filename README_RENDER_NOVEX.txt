NOVEX MARKET — Render Free Web Service
======================================

Files:
- novex_market_rebuild_bot.py : Discord bot + HTTP health server
- requirements.txt           : Python dependencies

Render settings:
- Runtime: Python 3
- Build Command: pip install -r requirements.txt
- Start Command: python novex_market_rebuild_bot.py
- Instance Type: Free

Environment Variables (Render Dashboard > Environment):
- DISCORD_TOKEN = your Discord bot token (keep this secret)
- GUILD_ID = 694270550524035112 (already used as the code default; optional)

The service listens on 0.0.0.0 and Render's PORT environment variable.
Health endpoints: / and /health

After deployment, open the service URL; it should return JSON with status=ok.
The bot must also be invited to your server with Manage Channels and Manage Roles.
Move the bot's highest role above the roles it needs to manage.

IMPORTANT: /rebuild_novex deletes existing channels (and their message history)
and eligible custom roles. Run /preview_rebuild first. Only the server owner
can execute the rebuild, and the exact confirmation phrase is required.

Render Free web services can spin down after inactivity. When sleeping, the
Discord bot disconnects and slash commands will not respond until it wakes.
Free hosting is therefore not a guaranteed always-online Discord bot host.
