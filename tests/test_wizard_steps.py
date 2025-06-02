import frontmatter

import pytest

from app.blueprints.wizard.routes import _eligible, _render, _steps


def test_eligible_with_requirements_met():
    post = frontmatter.Post('body', **{'requires': ['a', 'b']})
    cfg = {'a': True, 'b': True}
    assert _eligible(post, cfg)


def test_eligible_with_requirements_not_met():
    post = frontmatter.Post('body', **{'requires': ['a', 'b']})
    cfg = {'a': True, 'b': False}
    assert not _eligible(post, cfg)
    cfg = {}
    assert not _eligible(post, cfg)


def test_render_jinja_and_markdown(app):
    post = frontmatter.Post('{{ name }} **bold**')
    html = _render(post, {'name': 'Alice'})
    assert '<strong>bold</strong>' in html
    assert 'Alice' in html


def test_steps_filters_and_loads(tmp_path, monkeypatch):
    server_dir = tmp_path / 'myserver'
    server_dir.mkdir()
    # step requiring 'ok'
    f1 = server_dir / 'one.md'
    f1.write_text('''---
requires:
- ok
---
Step1''')
    # step without requirements
    f2 = server_dir / 'two.md'
    f2.write_text('''---
requires: []
---
Step2''')
    # point BASE_DIR to our temp path
    monkeypatch.setattr(
        'app.blueprints.wizard.routes.BASE_DIR', tmp_path
    )
    cfg = {'ok': True}
    steps = _steps('myserver', cfg)
    assert len(steps) == 2
    cfg = {'ok': False}
    steps = _steps('myserver', cfg)
    assert len(steps) == 1