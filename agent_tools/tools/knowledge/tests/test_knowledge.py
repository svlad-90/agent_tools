from __future__ import annotations

from pathlib import Path

from agent_tools.tools.knowledge import get_topic
from agent_tools.tools.knowledge import db_add
from agent_tools.tools.knowledge import db_get
from agent_tools.tools.knowledge import db_search
from agent_tools.tools.knowledge import db_topics
from agent_tools.tools.knowledge import init_db
from agent_tools.tools.knowledge import list_topics
from agent_tools.tools.knowledge import search_topics
from agent_tools.tools.knowledge import set_topic


class Args:
    def __init__(self, **kwargs: object) -> None:
        self.__dict__.update(kwargs)


def test_private_knowledge_is_separate_from_public(monkeypatch: object, tmp_path: Path, capsys: object) -> None:
    public_dir = tmp_path / "public"
    private_dir = tmp_path / "private"
    monkeypatch.setattr("agent_tools.tools.knowledge.PUBLIC_TOPICS_DIR", public_dir)
    monkeypatch.setenv("AGENT_TOOLS_PRIVATE_KNOWLEDGE_DIR", str(private_dir))

    assert set_topic(Args(scope="public", topic="agent_tools", finding="public finding")) == 0
    assert set_topic(Args(scope="private", topic="agent_tools", finding="private finding")) == 0

    assert (public_dir / "agent_tools.md").read_text(encoding="utf-8").count("finding") == 1
    assert (private_dir / "agent_tools.md").read_text(encoding="utf-8").count("finding") == 1

    assert get_topic(Args(scope="all", topic="agent_tools", with_header=False)) == 0
    output = capsys.readouterr().out
    assert "private finding" in output
    assert "public finding" not in output


def test_list_and_search_topics(monkeypatch: object, tmp_path: Path, capsys: object) -> None:
    public_dir = tmp_path / "public"
    private_dir = tmp_path / "private"
    public_dir.mkdir()
    private_dir.mkdir()
    (public_dir / "docker.md").write_text("# docker\n\n- build image\n", encoding="utf-8")
    (private_dir / "secrets.md").write_text("# secrets\n\n- token rotation\n", encoding="utf-8")
    monkeypatch.setattr("agent_tools.tools.knowledge.PUBLIC_TOPICS_DIR", public_dir)
    monkeypatch.setenv("AGENT_TOOLS_PRIVATE_KNOWLEDGE_DIR", str(private_dir))

    assert list_topics(Args(scope="all")) == 0
    listed = capsys.readouterr().out
    assert "public\tdocker" in listed
    assert "private\tsecrets" in listed

    assert search_topics(Args(scope="private", query="token")) == 0
    searched = capsys.readouterr().out
    assert "private:secrets:3" in searched


def test_sqlite_knowledge_db_add_search_get_and_topics(tmp_path: Path, capsys: object) -> None:
    db_path = tmp_path / "knowledge.sqlite3"

    assert init_db(Args(db=str(db_path))) == 0
    assert db_add(
        Args(
            db=str(db_path),
            scope="private",
            status="active",
            topic="agent_tools",
            text="repo_guard owns validation policy",
            source="test",
            tag=["validation", "validation", "repo"],
        )
    ) == 0
    added = capsys.readouterr().out
    assert "knowledge: added #1 private:agent_tools" in added

    assert db_search(Args(db=str(db_path), scope="private", status="active", query="policy")) == 0
    searched = capsys.readouterr().out
    assert "#1\tprivate:agent_tools\tactive\trepo_guard owns validation policy" in searched

    assert db_get(Args(db=str(db_path), finding_id=1)) == 0
    fetched = capsys.readouterr().out
    assert "tags:\trepo, validation" in fetched
    assert "source:\ttest" in fetched

    assert db_topics(Args(db=str(db_path), scope="all")) == 0
    topics = capsys.readouterr().out
    assert "private\tagent_tools\t1" in topics


def test_sqlite_knowledge_db_respects_scope_filter(tmp_path: Path, capsys: object) -> None:
    db_path = tmp_path / "knowledge.sqlite3"
    common = {"db": str(db_path), "status": "active", "topic": "agent_tools", "source": "", "tag": []}

    assert db_add(Args(**common, scope="public", text="public finding")) == 0
    assert db_add(Args(**common, scope="private", text="private finding")) == 0
    capsys.readouterr()

    assert db_search(Args(db=str(db_path), scope="public", status="active", query="finding")) == 0
    public_output = capsys.readouterr().out
    assert "public finding" in public_output
    assert "private finding" not in public_output
