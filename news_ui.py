from __future__ import annotations

import requests
import streamlit as st

from ai_news import fetch_gnews, format_news_for_ai, generate_with_openrouter


def render_news_section(
    openrouter_api_key: str,
    gnews_api_key: str,
    openrouter_model: str,
    save_history_fn,
) -> None:
    st.divider()
    st.header("AI Reasoning + Live News")

    ai_col, news_col = st.columns(2)
    with ai_col:
        st.metric(
            "Reasoning AI",
            "Configured" if openrouter_api_key else "API key missing",
        )
        st.caption(f"Model: {openrouter_model}")

    with news_col:
        st.metric(
            "News API",
            "Configured" if gnews_api_key else "API key missing",
        )
        st.caption("Provider: GNews")

    news_query = st.text_input(
        "News topic",
        value="India stock market OR NSE OR BSE",
        help="Enter a company, sector, ticker, or event.",
    )
    news_category = st.selectbox(
        "News category",
        ["business", "technology", "general", "world", "nation"],
        index=0,
        key="news_category",
    )

    if st.button("Fetch Latest News", use_container_width=True):
        if not gnews_api_key:
            st.error("Set GNEWS_API_KEY before fetching news.")
        else:
            try:
                st.session_state["news_articles"] = fetch_gnews(
                    gnews_api_key,
                    query=news_query,
                    category=news_category,
                    country="in",
                    language="en",
                    limit=10,
                )
            except (requests.RequestException, ValueError) as exc:
                st.error(f"News request failed: {exc}")

    news_articles = st.session_state.get("news_articles", [])

    if not news_articles:
        return
    st.subheader("News Feed")

    for article in news_articles:
        title = article.get("title", "Untitled")
        source = article.get("source", {}).get("name", "Unknown")
        published = article.get("publishedAt", "")
        url = article.get("url", "")
        st.markdown(f"**{title}**")
        st.caption(f"{source} | {published}")
        if url:
            st.link_button("Read article", url)

    if st.button("Analyze News with Reasoning AI", type="primary", use_container_width=True):
        if not openrouter_api_key:
            st.error("Set OPENROUTER_API_KEY before running AI analysis.")
            return

        news_context = format_news_for_ai(news_articles)
        system_prompt = (
            "You are a careful LinkedIn content analyst. "
            "Use only supplied news facts. Do not invent facts, quotes, prices, "
            "or events. Do not reveal private chain-of-thought or hidden reasoning. "
            "Mention uncertainty when the supplied data is incomplete."
        )

        user_prompt = (
            f"Create a professional LinkedIn post about: {news_query}.\n\n"
            "Summarize the most relevant 2-4 developments, explain why they matter "
            "to professionals, use only supplied facts, and end with a neutral "
            "takeway and 4-6 hashtags.\n\n\nNews:\n{news_context}"
        )

        try:
            ai_post = generate_with_openrouter(
                openrouter_api_key,
                system_prompt,
                user_prompt,
                model=openrouter_model,
                use_reasoning=True,
            )
            st.session_state["generated_post"] = ai_post
            save_history_fn(ai_post, news_query, "News AI Analysis")
        except (requests.RequestException, ValueError) as exc:
            st.error(
                f"AI request failed: {exc}"
            )
