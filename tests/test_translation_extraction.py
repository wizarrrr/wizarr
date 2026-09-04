from pathlib import Path

from babel.messages.extract import extract_from_dir
from babel.messages.frontend import parse_mapping_cfg

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_babel_config_extracts_default_wizard_steps():
    with (PROJECT_ROOT / "babel.cfg").open() as config_file:
        method_map, options_map = parse_mapping_cfg(config_file, "babel.cfg")

    extracted = list(
        extract_from_dir(
            PROJECT_ROOT,
            method_map=method_map,
            options_map=options_map,
        )
    )

    wizard_files = {
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "wizard_steps").rglob("*.md")
        if "_(" in path.read_text()
    }
    extracted_wizard_files = {
        Path(filename).as_posix()
        for filename, *_rest in extracted
        if Path(filename).as_posix().startswith("wizard_steps/")
    }

    assert wizard_files <= extracted_wizard_files
    assert any(
        Path(filename).as_posix() == "wizard_steps/plex/01_what_is.md" and message == "What is Plex?"
        for filename, _line, message, _comments, _context in extracted
    )
