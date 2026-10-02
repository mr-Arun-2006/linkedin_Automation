# LinkedIn Automation

A local Streamlit application that turns public GitHub repository information into professional LinkedIn post drafts.

## Features

- Reads GitHub repository metadata, README content, and recent commits.
- Generates project launch, progress, technical, and learning post drafts.
- Detects common technology topics and creates hashtags.
- Lets you edit the generated draft.
- Copies the draft to the clipboard.
- Opens LinkedIn for manual review and publishing.
- Stores the last 50 generated drafts locally.
- Requires no LinkedIn API key and no LinkedIn credentials.

## Important

LinkedIn prohibits third-party software that automates actions such as posting, commenting, liking, sharing, and messaging. This project therefore automates content preparation while leaving the final LinkedIn publication to the account owner.

## Run locally

Windows PowerShell:

    python -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    streamlit run app.py

Linux / macOS:

    python3 -m venv .venv
    source .venv/bin/activate
    pip  install -r requirements.txt
    streamlit run app.py


## Example
