from __future__ import annotations

from pathlib import Path

from agent_tools.tools.knowledge import get_topic
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
