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


## Remote WhatsApp control

The project can also be controlled remotely through the WhatsApp Business Platform. The official WhatsApp Cloud API supports programmatic sending/receiving and webhook-based events.

The remote control service is whatsapp_server.py. It exposes:

    /health
    /webhook

Only the WhatsApp number configured in WHATSAPP_ADMIN_PHONE is allowed to issue commands. Webhook requests are protected with the Meta X-Hub-Signature-256 application-secret signature.

### Remote commands

Send these commands from the authorized WhatsApp account:

    HELP
    STATUS
    TREND India
    TREND Global
    TREND Technology
    TREND Business
    COMMENT <LinkedIn post text>
    APPROVE <ID>
    REJECT <ID>

For a poster-based comment, send the poster/image as a WhatsApp image and put the LinkedIn post text in the image caption. The service downloads the media through the WhatsApp Cloud API and sends the post text + image to the AI comment generator.

Generated posts/comments receive an approval ID. APPROVE <ID> records your approval, but the final LinkedIn action remains manual.

### WhatsApp configuration

Copy .env.example and configure:

    WHATSAPP_ACCESS_TOKEN
    WHATSAPP_PHONE_NUMBER_ID
    WHATSAPP_APP_SECRET
    WHATSAPP_VERIFY_TOKEN
    WHATSAPP_ADMIN_PHONE
    WHATSAPP_GRAPH_VERSION=v26.0

The WhatsApp Cloud API requires a Meta business portfolio, WhatsApp Business Account, and business phone number. The app needs WhatsApp Business Platform messaging permissions and a public HTTPS webhook endpoint.

### Remote deployment

render.yaml contains a ready web-service definition for the WhatsApp control server:

    uvicorn whatsapp_server:app --host 0.0.0.0 --port $PORT

After deployment, configure the Meta webhook callback URL as your deployed HTTPS URL followed by /webhook.

Use the same WHATSAPP_VERIFY_TOKEN in your Meta webhook configuration and application environment.

For production, use persistent storage for WHATSAPP_STATE_DB so approval records survive restarts.

### Important LinkedIn boundary

WhatsApp can remotely manage the content workflow, but it must not be used to drive unauthorized LinkedIn automation. LinkedIn's current User Agreement prohibits bots or unauthorized automated methods for creating, commenting, liking, sharing, messaging, and other inauthentic engagement. LinkedIn also states that automated comments are not allowed.

This project therefore uses WhatsApp for remote generation, review, status, and explicit approval, while the final LinkedIn interaction remains a human action.

## License

GPL-3.0
