# Yagel Is Not Here

A Discord bot that watches a specific user's voice presence and alerts their friends if the user has been inactive in voice for a while so you don't get baited by a silent mic.

## Features
- Audit‑log aware presence updates: ignores moderator/server moves when determining activity
- Debounced activity writes to reduce disk churn
- Robust config parsing with clear errors
- UTF‑8 JSON persistence of last activity time
- Smart friend mention message formatting
- Alerts only when the user is actually in a voice channel

## How it works (high‑level)
- The bot listens to `on_voice_state_update` for the target user
  - Treats self‑mute, self‑deaf, stream, and video toggles as user‑initiated activity
  - Checks Guild Audit Log for recent `member_move` to avoid counting moderator moves as activity
  - Ignores AFK auto‑moves
  - Debounces writes (2s) to `last_active.json`
- A background task (`check_user_status`) runs every few minutes
  - If the user is in a voice channel and has been inactive beyond the configured threshold, it posts an alert message in the specified channel and resets the state to avoid spamming

## Requirements
- Python 3.10+
- A Discord bot application & token
- Bot permissions in the target server:
  - Read Messages / View Channel for your alert channel
  - Send Messages in your alert channel
  - View Audit Log (to correctly detect server‑initiated voice moves)
  - Read Member Presence (Intents: Presence, Members, Voice States)

## Project structure
```
C:\Users\<you>\...\Yagel Is Not Here
├─ main.py               # Bot implementation
├─ last_active.json      # Timestamp persistence (auto‑created/updated)
└─ .env                  # Local environment variables (not committed)
```

## Setup
1) Clone and enter the project directory
2) Create and fill `.env`

Example `.env`:
```
DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE
CHANNEL_ID=123456789012345678  # Channel where alerts are posted
USER_ID=987654321098765432     # The user whose voice activity is tracked
FRIENDS=111111111111111111,222222222222222222  # optional: IDs to @mention
```

Notes:
- `CHANNEL_ID` and `USER_ID` must be integers (as strings in the file). The app validates them on start.
- `FRIENDS` is optional; provide a comma‑separated list of user IDs. Whitespace will be trimmed.

3) Install dependencies
```
pip install -r requirements.txt
```
If you don't maintain a `requirements.txt`, these are the minimal packages:
```
pip install discord.py python-dotenv
```

## Running the bot
From the project root:
```
python main.py
```
When the bot connects, you should see a log line like:
```
<BotName>#1234 has connected to Discord!
```

## Configuration & behavior details
- Activity debounce: 2 seconds (configurable in code via `DEBOUNCE_SECONDS`)
- Away threshold: 15 minutes by default (`AWAY_ALERT_THRESHOLD_MINUTES`)
- Check interval: 5 minutes (`LOOP_CHECK_INTERVAL_MINUTES`)
- Timestamps use `discord.utils.utcnow()` and are stored as ISO‑8601 strings in `last_active.json`
- JSON keys are stringified user IDs to avoid numeric/JSON key mismatches

## Permissions & Intents
Make sure the bot application has the following intents enabled in the Discord Developer Portal and also in code:
- Server Members Intent (members)
- Presence Intent (presences)
- Message Content is NOT required
- Voice States Intent (voice_states)

The bot also benefits from the "View Audit Log" permission on the target server to correctly classify moves.

## Troubleshooting
- Bot starts but never alerts
  - Confirm the `CHANNEL_ID` is correct and the bot can send messages there
  - Ensure the tracked `USER_ID` is actually connected to a voice channel
  - Check that `last_active.json` exists and is writable; it will be created automatically
- Crashes on startup with `.env` error
  - Validate that `DISCORD_TOKEN`, `CHANNEL_ID`, and `USER_ID` are present; `CHANNEL_ID`/`USER_ID` must be integers (as strings)
- False alerts or missed alerts
  - Verify the bot has "View Audit Log" permission; without it, the bot may misclassify certain channel moves
- Timezone or timestamp parsing issues
  - The code handles naive/aware datetimes; if `last_active.json` gets corrupted, it will reset and continue

## Development
- Code style: follow existing formatting and patterns in `main.py`
- Commit messages: Conventional Commits are recommended
  - Example:
```
feat(voice-presence): audit-log aware presence updates, debounce, safer env parsing, and robust alert loop
```
- Local testing tips:
  - Create a private test server and a dedicated text channel for alerts
  - Grant the bot View Audit Log and required intents
  - Use an alt account or a friend to simulate moderator moves

## Security
- Keep `.env` out of version control (use `.gitignore`)
- Limit bot token access
- Consider using a separate role for the bot with only necessary permissions

## Deployment
- Run as a service (e.g., systemd, PM2, or a Windows service wrapper) if you need it always on
- Monitor logs and restart on failure
- Back up `last_active.json` if long‑term continuity matters; transient loss is generally acceptable


## Acknowledgements
- Built with [discord.py](https://github.com/Rapptz/discord.py)
- Env handling via [python‑dotenv](https://github.com/theskumar/python-dotenv)
