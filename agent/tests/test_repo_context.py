"""
Unit tests for repo context builder, inspector, search, and editor.
"""

from pathlib import Path
from oasis_agent.repo_context.inspector import RepoInspector
from oasis_agent.repo_context.search import CodebaseSearcher
from oasis_agent.repo_context.editor import CodebaseEditor
from oasis_agent.models import IssueContext


def test_repo_inspector_and_tree(tmp_path: Path):
    # Setup sample python project
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("def hello(): pass\n", encoding="utf-8")

    inspector = RepoInspector(tmp_path)
    stack = inspector.detect_stack()

    assert "Python" in stack["languages"]
    assert "pyproject.toml" in stack["manifest_files"]
    assert stack["test_command"] == ["pytest"]

    tree = inspector.build_file_tree()
    assert "pyproject.toml" in tree
    assert "src/main.py" in tree


def test_codebase_search_keywords(tmp_path: Path):
    (tmp_path / "auth.py").write_text("def login_user(username, password): pass\n", encoding="utf-8")
    (tmp_path / "payment.py").write_text("def process_payment(amount): pass\n", encoding="utf-8")

    searcher = CodebaseSearcher(tmp_path)
    issue = IssueContext(
        repo_url="http://repo",
        repo_name="owner/repo",
        issue_number=5,
        title="Fix login_user token expiration",
        body="User authentication fails when token expires in login_user.",
    )

    keywords = searcher.extract_keywords(issue)
    assert "login_user" in keywords

    ranked = searcher.rank_relevant_files(keywords, top_k=2)
    assert len(ranked) > 0
    # auth.py should rank highest
    top_file, score = ranked[0]
    assert "auth.py" in top_file


def test_codebase_editor_and_rollback(tmp_path: Path):
    file_a = tmp_path / "calc.py"
    file_a.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    editor = CodebaseEditor(tmp_path)
    assert "calc.py" in editor.list_files()

    # Edit file
    diff = editor.edit_file("calc.py", "def add(a, b):\n    # fixed\n    return a + b\n")
    assert "+    # fixed" in diff

    # Create file
    editor.create_file("utils.py", "# new file\n")
    assert (tmp_path / "utils.py").exists()

    diff_summary = editor.compute_diff_summary()
    assert "calc.py" in diff_summary.files_changed
    assert "utils.py" in diff_summary.files_changed

    # Rollback
    editor.rollback_all()
    assert not (tmp_path / "utils.py").exists()
    assert editor.read_file("calc.py") == "def add(a, b):\n    return a + b\n"
