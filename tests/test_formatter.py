"""Unit tests for TextFormatter — filler removal, capitalization, punctuation."""

from src.text.formatter import TextFormatter


def test_empty_input_returns_empty():
    assert TextFormatter().format("") == ""
    assert TextFormatter().format("   ") == ""


def test_capitalizes_first_letter():
    out = TextFormatter(remove_fillers=False).format("hello world")
    assert out.startswith("H")


def test_removes_basic_fillers():
    out = TextFormatter(remove_fillers=True).format("um so I uh think maybe")
    # The "um" and "uh" should be gone; meaning preserved
    assert "um" not in out.lower().split()
    assert "uh" not in out.lower().split()
    assert "think" in out.lower()


def test_filler_removal_can_be_disabled():
    out = TextFormatter(remove_fillers=False).format("um hello")
    assert "um" in out.lower()


def test_adds_period_when_missing():
    out = TextFormatter(remove_fillers=False).format("hello world")
    assert out.endswith(".")


def test_preserves_existing_terminal_punctuation():
    for ending in ("?", "!", "."):
        out = TextFormatter(remove_fillers=False).format(f"hello world{ending}")
        # Should not double up
        assert out.endswith(ending)
        assert not out.endswith(ending + ".")


def test_collapses_multiple_spaces():
    out = TextFormatter(remove_fillers=False).format("hello    there")
    assert "    " not in out
    assert "hello there" in out.lower()


def test_set_remove_fillers_toggle():
    f = TextFormatter(remove_fillers=True)
    out1 = f.format("um okay then")
    f.set_remove_fillers(False)
    out2 = f.format("um okay then")
    assert "um" not in out1.lower().split()
    assert "um" in out2.lower()
