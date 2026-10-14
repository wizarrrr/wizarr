"""Enter on Settings > General saves the form.

The Create API Key button sits inside the settings form. A button with no type
is a submit button, and Enter submits a form through its first one, so Enter in a
text field opened the Create API Key dialog instead of saving. The button is now
type="button", so Enter reaches the real Save button.
"""

import re

from app.models import AdminAccount


def _general_page(client, session):
    admin = AdminAccount(username="testadmin")
    admin.set_password("TestPass123")
    session.add(admin)
    session.commit()
    client.post("/login", data={"username": "testadmin", "password": "TestPass123"})
    resp = client.get("/settings/general", headers={"HX-Request": "true"})
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def test_create_api_key_button_does_not_submit_the_form(client, session):
    html = _general_page(client, session)
    openings = re.findall(r"<button\b[^>]*>", html, re.S)
    create = [b for b in openings if 'hx-target="#create-api-key-modal"' in b]
    assert len(create) == 1
    assert 'type="button"' in create[0]
