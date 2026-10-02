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

## License

GPL-3.0
