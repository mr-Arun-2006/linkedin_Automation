# LinkedIn Automation

A local Streamlit application that turns GitHub project information and current news into professional LinkedIn post drafts.

## Features

- Reads public GitHub repository metadata, README content, and recent commits.
- Generates project launch, progress, technical, and learning post drafts.
- Fetches India-focused news from GNews.
- Uses an OpenRouter model for reasoning-assisted news analysis and post generation.
- Supports the OpenRouter free-model router through `openrouter/free`.
- Copies drafts to the clipboard and opens LinkedIn for manual publishing.
- Keeps a local history of generated drafts.
- No LinkedIn API key, LinkedIn login, cookie, or session token is required.

## API keys

Two optional API keys are supported:

- `OPENROUTER_API_KEY` for reasoning-assisted AI generation.
- `GNEWS_API_KEY` for news retrieval.

The default AI model is `openrouter/free`.

Never commit real keys to GitHub.

### Windows PowerShell

Set keys for the current terminal session:

    $env:OPENROUTER_API_KEY="your_openrouter_key"
    $env:GNEWS_API_KEY="your_gnews_key"
    $env:OPENROUTER_MODEL="openrouter/free"

    streamlit run app.py

For Streamlit deployment, use the application's Secrets configuration instead of committing a `.env` file.

### Optional .env file

Copy `.env.example` to `.env` and fill in the values. The repository ignores `.env`.

## Run locally

    python -m venv .venv
    .venv\\Scripts\\Activate.ps1
    pip install -r requirements.txt
    streamlit run app.py

Linux / macOS:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    streamlit run app.py

## Workflow

1. Enter a public GitHub repository.
2. Generate a project-based LinkedIn draft.
3. Fetch current news by topic.
4. Run reasoning-assisted news analysis when the OpenRouter key is configured.
5. Review and edit the final draft.
6. Copy it and open LinkedIn.
7. Paste and publish manually.

## News freshness

GNews provides live updates on paid plans, while its current Free plan is intended for development/testing and has a 12-hour delay, so the application should not label Free-plan results as real-time. citeturn125767view0

## LinkedIn publishing

LinkedIn prohibits third-party software that automates actions such as posting, commenting, liking, sharing, and messaging. This project therefore automates content preparation while leaving the final LinkedIn publication to the account owner.

## Security

This application does not store LinkedIn credentials. API keys are read from environment variables or Streamlit secrets and are not displayed in the UI.


## Remote Telegram control

The project can be controlled remotely through a Telegram Bot. Telegram bots use the Bot API and can receive updates through webhooks or long polling. For this project, the cloud deployment uses a webhook. citeturn545338search2turn536513search0

The remote control service is telegram_server.py.

### Remote commands

Send these commands from the authorized Telegram account:

    /help
    /status
    /trend india
    /trend global
    /trend technology
    /trend business
    /comment <LinkedIn post text>
    /approve <ID>
    /reject <ID>

For a poster-based comment, send the LinkedIn poster/image with a caption beginning with:

    /comment <LinkedIn post text>

The bot reads the poster image plus the caption and generates a builder-style comment with a specific observation, professional insight, practical building angle, and one real question.

Generated drafts receive an approval ID and also include Approve/Reject buttons.

### Security

Only the Telegram numeric user ID configured in TELEGRAM_ADMIN_USER_ID can control the bot.

Telegram webhook requests are also checked against TELEGRAM_WEBHOOK_SECRET using the X-Telegram-Bot-Api-Secret-Token header supported by Telegram's setWebhook API. citeturn536513search0

Never commit TELEGRAM_BOT_TOKEN or any other secret to GitHub.

### Configuration

Copy .env.example and configure:

    TELEGRAM_BOT_TOKEN
    TELEGRAM_ADMIN_USER_ID
    TELEGRAM_WEBHOOK_SECRET

Create the bot with @BotFather and store the generated token securely. Telegram notes that anyone with the bot token can control the bot, so it must be treated as a secret. citeturn536513search9

### Remote deployment

render.yaml contains a web-service definition for:

    uvicorn telegram_server:app --host 0.0.0.0 --port $PORT

After deployment, set the Telegram webhook to your public HTTPS endpoint:

    https://<your-render-service>/webhook

Telegram webhooks require HTTPS and the service must be publicly reachable. citeturn545338search1turn536513search0

### Remote workflow

    Telegram command/image
            |
            v
    Secure webhook
            |
            +--> GNews --> current-news trend post
            |
            +--> OpenRouter --> AI generation
            |
            v
    Approval ID + Approve/Reject
            |
            v
    Manual LinkedIn action

Telegram manages the remote content workflow. It does not automate LinkedIn posting or commenting.

## License

GPL-3.0
