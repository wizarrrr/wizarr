"""Wizard export/import service for managing wizard steps in JSON format."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.extensions import db
from app.models import WizardBundle, WizardBundleStep, WizardStep


@dataclass(frozen=True)
class WizardStepDTO:
    """Data transfer object for wizard step export/import."""

    server_type: str
    position: int
    title: str | None
    markdown: str
    requires: list[str] | None
    require_interaction: bool = False
    category: str = "post_invite"  # Category field for pre/post-invite distinction
    interactions: dict[str, Any] | None = None  # Modular interaction configuration

    @classmethod
    def from_model(cls, step: WizardStep) -> WizardStepDTO:
        """Create DTO from WizardStep model."""
        return cls(
            server_type=step.server_type,
            position=step.position,
            title=step.title,
            markdown=step.markdown,
            requires=step.requires or [],
            require_interaction=bool(getattr(step, "require_interaction", False)),
            category=getattr(step, "category", "post_invite"),
            interactions=getattr(step, "interactions", None),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "server_type": self.server_type,
            "position": self.position,
            "title": self.title,
            "markdown": self.markdown,
            "requires": self.requires or [],
            "require_interaction": bool(self.require_interaction),
            "category": self.category,
        }
        # Only include interactions if present (backward compatible)
        if self.interactions:
            result["interactions"] = self.interactions
        return result


@dataclass(frozen=True)
class WizardBundleDTO:
    """Data transfer object for wizard bundle export/import."""

    name: str
    description: str | None
    steps: list[WizardStepDTO]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps],
        }


@dataclass(frozen=True)
class WizardExportDTO:
    """Data transfer object for wizard export response."""

    steps: list[WizardStepDTO] | None = None
    bundle: WizardBundleDTO | None = None
    export_date: str = ""
    total_count: int = 0
    server_types: list[str] = field(default_factory=list)
    export_type: str = "steps"  # "steps" or "bundle"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "export_date": self.export_date,
            "export_type": self.export_type,
        }

        if self.export_type == "bundle" and self.bundle:
            result["bundle"] = self.bundle.to_dict()
            result["total_count"] = len(self.bundle.steps)
        elif self.export_type == "steps" and self.steps:
            result["steps"] = [step.to_dict() for step in self.steps]
            result["total_count"] = self.total_count
            result["server_types"] = self.server_types or []

        return result


@dataclass(frozen=True)
class WizardImportResult:
    """Data transfer object for wizard import results."""

    success: bool
    message: str
    imported_count: int
    skipped_count: int
    updated_count: int
    errors: list[str]


class WizardExportImportService:
    """Service for exporting and importing wizard steps."""

    def __init__(self, session: Session | None = None):
        """Initialize service with optional database session."""
        self.session = session or db.session
        self.logger = logging.getLogger(__name__)

    def export_steps_by_server_type(self, server_type: str) -> WizardExportDTO:
        """Export wizard steps for a specific server type.

        Args:
            server_type: The server type to export steps for

        Returns:
            WizardExportDTO with filtered steps and metadata
        """
        steps = (
            self.session.query(WizardStep)
            .filter(WizardStep.server_type == server_type)
            .order_by(WizardStep.position)
            .all()
        )

        step_dtos = [WizardStepDTO.from_model(step) for step in steps]

        return WizardExportDTO(
            steps=step_dtos,
            export_date=datetime.now(UTC).isoformat(),
            total_count=len(step_dtos),
            server_types=[server_type] if step_dtos else [],
            export_type="steps",
        )

    def export_bundle(self, bundle_id: int) -> WizardExportDTO:
        """Export a wizard bundle with its steps.

        Args:
            bundle_id: ID of the bundle to export

        Returns:
            WizardExportDTO with bundle data
        """
        bundle = (
            self.session.query(WizardBundle)
            .filter(WizardBundle.id == bundle_id)
            .first()
        )
        if not bundle:
            raise ValueError(f"Bundle with ID {bundle_id} not found")

        # Get bundle steps in order
        bundle_steps = (
            self.session.query(WizardBundleStep, WizardStep)
            .join(WizardStep, WizardBundleStep.step_id == WizardStep.id)
            .filter(WizardBundleStep.bundle_id == bundle_id)
            .order_by(WizardBundleStep.position)
            .all()
        )

        step_dtos = [
            WizardStepDTO.from_model(wizard_step) for _, wizard_step in bundle_steps
        ]

        bundle_dto = WizardBundleDTO(
            name=bundle.name, description=bundle.description, steps=step_dtos
        )

        return WizardExportDTO(
            bundle=bundle_dto,
            export_date=datetime.now(UTC).isoformat(),
            export_type="bundle",
        )

    def validate_import_data(self, data: dict[str, Any]) -> list[str]:
        """Validate JSON import data structure.

        Args:
            data: JSON data to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check export type
        export_type = data.get("export_type", "steps")
        if export_type not in ["steps", "bundle"]:
            errors.append("Invalid export_type, must be 'steps' or 'bundle'")
            return errors

        if export_type == "bundle":
            return self._validate_bundle_data(data)
        return self._validate_steps_data(data)

    def _validate_steps_data(self, data: dict[str, Any]) -> list[str]:
        """Validate steps export data."""
        errors = []

        # Check required top-level keys
        if "steps" not in data:
            errors.append("Missing required field: 'steps'")
            return errors

        if not isinstance(data["steps"], list):
            errors.append("Field 'steps' must be a list")
            return errors

        # Validate each step
        for i, step in enumerate(data["steps"]):
            errors.extend(self._validate_step_data(step, i))

        return errors

    def _validate_bundle_data(self, data: dict[str, Any]) -> list[str]:
        """Validate bundle export data."""
        errors = []

        # Check required top-level keys
        if "bundle" not in data:
            errors.append("Missing required field: 'bundle'")
            return errors

        bundle = data["bundle"]
        if not isinstance(bundle, dict):
            errors.append("Field 'bundle' must be an object")
            return errors

        # Validate bundle fields
        if "name" not in bundle:
            errors.append("Bundle: missing required field 'name'")
        elif not isinstance(bundle["name"], str):
            errors.append("Bundle: 'name' must be a string")

        if (
            "description" in bundle
            and bundle["description"] is not None
            and not isinstance(bundle["description"], str)
        ):
            errors.append("Bundle: 'description' must be a string or null")

        if "steps" not in bundle:
            errors.append("Bundle: missing required field 'steps'")
            return errors

        if not isinstance(bundle["steps"], list):
            errors.append("Bundle: 'steps' must be a list")
            return errors

        # Validate each step in bundle
        for i, step in enumerate(bundle["steps"]):
            errors.extend(self._validate_step_data(step, i))

        return errors

    def _validate_step_data(self, step: dict[str, Any], index: int) -> list[str]:
        """Validate individual step data."""
        errors = []

        if not isinstance(step, dict):
            errors.append(f"Step {index}: must be an object")
            return errors

        # Check required fields
        required_fields = ["server_type", "position", "markdown"]
        errors.extend(
            f"Step {index}: missing required field '{required_field}'"
            for required_field in required_fields
            if required_field not in step
        )

        # Validate field types
        if "server_type" in step and not isinstance(step["server_type"], str):
            errors.append(f"Step {index}: 'server_type' must be a string")

        if "position" in step and not isinstance(step["position"], int):
            errors.append(f"Step {index}: 'position' must be an integer")

        if "markdown" in step and not isinstance(step["markdown"], str):
            errors.append(f"Step {index}: 'markdown' must be a string")

        if (
            "title" in step
            and step["title"] is not None
            and not isinstance(step["title"], str)
        ):
            errors.append(f"Step {index}: 'title' must be a string or null")

        if "requires" in step and step["requires"] is not None:
            if not isinstance(step["requires"], list):
                errors.append(f"Step {index}: 'requires' must be a list or null")
            elif not all(isinstance(req, str) for req in step["requires"]):
                errors.append(f"Step {index}: all items in 'requires' must be strings")

        if (
            "require_interaction" in step
            and step["require_interaction"] is not None
            and not isinstance(step["require_interaction"], bool)
        ):
            errors.append(f"Step {index}: 'require_interaction' must be a boolean")

        # Validate category field (optional, defaults to 'post_invite')
        if "category" in step and step["category"] is not None:
            if not isinstance(step["category"], str):
                errors.append(f"Step {index}: 'category' must be a string")
            elif step["category"] not in ["pre_invite", "post_invite"]:
                errors.append(
                    f"Step {index}: 'category' must be 'pre_invite' or 'post_invite'"
                )

        # Validate interactions field (optional JSON object)
        if "interactions" in step and step["interactions"] is not None:
            if not isinstance(step["interactions"], dict):
                errors.append(f"Step {index}: 'interactions' must be an object or null")
            else:
                errors.extend(
                    self._validate_interactions_data(step["interactions"], index)
                )

        return errors

    def _validate_interactions_data(
        self, interactions: dict[str, Any], step_index: int
    ) -> list[str]:
        """Validate interactions configuration structure."""
        errors = []
        valid_interaction_types = ["click", "time", "tos", "text_input", "quiz"]

        for key in interactions:
            if key not in valid_interaction_types:
                errors.append(f"Step {step_index}: unknown interaction type '{key}'")
                continue

            interaction = interactions[key]
            if not isinstance(interaction, dict):
                errors.append(
                    f"Step {step_index}: interaction '{key}' must be an object"
                )
                continue

            # Validate enabled field
            if "enabled" not in interaction:
                errors.append(
                    f"Step {step_index}: interaction '{key}' missing 'enabled' field"
                )
            elif not isinstance(interaction["enabled"], bool):
                errors.append(
                    f"Step {step_index}: interaction '{key}.enabled' must be a boolean"
                )

            # Type-specific validation
            if key == "time" and "duration_seconds" in interaction:
                duration = interaction["duration_seconds"]
                if not isinstance(duration, int) or duration < 1:
                    errors.append(
                        f"Step {step_index}: 'time.duration_seconds' must be a positive integer"
                    )

            if key == "quiz" and "questions" in interaction:
                questions = interaction["questions"]
                if not isinstance(questions, list):
                    errors.append(f"Step {step_index}: 'quiz.questions' must be a list")
                elif len(questions) == 0 and interaction.get("enabled", False):
                    errors.append(
                        f"Step {step_index}: 'quiz.questions' cannot be empty when enabled"
                    )

        return errors

    def import_data(
        self, data: dict[str, Any], replace_existing: bool = False
    ) -> WizardImportResult:
        """Import wizard data (steps or bundle) from JSON data.

        Args:
            data: JSON data containing wizard steps or bundle
            replace_existing: If True, replace existing data; if False, merge with existing

        Returns:
            WizardImportResult with operation results
        """
        # Validate input data
        validation_errors = self.validate_import_data(data)
        if validation_errors:
            return WizardImportResult(
                success=False,
                message="Validation failed",
                imported_count=0,
                skipped_count=0,
                updated_count=0,
                errors=validation_errors,
            )

        export_type = data.get("export_type", "steps")

        if export_type == "bundle":
            return self._import_bundle(data, replace_existing)
        return self._import_steps(data, replace_existing)

    def _import_steps(
        self, data: dict[str, Any], replace_existing: bool
    ) -> WizardImportResult:
        """Import wizard steps from JSON data."""
        try:
            imported_count = 0
            skipped_count = 0
            updated_count = 0
            errors = []

            steps_data = data["steps"]

            if replace_existing:
                # Delete all existing steps for the server types being imported
                server_types = {step["server_type"] for step in steps_data}
                for server_type in server_types:
                    deleted_count = (
                        self.session.query(WizardStep)
                        .filter(WizardStep.server_type == server_type)
                        .delete()
                    )
                    self.logger.info(
                        f"Deleted {deleted_count} existing {server_type} steps for replacement import"
                    )

            # Group steps by server_type for position management
            steps_by_server = {}
            for step_data in steps_data:
                server_type = step_data["server_type"]
                if server_type not in steps_by_server:
                    steps_by_server[server_type] = []
                steps_by_server[server_type].append(step_data)

            # Process each server type
            for server_type, server_steps in steps_by_server.items():
                # Sort by position to maintain order
                server_steps.sort(key=lambda x: x["position"])

                if not replace_existing:
                    # For additive import, we need to handle position conflicts
                    existing_max_position = (
                        self.session.query(db.func.max(WizardStep.position))
                        .filter(WizardStep.server_type == server_type)
                        .scalar()
                    )
                    next_position = (existing_max_position or -1) + 1
                else:
                    next_position = 0

                # Import steps for this server type
                for step_data in server_steps:
                    try:
                        if not replace_existing:
                            # Check if step already exists at this position
                            existing_step = (
                                self.session.query(WizardStep)
                                .filter(
                                    and_(
                                        WizardStep.server_type == server_type,
                                        WizardStep.position == step_data["position"],
                                    )
                                )
                                .first()
                            )

                            if existing_step:
                                # Update existing step
                                existing_step.title = step_data.get("title")
                                existing_step.markdown = step_data["markdown"]
                                existing_step.requires = step_data.get("requires")
                                if "require_interaction" in step_data:
                                    existing_step.require_interaction = bool(
                                        step_data.get("require_interaction") or False
                                    )
                                # Update category with backward compatibility
                                existing_step.category = step_data.get(
                                    "category", "post_invite"
                                )
                                # Update interactions (new modular system)
                                existing_step.interactions = step_data.get(
                                    "interactions", None
                                )
                                updated_count += 1
                                continue

                            # Use next available position to avoid conflicts
                            position = next_position
                            next_position += 1
                        else:
                            position = step_data["position"]

                        # Create new step
                        new_step = WizardStep(
                            server_type=server_type,
                            position=position,
                            title=step_data.get("title"),
                            markdown=step_data["markdown"],
                            requires=step_data.get("requires"),
                            require_interaction=bool(
                                step_data.get("require_interaction") or False
                            ),
                            category=step_data.get("category", "post_invite"),
                            interactions=step_data.get("interactions", None),
                        )
                        self.session.add(new_step)
                        imported_count += 1

                    except Exception as e:
                        error_msg = f"Failed to import step for {server_type} at position {step_data['position']}: {e!s}"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
                        skipped_count += 1

            # Commit all changes
            self.session.commit()

            success = len(errors) == 0 or (imported_count > 0 or updated_count > 0)
            message = self._build_import_message(
                imported_count, updated_count, skipped_count, replace_existing
            )

            return WizardImportResult(
                success=success,
                message=message,
                imported_count=imported_count,
                skipped_count=skipped_count,
                updated_count=updated_count,
                errors=errors,
            )

        except Exception as e:
            self.session.rollback()
            error_msg = f"Steps import failed: {e!s}"
            self.logger.error(error_msg)
            return WizardImportResult(
                success=False,
                message=error_msg,
                imported_count=0,
                skipped_count=0,
                updated_count=0,
                errors=[error_msg],
            )

    def _import_bundle(
        self, data: dict[str, Any], replace_existing: bool
    ) -> WizardImportResult:
        """Import a wizard bundle from JSON data."""
        try:
            bundle_data = data["bundle"]
            bundle_name = bundle_data["name"]

            # Check if bundle already exists
            existing_bundle = (
                self.session.query(WizardBundle)
                .filter(WizardBundle.name == bundle_name)
                .first()
            )

            if existing_bundle and not replace_existing:
                return WizardImportResult(
                    success=False,
                    message=f"Bundle '{bundle_name}' already exists. Use replace mode to overwrite.",
                    imported_count=0,
                    skipped_count=0,
                    updated_count=0,
                    errors=[f"Bundle '{bundle_name}' already exists"],
                )

            if existing_bundle and replace_existing:
                # Delete existing bundle (cascades to bundle steps)
                self.session.delete(existing_bundle)
                self.logger.info(
                    f"Deleted existing bundle '{bundle_name}' for replacement"
                )

            # Create new bundle
            new_bundle = WizardBundle(
                name=bundle_name, description=bundle_data.get("description")
            )
            self.session.add(new_bundle)
            self.session.flush()  # Get the bundle ID

            # Import bundle steps as individual wizard steps with server_type "custom"
            imported_count = 0
            errors = []

            # Find next available position for custom steps
            existing_max_position = (
                self.session.query(db.func.max(WizardStep.position))
                .filter(WizardStep.server_type == "custom")
                .scalar()
            )
            next_position = (existing_max_position or -1) + 1

            for bundle_position, step_data in enumerate(bundle_data["steps"]):
                try:
                    # Create the wizard step with server_type "custom"
                    wizard_step = WizardStep(
                        server_type="custom",
                        position=next_position,
                        title=step_data.get("title"),
                        markdown=step_data["markdown"],
                        requires=step_data.get("requires"),
                        require_interaction=bool(
                            step_data.get("require_interaction") or False
                        ),
                        category=step_data.get("category", "post_invite"),
                        interactions=step_data.get("interactions", None),
                    )
                    self.session.add(wizard_step)
                    self.session.flush()  # Get the step ID

                    # Create bundle step association
                    bundle_step = WizardBundleStep(
                        bundle_id=new_bundle.id,
                        step_id=wizard_step.id,
                        position=bundle_position,
                    )
                    self.session.add(bundle_step)

                    imported_count += 1
                    next_position += 1

                except Exception as e:
                    error_msg = f"Failed to import bundle step at position {bundle_position}: {e!s}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)

            self.session.commit()

            success = imported_count > 0
            message = f"Successfully imported bundle '{bundle_name}' with {imported_count} steps"
            if errors:
                message += f" ({len(errors)} steps failed)"

            return WizardImportResult(
                success=success,
                message=message,
                imported_count=imported_count,
                skipped_count=len(errors),
                updated_count=0,
                errors=errors,
            )

        except Exception as e:
            self.session.rollback()
            error_msg = f"Bundle import failed: {e!s}"
            self.logger.error(error_msg)
            return WizardImportResult(
                success=False,
                message=error_msg,
                imported_count=0,
                skipped_count=0,
                updated_count=0,
                errors=[error_msg],
            )

    def _build_import_message(
        self,
        imported_count: int,
        updated_count: int,
        skipped_count: int,
        replace_existing: bool,
    ) -> str:
        """Build a descriptive message for import results."""
        parts = []

        if replace_existing:
            parts.append("Full import completed")
        else:
            parts.append("Additive import completed")

        if imported_count > 0:
            parts.append(f"{imported_count} steps imported")

        if updated_count > 0:
            parts.append(f"{updated_count} steps updated")

        if skipped_count > 0:
            parts.append(f"{skipped_count} steps skipped due to errors")

        return ": ".join(parts) if len(parts) > 1 else parts[0]

    def get_server_types_with_steps(self) -> list[str]:
        """Get list of server types that have wizard steps.

        Returns:
            Sorted list of server types
        """
        server_types = self.session.query(WizardStep.server_type).distinct().all()
        return sorted([row[0] for row in server_types])
