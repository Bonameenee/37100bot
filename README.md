# 37100bot

A lightweight Telegram bot that announces daily events and manages food orders for a community chat.

## 1. Create a Telegram bot

1. Talk to [@BotFather](https://t.me/BotFather).
2. Run `/newbot` and follow the prompts to choose the bot name and username.
3. Copy the HTTP API token that BotFather returns; you will need it for `config.json`.

## 2. Prepare the Python environment

```bash
git clone https://github.com/your-org/37100bot.git
cd 37100bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Keep the virtual environment active whenever you run or manage the bot.

## 3. Configure the bot

Create `config.json` in the project root with the following structure:

```json
{
  "TOKEN": "TELEGRAM_BOT_API_TOKEN",
  "ADMIN_ID": [12345678, 87654321],
  "CHAT_ID": -1001234567890,
  "THREAD_ID": 42,
  "API_BASE_URL": "https://example.com",
  "API_TOKEN": "BACKEND_ACCESS_TOKEN"
}
```

- `TOKEN`: Telegram API token from BotFather.
- `ADMIN_ID`: list of Telegram user IDs that can run admin commands.
- `CHAT_ID`: target chat or supergroup ID (negative values for groups).
- `THREAD_ID` (optional): topic/thread ID if the bot operates inside a forum-style supergroup.
- `API_BASE_URL` and `API_TOKEN`: endpoint and token for the external service that provides daily events. Adjust or omit if not needed.

If the bot runs on a server, set correct permissions on `config.json` to avoid exposing secrets.

## 4. Run the bot manually (for testing)

```bash
source .venv/bin/activate
python 37100bot.py
```

The bot will start polling. Hit `Ctrl+C` to stop.

## 5. Install as a systemd service

Create `/etc/systemd/system/37100bot.service` with:

```ini
[Unit]
Description=37100 Telegram Bot
After=network.target

[Service]
User=botuser
Group=botuser
WorkingDirectory=/opt/37100bot
Environment="PATH=/opt/37100bot/.venv/bin"
ExecStart=/opt/37100bot/.venv/bin/python /opt/37100bot/37100bot.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Adjust paths, user, and group to match your deployment.

Deploy the codebase, create the virtual environment, install requirements, and place `config.json` under `/opt/37100bot`.

Reload systemd and enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now 37100bot.service
```

Check the logs:

```bash
journalctl -u 37100bot.service -f
```

## 6. Optional: automated updates

You can automate pulls and service restarts via cron or CI. For example, add a script under `/opt/37100bot/updatebot.sh` to pull from `main` and restart the service, then use cron to execute it periodically.

---

If you encounter issues, verify the bot token, chat IDs, and network connectivity between the bot host and the external API. Contributions and improvements are welcome. 
