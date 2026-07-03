from datetime import datetime, timezone

from pulseflow.filters import filter_jobs
from pulseflow.models import Job

NOW = datetime(2026, 7, 4, tzinfo=timezone.utc)


def job(title: str = "", description: str = "") -> Job:
    return Job(guid=f"g-{title}-{description}"[:64], title=title, description=description, fetched_at=NOW)


def matches(keywords: list[str], **fields) -> bool:
    return filter_jobs([job(**fields)], keywords) != []


def test_case_insensitive():
    assert matches(["SaaS"], title="Build a saas billing portal")
    assert matches(["iOS"], description="Native IOS app needed")


def test_word_boundaries_reject_substrings():
    assert not matches(["RAG"], title="Dragon logo design")          # 'rag' inside a word
    assert not matches(["iOS"], title="Kiosk software")              # 'ios' inside a word
    assert not matches(["MVP"], title="MVPX platform")               # trailing overrun


def test_dotted_keyword_next_js():
    assert matches(["Next.js"], title="Senior Next.js developer")
    assert matches(["Next.js"], title="Migrate site to next.js.")    # trailing punctuation ok
    assert not matches(["Next.js"], title="We use next.jsx here")    # overrun rejected
    assert not matches(["Next.js"], title="Nextjs developer")        # dot is literal, not 'any char'


def test_multiword_keyword_ai_agent():
    assert matches(["AI agent"], description="Build an AI agent for support")
    assert matches(["AI agent"], description="an AI  agent (double space)")
    assert matches(["AI agent"], description="an AI\nagent across a newline")
    assert not matches(["AI agent"], description="mai agents")       # left boundary holds


def test_any_match_across_title_and_description():
    assert matches(["LangGraph", "MVP"], title="No match here", description="ship an MVP fast")
    assert not matches(["LangGraph"], title="Django admin", description="CRUD forms")


def test_real_config_keywords_compile_and_run():
    from pulseflow.config import load_keywords_config

    keywords = load_keywords_config().keywords
    got = filter_jobs(
        [job(title="Agentic RAG pipeline with LangGraph"), job(title="Wordpress theme tweak")],
        keywords,
    )
    assert [j.title for j in got] == ["Agentic RAG pipeline with LangGraph"]
