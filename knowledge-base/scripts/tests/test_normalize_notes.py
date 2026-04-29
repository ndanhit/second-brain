"""
Tests for normalize_notes.py (User Story 1)

Run with: pytest knowledge-base/scripts/tests/test_normalize_notes.py -v
"""

import json
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure scripts/ is on the path so we can import normalize_notes
sys.path.insert(0, str(Path(__file__).parent.parent))

import normalize_notes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_claude_response(files: list) -> MagicMock:
    """Build a mock subprocess.run result that simulates a successful Claude response."""
    payload = {
        "is_error": False,
        "subtype": "success",
        "structured_output": {"files": files},
    }
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = json.dumps(payload)
    mock.stderr = ""
    return mock


def make_claude_error_response(subtype: str = "error_unknown") -> MagicMock:
    payload = {
        "is_error": True,
        "subtype": subtype,
        "structured_output": None,
    }
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = json.dumps(payload)
    mock.stderr = ""
    return mock


# ---------------------------------------------------------------------------
# T010: test_normalize_missing_file
# ---------------------------------------------------------------------------

def test_normalize_missing_file(tmp_path):
    """Script exits with code 1 when the notes file does not exist."""
    missing = tmp_path / "nonexistent.md"
    with pytest.raises(SystemExit) as exc_info:
        sys.argv = ["normalize_notes.py", str(missing)]
        normalize_notes.main()
    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# T011: test_normalize_empty_file
# ---------------------------------------------------------------------------

