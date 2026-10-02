from __future__ import annotations

import json
import os

from ai_news import fetch_gnews, format_news_for_ai, generate_with_openrouter
import re
from datetime import datetime, timezone
from pathlib import Path

import pyperclip
import requests
import streamlit as st

GITHUB_API = "https://api.github.com"
HISTORY_DIR = Path("data/history")
HISTORY_FILE = HISTORY_DIR / "posts.json"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip() or "openrouter/free"

try:
    OPENROUTER_API_KEY = OPENROUTER_API_KEY or str(
        st.secrets.get("OPENROUTER_API_KEY", "")
    ).strip()
    GNEWS_API_KEY = GNEWS_API_KEY or str(
        st.secrets.get("GNEWS_API_KEY", "")
    ).strip()
    OPENROUTER_MODEL = str(
        st.secrets.get("OPENROUTER_MODEL", OPENROUTER_MODEL)
    ).strip() or OPENROUTER_MODEL
except Exception:
    pass

st.set_page_config(
    page_title="LinkedIn Content Automation",
    page_icon="LI",
    layout="wide",
)


def github_request(path: str) -> dict | list:
    response = requests.get(
        f"{GITHUB_API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300)
def get_repository(repo_full_name: str) -> dict:
    return github_request(f"/repos/{repo_full_name}")


@st.cache_data(ttl=300)
def get_readme(repo_full_name: str) -> str:
    response = requests.get(
        f"https://raw.githubusercontent.com/{repo_full_name}/HEAD/README.md",
        timeout=20,
    )
    if response.status_code == 404:
        return ""
    response.raise_for_status()
    return response.text


@st.cache_data(ttl=300)
def get_commits(repo_full_name: str) -> list[dict]:
    data = github_request(f"/repos/{repo_full_name}/commits?per_page=5")
    return data if isinstance(data, list) else []


def clean_markdown(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"!\[[^]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def infer_topics(repo: dict, readme: str) -> list[str]:
    text = f"{repo.get('name', '')} {repo.get('description', '')} {readme}".lower()

    mapping = {
        "python": "Python",
        "sql": "SQL",
        "fastapi": "FastAPI",
        "streamlit": "Streamlit",
        "react": "React",
        "machine learning": "Machine Learning",
        "fintech": "FinTech",
        "stock market": "Stock Market",
        "data engineering": "Data Engineering",
        "docker": "Docker",
        "mongodb": "MongoDB",
        "postgres": "PostgreSQL",
        "redis": "Redis",
        "ai": "AI",
    }
    return [
        label
        for needle, label in mapping.items()
        if needle in text
    ][:6]


def build_post(
    repo: dict,
    readme: str,
    commits: list[dict],
    post_type: str,
    tone: str,
) -> str:
    name = repo.get("name", "GitHub project")
    description = repo.get("description") or "A project I am building and improving."
    url = repo.get("html_url", "")
    topics = infer_topics(repo, readme)
    overview = clean_markdown(readme)[:500].replace("\n", " ").strip()

    recent_commit = ""
    if commits:
        recent_commit = (
            commits[0]
            .get("commit", {})
            .get("message", "")
            .splitlines()[0]
        )

    hashtags = [
        "GitHub",
        "BuildInPublic",
        "SoftwareDevelopment",
        "DataEngineering",
    ]
    hashtags.extend(topic.replace(" ", "") for topic in topics)
    hashtags = list(dict.fromkeys(hashtags))[:8]
    tags = " ".join(f"#{tag}" for tag in hashtags)

    if post_type == "Project Launch":
        hook = f"Building and sharing my latest project: {name}"
        body = (
            f"{description}\n\n"
            "The project focuses on practical engineering rather than just a demo. "
            "I am building it iteratively, testing the workflow, and documenting the work in GitHub."
        )
    elif post_type == "Progress Update":
        hook = f"Project update: {name}"
        body = (
            f"I am continuing to improve {name}.\n\n"
            "The current focus is making the workflow cleaner, easier to use, and more reliable."
        )
        if recent_commit:
            body += f"\n\nLatest GitHub update: {recent_commit}."
    elif post_type == "Technical":
        hook = f"What I am building with {name}"
        body = (
            f"The project is an engineering exercise around {description.lower()} "
            "It is helping me practice designing a useful workflow from input to a repeatable output."
        )
    else:
        hook = f"Learning through {name}"
        body = (
            f"Working on {name} is giving me hands-on practice with real software development. "
            "The goal is to turn concepts into a usable project and keep improving it through implementation."
        )

    extra = f"\n\nProject link: {url}"
    if overview and tone == "Technical":
        extra += f"\n\nREADME snapshot: {overview}"

    return f"{hook}\n\n{body}{extra}\n\n{tags}"


def load_history() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []

    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_history(post: str, repo: str, post_type: str) -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    history = load_history()
    history.insert(
        0,
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "repository": repo,
            "type": post_type,
            "content": post,
        },
    )
    HISTORY_FILE.write_text(
        json.dumps(history[:50], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> None:
    st.title("LinkedIn Content Automation")
    st.caption(
        "GitHub project -> professional LinkedIn draft. "
        "No LinkedIn API key required."
    )

    with st.sidebar:
        st.header("Project")
        repo_input = st.text_input(
            "GitHub repository",
            value="mr-Arun-2006/linkedin_Automation",
            placeholder="owner/repository",
        )
        post_type = st.selectbox(
            "Post type",
            [
                "Project Launch",
                "Progress Update",
                "Technical",
                "Learning",
            ],
        )
        tone = st.selectbox(
            "Tone",
            ["Professional", "Technical"],
        )
 
    repo_name = repo_input.strip()

    if not re.fullmatch(
        r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
        repo_name,
    ):
        st.error("Enter the repository as owner/name.")
        return
 
    try:
        repo = get_repository(repo_name)
        readme = get_readme(repo_name)
        commits = get_commits(repo_name)
    except requests.RequestException as exc:
        st.error(f"GitHub request failed: {exc}")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Stars", repo.get("stargazers_count", 0))
    col2.metric("Forks", repo.get("forks_count", 0))
    col3.metric("Language", repo.get("language") or "N/A")

    st.subheader(repo.get("name", "Repository"))
    st.write(repo.get("description") or "No GitHub description is set.")

    if st.button(
        "Generate LinkedIn Post",
        type="primary",
        use_container_width=True,
    ):
        post = build_post(
            repo,
            readme,
            commits,
            post_type,
            tone,
        )
        st.session_state["generated_post"] = post
        save_history(post, repo_name, post_type)

    post = st.session_state.get("generated_post", "")

    if post:
        st.subheader("Generated Post")
        edited = st.text_area(
            "Review and edit before publishing",
            value=post,
            height=350,
        )
        st.session_state["generated_post"] = edited

        col_a, col_b = st.columns(2)

        if col_a.button(
            "Copy to Clipboard",
            use_container_width=True,
        ):
            try:
                pyperclip.copy(edited)
                st.success("Copied to clipboard.")
            except pyperclip.PyperclipException:
                st.warning(
                    "Clipboard access is unavailable. Copy the text manually."
                )

        col_b.link_button(
            "Open LinkedIn",
            "https://www.linkedin.com/feed/?shareActive=true",
            use_container_width=True,
        )

        st.info(
            "Publishing remains manual: review the draft, paste it into "
            "LinkedIn, and click Post yourself."
        )

    st.diveder()
    st.header("AI Reasoning + Live News")

    ai_col, news_col = st.columns(2)
    with ai_col:
        st.metric(
            "Reasoning AI",
            "Configured" if OPENROUTER_API_KEY else "API key missing",
        )
        st.caption(f"Model: {OPENROUTER_MODEL}")
    with news_col:
        st.metric(
            "News API",
            "Configured" if GNEWS_API_KEY else "API key missing",
        )
        st.caption("Provider: GNews")

    news_query = st.text_input(
        "News topic",
        value="India stock market OR NSE OR BSE",
        help="Enter a company, sector, ticker, or event. Leave it broad for market news.",
    )
    news_category = st.selectbox(
        "News category",
        ["business", "technology", "general", "world", "nation"],
        index=0,
         key="news_category"
    )

    if st.button("Fetch Latest News", use_container_width=True):
        if not GNEWS_API_KEY :
            st.error("Set{GNEWS_API_KEY} before fetching news.")
        else:
             try:
                st.session_state["comrit"] = fetch_gnews(GNEWS_API_KEY, query=news_query, category=news_category, country="in", language="en", limit=10)
             except (requests.RequestException, ValueError) as exc:
                st.error((f"News request failed: {exc}")

    news_articles = st.session_state.get("commit", [])
    if news_articles:
        st.subheader("News Feed")
        for article in news_articles:
            st.markdown(f"**{article.get('title', 'Untitled')}* ")
            st.caption(f"article.get('source', {}).get('name', 'Unknown')}  | {article.get('publishedAt', '')}")
            url = article.get("url", "")
            if url:
                st.link_button("Read article", url)

        if st.button("Analyze News with Reasoning AI", type="primary", use_container_width=True):
            if not OPENROUTER_API_KEY: st.error("Set OPENROUTER_API_KEY before running AI analysis.")
            else:
                news_context = format_news_for_ai(news_articles)
                system_prompt = "You are a careful LinkedIn content analyst. Use only supplied news facts. Do not invent facts, quotes, prices, or events. Do not reveal private chain-of-thought. Mention uncertainty when data is incomplete."
                user_prompt = f"Create a professional LinkedIn post about : {news_query}.\n\nList the most relevant 2-4 developments, explain why they matter, use only supplied facts, and end with 4-6 hashtags.\n\nNews:\n{news_context}"
                try:
                    ai_post = generate_with_openrouter(OPENROUTER_API_KEY, system_prompt, user_prompt, model=OPENROUTER_MODEL, use_reasoning=True)
                    st.session_state["generated_post"] = ai_post
                    save_history(ai_post, news_query, "News AI Analysis")
                except (requests.RequestException, ValueError) as exc:
                    st.error(!"AI request failed: {exc}")

    with st.expander("Recent commits"):
        if not commits:
            st.write("No commits found.")

        for commit in commits:
            message = (
                commit.get("commit", {})
                .get("message", "")
                .splitlines()[0]
            )
            sha = commit.get("sha", "")[:7]
            st.write(f"{sha} - {message}")

    with st.expander("Post history"):
        history = load_history()

        if not history:
            st.write("No generated posts yet.")

        for item in history[:10]:
            st.caption(
                f"{item['created_at']} | "
                f"{item['repository']} | "
                f"{item['type']}"
            )
            st.code(item["content"])


if __name__ == "__main__":
    main()
