"""Export/import round-tripping of the api_check config.

The one rule that matters here: the encrypted credential must never leave the
database. An exported step carries the whole gate configuration except the key,
and importing it produces a gate that is inert until an admin supplies one -
so a shared JSON file cannot lock anybody out against a stranger's endpoint.
"""

from app.extensions import db
from app.models import WizardStep
from app.services.ldap.encryption import encrypt_credential
from app.services.wizard_api_check.config import normalize
from app.services.wizard_export_import import WizardExportImportService
from tests.external.api_check.conftest import api_check_blob

CIPHERTEXT_MARKER = "sk-live-super-secret"


def gated_blob():
    return api_check_blob(
        "https://api.example.com/check",
        sign_requests=True,
        api_key_enc=encrypt_credential(CIPHERTEXT_MARKER),
        interval_seconds=25,
        expect_status=[200, 204],
        pending_message="Install the app",
    )


def make_gated_step(app, server_type="jellyfin"):
    with app.app_context():
        step = WizardStep(
            server_type=server_type,
            category="post_invite",
            position=0,
            title="Gated",
            markdown="# Gated\n\n{{ widget:api_check }}",
            api_check=gated_blob(),
        )
        db.session.add(step)
        db.session.commit()
        return step.id


class TestExport:
    def test_export_carries_the_configuration(self, app, session):
        make_gated_step(app)

        with app.app_context():
            export = WizardExportImportService().export_steps_by_server_type("jellyfin")
            blob = export.to_dict()["steps"][0]["api_check"]

        assert blob["enabled"] is True
        assert blob["url"] == "https://api.example.com/check"
        assert blob["interval_seconds"] == 25
        assert blob["expect_status"] == [200, 204]
        assert blob["pending_message"] == "Install the app"

    def test_export_never_contains_the_credential(self, app, session):
        import json

        make_gated_step(app)

        with app.app_context():
            export = WizardExportImportService().export_steps_by_server_type("jellyfin")
            serialised = json.dumps(export.to_dict())

        assert "api_key_enc" not in serialised
        assert CIPHERTEXT_MARKER not in serialised

    def test_export_reports_key_presence_without_the_key(self, app, session):
        make_gated_step(app)

        with app.app_context():
            export = WizardExportImportService().export_steps_by_server_type("jellyfin")
            blob = export.to_dict()["steps"][0]["api_check"]

        assert blob["has_api_key"] is True

    def test_ungated_steps_export_an_inert_config(self, app, session):
        with app.app_context():
            db.session.add(
                WizardStep(
                    server_type="jellyfin",
                    category="post_invite",
                    position=0,
                    title="Plain",
                    markdown="# Plain",
                )
            )
            db.session.commit()

            export = WizardExportImportService().export_steps_by_server_type("jellyfin")
            blob = export.to_dict()["steps"][0]["api_check"]

        assert blob["enabled"] is False


class TestImport:
    def test_import_restores_the_configuration(self, app, session):
        make_gated_step(app)

        with app.app_context():
            service = WizardExportImportService()
            payload = service.export_steps_by_server_type("jellyfin").to_dict()
            WizardStep.query.delete()
            db.session.commit()

            result = service.import_data(payload, replace_existing=True)
            assert result.success, result.errors

            step = WizardStep.query.filter_by(server_type="jellyfin").first()
            cfg = normalize(step.api_check, category=step.category)

        assert cfg.enabled is True
        assert cfg.url == "https://api.example.com/check"
        assert cfg.interval_seconds == 25

    def test_an_imported_signed_gate_is_inert_without_a_key(self, app, session):
        make_gated_step(app)

        with app.app_context():
            service = WizardExportImportService()
            payload = service.export_steps_by_server_type("jellyfin").to_dict()
            WizardStep.query.delete()
            db.session.commit()
            service.import_data(payload, replace_existing=True)

            step = WizardStep.query.filter_by(server_type="jellyfin").first()
            cfg = normalize(step.api_check, category=step.category)

        assert cfg.api_key_enc == ""
        assert cfg.is_active is False, "an imported gate must not block until keyed"

    def test_a_hostile_payload_cannot_smuggle_a_credential(self, app, session):
        with app.app_context():
            payload = {
                "export_type": "steps",
                "server_type": "jellyfin",
                "steps": [
                    {
                        "server_type": "jellyfin",
                        "category": "post_invite",
                        "position": 0,
                        "title": "Hostile",
                        "markdown": "# x",
                        "api_check": {
                            "version": 1,
                            "enabled": True,
                            "url": "https://attacker.test/collect",
                            "api_key_enc": "injected-ciphertext",
                            "sign_requests": True,
                        },
                    }
                ],
            }
            WizardExportImportService().import_data(payload, replace_existing=True)

            step = WizardStep.query.filter_by(server_type="jellyfin").first()
            cfg = normalize(step.api_check, category=step.category)

        assert cfg.api_key_enc == ""
        assert cfg.is_active is False

    def test_import_tolerates_a_missing_api_check_key(self, app, session):
        with app.app_context():
            payload = {
                "export_type": "steps",
                "server_type": "jellyfin",
                "steps": [
                    {
                        "server_type": "jellyfin",
                        "category": "post_invite",
                        "position": 0,
                        "title": "Legacy export",
                        "markdown": "# x",
                    }
                ],
            }

            result = WizardExportImportService().import_data(
                payload, replace_existing=True
            )
            step = WizardStep.query.filter_by(server_type="jellyfin").first()
            cfg = normalize(step.api_check, category=step.category)

        assert result.success, result.errors
        assert cfg.enabled is False

    def test_import_rejects_a_malformed_api_check(self, app, session):
        with app.app_context():
            payload = {
                "export_type": "steps",
                "server_type": "jellyfin",
                "steps": [
                    {
                        "server_type": "jellyfin",
                        "category": "post_invite",
                        "position": 0,
                        "title": "Broken",
                        "markdown": "# x",
                        "api_check": "not-a-dict",
                    }
                ],
            }

            result = WizardExportImportService().import_data(
                payload, replace_existing=True
            )

        assert result.success is False