def test_normalize_empty_file(tmp_path, capsys):
    """Script exits with code 0 and prints 'No documents generated' for empty notes."""
    empty_file = tmp_path / "empty.md"
    empty_file.write_text("", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        sys.argv = ["normalize_notes.py", str(empty_file)]
        normalize_notes.main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "No documents generated" in captured.out


# ---------------------------------------------------------------------------
# T012: test_normalize_writes_files
# ---------------------------------------------------------------------------

def test_normalize_writes_files(tmp_path):
    """
    Mock subprocess.run to return valid JSON with two files.
    Assert both files are written to the correct category folders.
    """
    notes_file = tmp_path / "notes" / "test-note.md"
    notes_file.parent.mkdir()
    notes_file.write_text("# Test note\n\nSome content.", encoding="utf-8")

    kb_root = tmp_path
    (kb_root / "2-areas" / "systems").mkdir(parents=True)
    (kb_root / "2-areas" / "architecture").mkdir(parents=True)

    two_files = [
        {"path": "2-areas/systems/my-service.md", "content": "---\ntitle: My Service\ntype: system\ntags: []\nupdated: 2026-04-07\n---\n# My Service\n"},
        {"path": "2-areas/architecture/my-pattern.md", "content": "---\ntitle: My Pattern\ntype: architecture\ntags: []\nupdated: 2026-04-07\n---\n# My Pattern\n"},
    ]

    mock_result = make_claude_response(two_files)

    with patch("subprocess.run", return_value=mock_result), \
         patch.object(Path, "parent", new_callable=lambda: property(lambda self: tmp_path if self == Path(normalize_notes.__file__) else self.parent)):
        # Patch kb_root determination inside main
        with patch("normalize_notes.Path") as MockPath:
            # We need a more targeted patch — patch write_document directly
            pass

    # Simpler approach: directly test write_document and call_claude independently,
    # then test the full flow by patching call_claude
    written = []

    def fake_write(kb_r, path, content, overwrite, note_path):
        written.append(path)
        full = kb_root / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        return "created"

    with patch("subprocess.run", return_value=mock_result), \
         patch("normalize_notes.write_document", side_effect=fake_write):
        # Patch __file__ to control kb_root
        original_file = normalize_notes.__file__
        try:
            normalize_notes.__file__ = str(kb_root / "scripts" / "normalize_notes.py")
            sys.argv = ["normalize_notes.py", str(notes_file)]
            try:
                normalize_notes.main()
            except SystemExit as e:
                assert e.code == 0 or e.code is None
        finally:
            normalize_notes.__file__ = original_file

    assert "2-areas/systems/my-service.md" in written
    assert "2-areas/architecture/my-pattern.md" in written


# ---------------------------------------------------------------------------
# T013: test_normalize_collision_merge
# ---------------------------------------------------------------------------

@patch("normalize_notes._run_claude_json")
def test_normalize_collision_merge(mock_run, tmp_path):
    """
    When a target file already exists and overwrite=False,
    the Auto-Merge logic is triggered via _run_claude_json.
    """
    existing_content = "original content"
    target = tmp_path / "2-areas" / "systems" / "my-service.md"
    target.parent.mkdir(parents=True)
    target.write_text(existing_content, encoding="utf-8")

    mock_run.return_value = {"merged_content": "successfully merged content"}

    status = normalize_notes.write_document(
        tmp_path, "2-areas/systems/my-service.md", "new content", overwrite=False, note_path_str="notes/test-note.md"
    )

    assert status == "merged"
    assert target.read_text(encoding="utf-8") == "successfully merged content"
    
    # Verify the merge prompt was sent with the correct schema
    mock_run.assert_called_once()
    prompt_used, schema_used = mock_run.call_args[0]
    assert "EXISTING knowledge base document" in prompt_used
    assert "original content" in prompt_used
    assert "new content" in prompt_used
    assert schema_used == normalize_notes.MERGE_SCHEMA


# ---------------------------------------------------------------------------
# T014: test_normalize_collision_overwrite_flag
# ---------------------------------------------------------------------------

@patch("normalize_notes._run_claude_json")
def test_normalize_collision_overwrite_flag(mock_run, tmp_path):
    """
    When overwrite=True is passed, existing files are overwritten without AI merging.
    """
    target = tmp_path / "2-areas" / "systems" / "my-service.md"
    target.parent.mkdir(parents=True)
    target.write_text("original content", encoding="utf-8")

    status = normalize_notes.write_document(
        tmp_path, "2-areas/systems/my-service.md", "new content", overwrite=True, note_path_str="notes/test.md"
    )

    assert status == "overwritten"
    assert target.read_text(encoding="utf-8") == "new content"
    # Ensure AI merge was not called
    mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# T015: test_normalize_claude_error
# ---------------------------------------------------------------------------

def test_normalize_claude_error(tmp_path, capsys):
    """
    When subprocess returns non-zero returncode, script exits with code 1.
    """
    notes_file = tmp_path / "notes" / "test-note.md"
    notes_file.parent.mkdir()
    notes_file.write_text("# Note\n\nContent.", encoding="utf-8")

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "claude: command error"
    mock_result.stdout = ""

    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["normalize_notes.py", str(notes_file)]
            normalize_notes.main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error" in captured.err


# ---------------------------------------------------------------------------
# T016: test_normalize_path_traversal_rejected
# ---------------------------------------------------------------------------

def test_normalize_path_traversal_rejected():
    """
    validate_output_path rejects path traversal and non-allowed categories.
    """
    # Path traversal attempts
    assert normalize_notes.validate_output_path("../../etc/passwd") is False
    assert normalize_notes.validate_output_path("1-projects/../../etc/passwd") is False
    assert normalize_notes.validate_output_path("../1-projects/file.md") is False

    # Absolute path
    assert normalize_notes.validate_output_path("/etc/passwd") is False

    # Disallowed category
    assert normalize_notes.validate_output_path("adr/my-decision.md") is False
    assert normalize_notes.validate_output_path("glossary/term.md") is False

    # No category (just a filename)
    assert normalize_notes.validate_output_path("file.md") is False

    # Valid paths
    assert normalize_notes.validate_output_path("2-areas/systems/payment-service.md") is True
    assert normalize_notes.validate_output_path("2-areas/architecture/retry-pattern.md") is True
    assert normalize_notes.validate_output_path("3-resources/playbooks/debug-payment.md") is True

    # Non-.md extension
    assert normalize_notes.validate_output_path("2-areas/systems/file.txt") is False
