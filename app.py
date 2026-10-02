from __future__ import annotations

import json
import os

from news_ui import render_news_section
from ai_news import fetch_gnews, generate_with_openrouter
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

    render_news_section(
        OPENROUTER_API_KEY,
        GNEWS_API_KEY,
        OPENROUTER_MODEL,
        save_history,
    )

    st.divider()
    st.header("Trending Post + Connection Comment Assistant")

    trend_tab, comment_tab = st.tabs(["Trending Topic Post", "Connection Comment"])

    with trend_tab:
        st.caption(
            "Build a post from current news trends. This is news-based trend discovery, "
            "not LinkedIn feed scraping."
        )
        trend_region = st.selectbox(
            "Trend market",
            ["India", "Global", "Technology", "Business"],
            key="trend_region",
        )

        if st.button(
            "Discover Trending Topics",
            type="primary",
            use_container_width=True,
        ):
            if not GNEWS_API_KEY:
                st.error("Set GNEWS_API_KEY before discovering trends.")
            elif not OPENROUTER_API_KEY:
                st.error("Set OPENROUTER_API_KEY before generating the trend post.")
            else:
                queries = {
                    "India": "India technology OR business OR AI OR stock market",
                    "Global": "technology OR AI OR business OR markets",
                    "Technology": "artificial intelligence OR software OR cloud OR cybersecurity",
                    "Business": "business OR startups OR finance OR markets",
                }
                try:
                    trend_articles = fetch_gnews(
                        GNEWS_API_KEY,
                        query=queries[trend_region],
                        country="in" if trend_region == "India" else "us",
                        language="en",
                        limit=10,
                    )
                    if not trend_articles:
                        st.warning("No trend articles were returned.")
                    else:
                        context = "\n\n".join(
                            f"{i}. {a.get('title', '')} | "
                            f"{a.get('source', {}).get('name', 'Unknown')} | "
                            f"{a.get('publishedAt', '')} | "
                            f"{a.get('description', '')} | "
                            f"{a.get('url', '')}"
                            for i, a in enumerate(trend_articles, start=1)
                        )
                        trend_prompt = (
                            "Create one professional LinkedIn post based only on the supplied news. "
                            "Identify the strongest current theme, explain 2-3 concrete developments, "
                            "add one practical takeaway for professionals, avoid unsupported claims, "
                            "and finish with 4-6 concise hashtags. Do not mention hidden reasoning."
                        )
                        trend_user = (
                            f"Region/theme: {trend_region}\n\n"
                            f"Current news:\n{context}"
                        )
                        trend_post = generate_with_openrouter(
                            OPENROUTER_API_KEY,
                            trend_prompt,
                            trend_user,
                            model=OPENROUTER_MODEL,
                            use_reasoning=True,
                        )
                        st.session_state["generated_post"] = trend_post
                        save_history(
                            trend_post,
                            f"trending:{trend_region}",
                            "Trending Topic Post",
                        )
                except (requests.RequestException, ValueError) as exc:
                    st.error(f"Trending post generation failed: {exc}")

    with comment_tab:
        st.caption(
            "Builder-style LinkedIn comment: specific observation -> your professional/technical insight "
            "-> practical building angle -> one genuine question. Review and paste manually."
        )

        connection_post = st.text_area(
            "Connection post text",
            height=220,
            placeholder="Paste the LinkedIn post text here...",
            key="connection_post",
        )

        poster_context = st.text_area(
            "Poster context (optional)",
            height=120,
            placeholder=(
                "For a post with a poster/image, add the visible headline, key points, "
                "or a short description. The AI will use only this supplied context."
            ),
            key="poster_context",
        )

        comment_goal = st.selectbox(
            "Comment approach",
            [
                "Builder Insight + Real Question",
                "Technical Builder + Real Question",
                "Professional Learning + Real Question",
                "Supportive + Practical Question",
            ],
            key="comment_goal",
        )

        st.markdown(
            "**Your comment structure:** "
            "1) reference one specific point, "
            "2) add a useful builder/engineering perspective, "
            "3) connect it to implementation or real-world impact, "
            "4) end with one answerable question."
        )

        if st.button(
            "Generate Comment",
            type="primary",
            use_container_width=True,
        ):
            if not connection_post.strip():
                st.warning("Paste the connection's post text first.")
            elif not OPENROUTER_API_KEY:
                st.error("Set OPENROUTER_API_KEY before generating a comment.")
            else:
                comment_system = (
                    "Write a professional LinkedIn comment in the user's builder-oriented style. "
                    "The goal is to sound like someone who is actively learning, building, testing, "
                    "and thinking about real-world implementation. "
                    "Use this exact structure: "
                    "(1) mention one specific idea from the post, "
                    "(2) add one original but evidence-grounded professional or technical observation, "
                    "(3) add a practical builder angle such as implementation, trade-offs, adoption, "
                    "reliability, scalability, or user impact, depending on the post, "
                    "(4) end with ONE genuine, specific question that invites a useful answer. "
                    "The question must not be generic and must connect directly to the post. "
                    "Keep it natural, concise, and human: normally 3-5 sentences and about 50-90 words. "
                    "Do not use empty praise such as 'Great post' or 'Amazing'. "
                    "Do not repeat the post, invent personal experience, invent facts, or claim the user "
                    "did something they did not provide. Do not use hashtags or emojis. "
                    "When poster context is supplied, refer to a concrete detail from it, but never invent "
                    "visual details that are not supplied. Do not reveal hidden reasoning."
                )
                comment_user = (
                    f"Comment approach: {comment_goal}\n\n"
                    f"LinkedIn post:\n{connection_post.strip()}\n\n"
                    f"Poster context:\n{poster_context.strip() or 'Not supplied'}"
                )
                try:
                    comment = generate_with_openrouter(
                        OPENROUTER_API_KEY,
                        comment_system,
                        comment_user,
                        model=OPENROUTER_MODEL,
                        use_reasoning=True,
                    )
                    st.session_state["generated_comment"] = comment.strip()
                    save_history(
                        comment.strip(),
                        "connection-post",
                        "Connection Comment",
                    )
                except (requests.RequestException, ValueError) as exc:
                    st.error(f"Comment generation failed: {exc}")

        generated_comment = st.session_state.get("generated_comment", "")
        if generated_comment:
            st.subheader("Generated Comment")
            edited_comment = st.text_area(
                "Review and edit",
                value=generated_comment,
                height=180,
                key="generated_comment_editor",
            )
            st.session_state["generated_comment"] = edited_comment
            cc1, cc2 = st.columns(2)
            if cc1.button("Copy Comment", use_container_width=True):
                try:
                    pyperclip.copy(edited_comment)
                    st.success("Comment copied to clipboard.")
                except pyperclip.PyperclipException:
                    st.warning("Clipboard access is unavailable. Copy manually.")
            cc2.link_button(
                "Open LinkedIn",
                "https://www.linkedin.com/feed/",
                use_container_width=True,
            )

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
