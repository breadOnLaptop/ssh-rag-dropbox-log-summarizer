# SSH-RAG Dropbox Log Summarizer

A multi-threaded Python daemon that monitors user drop zones, safely handles large files, queues API requests to prevent model overload, and leverages Open WebUI’s native OpenAI-compatible API to generate Markdown summaries of log files.

## Architecture Overview
This application sets up "Drop Zones" for users. Users can SCP log files into their respective `logs_in` directories. The Watcher Daemon will:
1. Detect when the file upload is completely finished (using `on_closed` events).
2. Queue the processing to avoid overwhelming the AI API or running out of memory.
3. Automatically truncate files that are too large (default max size: 1MB).
4. Send the log content to a configured AI Model (e.g., Open WebUI running Gemma 4).
5. Output a structured Markdown report in the user's `reports_out` directory.

## Repository Structure
- `src/watcher.py` - Core multi-threaded Python daemon.
- `config/user_keys.example.json` - Example configuration for mapping users to API keys.
- `systemd/log_agent.service` - Systemd service file for running the daemon in the background.
- `scripts/setup.sh` - Automated script to initialize folders, permissions, and environments.
- `scripts/cleanup_cron.sh` - Cron script to prevent disk overflow by removing old logs/reports.
- `tests/` - Pytest coverage for the core processor.

## Installation

### 1. Automated Setup
The easiest way to get started is by running the setup script on your server:

```bash
chmod +x scripts/setup.sh
sudo ./scripts/setup.sh
```

### 2. Configuration
The script installs to `/opt/log_agent`. You must configure your API tokens mapping local usernames to Open WebUI keys:

```bash
sudo nano /opt/log_agent/config/user_keys.json
```
```json
{
    "alice": "sk-your-openwebui-api-key-for-alice",
    "bob": "sk-your-openwebui-api-key-for-bob"
}
```

### 3. Start the Background Service
Enable and start the systemd service so it persists across reboots.

```bash
sudo cp systemd/log_agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now log_agent
```

### 4. Setup Automated Disk Cleanup
To prevent logs from consuming your server's disk space, add a cron job:

```bash
sudo crontab -e
```
Add the following line (runs at midnight, deletes files older than 7 days):
```bash
0 0 * * * /opt/log_agent/scripts/cleanup_cron.sh
```

## Running Tests
This project includes pytest coverage. To run the tests:

```bash
# Create a virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run pytest
pytest tests/
```

## Environment Variables
The daemon can be customized by exporting these environment variables (can be added to the `.service` file):
- `LOG_AGENT_BASE_DIR` (default: `/opt/log_agent`)
- `LOG_AGENT_CONFIG_PATH` (default: `<BASE_DIR>/config/user_keys.json`)
- `LOG_AGENT_DROP_ZONES_DIR` (default: `<BASE_DIR>/drop_zones`)
- `LOG_AGENT_API_URL` (default: `http://localhost:8080/api/chat/completions`)
- `LOG_AGENT_MODEL` (default: `gemma-4`)
- `LOG_AGENT_MAX_FILE_SIZE` (default: `1048576` bytes / 1MB)
