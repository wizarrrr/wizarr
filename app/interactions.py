"""Modular wizard step interaction types.

This module provides strongly-typed dataclasses for configuring various
interaction requirements that users must satisfy before proceeding to the
next wizard step. Interaction types are combinable - multiple types can
be enabled on a single step and all must be satisfied.

Supported interaction types:
- Click: User must click a link/button in content
- Time: User must wait N seconds (countdown timer)
- ToS: User must accept Terms of Service
- TextInput: User must answer a question correctly
- Quiz: User must pass a multi-question quiz
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Self


class InteractionType(StrEnum):
    """Supported wizard step interaction types."""

    CLICK = "click"
    TIME = "time"
    TOS = "tos"
    TEXT_INPUT = "text_input"
    QUIZ = "quiz"


class QuizQuestionType(StrEnum):
    """Supported quiz question types."""

    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"


@dataclass(frozen=True, slots=True)
class ClickInteraction:
    """Configuration for click-based interaction requirement.

    Requires user to click a link or button within the step content
    before proceeding. This is similar to the legacy require_interaction
    behavior but implemented as a modular component.

    Attributes:
        enabled: Whether this interaction type is active.
        target_selector: CSS selector for clickable elements (default: "a, button").
        description: Optional help text shown to user.
    """

    enabled: bool = True
    target_selector: str = "a, button"
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "enabled": self.enabled,
            "target_selector": self.target_selector,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Deserialize from JSON dict."""
        return cls(
            enabled=data.get("enabled", True),
            target_selector=data.get("target_selector", "a, button"),
            description=data.get("description"),
        )


@dataclass(frozen=True, slots=True)
class TimeInteraction:
    """Configuration for time-based interaction requirement.

    Requires user to wait for a specified duration before the
    continue button becomes available. Shows a countdown timer.

    Attributes:
        enabled: Whether this interaction type is active.
        duration_seconds: Number of seconds to wait.
        show_countdown: Whether to display countdown timer to user.
    """

    enabled: bool = True
    duration_seconds: int = 30
    show_countdown: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "enabled": self.enabled,
            "duration_seconds": self.duration_seconds,
            "show_countdown": self.show_countdown,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Deserialize from JSON dict."""
        return cls(
            enabled=data.get("enabled", True),
            duration_seconds=data.get("duration_seconds", 30),
            show_countdown=data.get("show_countdown", True),
        )

    def validate(self) -> list[str]:
        """Return validation errors, if any."""
        errors = []
        if self.duration_seconds < 1:
            errors.append("Time duration must be at least 1 second")
        return errors


@dataclass(frozen=True, slots=True)
class TosInteraction:
    """Configuration for Terms of Service acceptance interaction.

    Requires user to read and accept terms of service before
    proceeding. Supports rich markdown content and optional
    scroll-to-bottom requirement.

    Attributes:
        enabled: Whether this interaction type is active.
        content_markdown: Terms content in markdown format.
        checkbox_label: Label for the acceptance checkbox.
        require_scroll: Whether user must scroll to bottom before checkbox appears.
        version: Optional version string for tracking ToS changes.
    """

    enabled: bool = True
    content_markdown: str = ""
    checkbox_label: str = "I agree to the Terms of Service"
    require_scroll: bool = False
    version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "enabled": self.enabled,
            "content_markdown": self.content_markdown,
            "checkbox_label": self.checkbox_label,
            "require_scroll": self.require_scroll,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Deserialize from JSON dict."""
        return cls(
            enabled=data.get("enabled", True),
            content_markdown=data.get("content_markdown", ""),
            checkbox_label=data.get(
                "checkbox_label", "I agree to the Terms of Service"
            ),
            require_scroll=data.get("require_scroll", False),
            version=data.get("version"),
        )

    def validate(self) -> list[str]:
        """Return validation errors, if any."""
        errors = []
        if not self.content_markdown.strip():
            errors.append("ToS content cannot be empty")
        if len(self.content_markdown) > 100000:
            errors.append("ToS content exceeds maximum length (100,000 characters)")
        return errors


@dataclass(frozen=True, slots=True)
class TextInputInteraction:
    """Configuration for text input validation interaction.

    Requires user to provide a specific answer to a question.
    Supports multiple acceptable answers and case sensitivity options.

    Attributes:
        enabled: Whether this interaction type is active.
        question: The question to display to the user.
        answers: List of acceptable answers.
        case_sensitive: Whether answer matching is case-sensitive.
        placeholder: Placeholder text for the input field.
        error_message: Message shown when answer is incorrect.
    """

    enabled: bool = True
    question: str = ""
    answers: tuple[str, ...] = field(default_factory=tuple)
    case_sensitive: bool = False
    placeholder: str = "Enter your answer"
    error_message: str = "Incorrect answer. Please try again."

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "enabled": self.enabled,
            "question": self.question,
            "answers": list(self.answers),
            "case_sensitive": self.case_sensitive,
            "placeholder": self.placeholder,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Deserialize from JSON dict."""
        answers = data.get("answers", [])
        if isinstance(answers, list):
            answers = tuple(answers)
        return cls(
            enabled=data.get("enabled", True),
            question=data.get("question", ""),
            answers=answers,
            case_sensitive=data.get("case_sensitive", False),
            placeholder=data.get("placeholder", "Enter your answer"),
            error_message=data.get(
                "error_message", "Incorrect answer. Please try again."
            ),
        )

    def validate(self) -> list[str]:
        """Return validation errors, if any."""
        errors = []
        if not self.question.strip():
            errors.append("Text input question cannot be empty")
        if not self.answers:
            errors.append("At least one valid answer is required")
        if any(not ans.strip() for ans in self.answers):
            errors.append("Empty answers are not allowed")
        return errors

    def check_answer(self, user_answer: str) -> bool:
        """Check if user's answer matches any valid answer."""
        user_answer = user_answer.strip()
        if self.case_sensitive:
            return user_answer in self.answers
        return user_answer.lower() in [a.lower() for a in self.answers]


@dataclass(frozen=True, slots=True)
class QuizQuestion:
    """A single quiz question configuration.

    Attributes:
        id: Unique identifier for this question.
        question: The question text.
        type: Question type (multiple_choice or true_false).
        correct_answer: The correct answer (string for MC, bool for T/F).
        options: List of options for multiple choice questions.
        explanation: Optional explanation shown after answering.
    """

    id: str
    question: str
    type: QuizQuestionType
    correct_answer: str | bool
    options: tuple[str, ...] = field(default_factory=tuple)
    explanation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        result: dict[str, Any] = {
            "id": self.id,
            "question": self.question,
            "type": self.type.value,
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
        }
        if self.type == QuizQuestionType.MULTIPLE_CHOICE:
            result["options"] = list(self.options)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Deserialize from JSON dict."""
        options = data.get("options", [])
        if isinstance(options, list):
            options = tuple(options)
        return cls(
            id=data.get("id", ""),
            question=data.get("question", ""),
            type=QuizQuestionType(data.get("type", "multiple_choice")),
            correct_answer=data.get("correct_answer", ""),
            options=options,
            explanation=data.get("explanation"),
        )

    def validate(self) -> list[str]:
        """Return validation errors, if any."""
        errors = []
        if not self.id.strip():
            errors.append("Question ID cannot be empty")
        if not self.question.strip():
            errors.append(f"Question '{self.id}' text cannot be empty")
        if self.type == QuizQuestionType.MULTIPLE_CHOICE:
            if len(self.options) < 2:
                errors.append(f"Question '{self.id}' needs at least 2 options")
            if self.correct_answer not in self.options:
                errors.append(f"Question '{self.id}' correct answer not in options")
        if self.type == QuizQuestionType.TRUE_FALSE and not isinstance(
            self.correct_answer, bool
        ):
            errors.append(
                f"Question '{self.id}' must have boolean correct_answer for true/false type"
            )
        return errors

    def check_answer(self, user_answer: str | bool) -> bool:
        """Check if user's answer is correct."""
        if self.type == QuizQuestionType.TRUE_FALSE:
            # Handle string "true"/"false" from form submission
            if isinstance(user_answer, str):
                user_answer = user_answer.lower() == "true"
            return user_answer == self.correct_answer
        return user_answer == self.correct_answer


@dataclass(frozen=True, slots=True)
class QuizInteraction:
    """Configuration for quiz interaction requirement.

    Requires user to answer a series of questions correctly.
    Supports multiple choice and true/false question types.

    Attributes:
        enabled: Whether this interaction type is active.
        questions: List of quiz questions.
        pass_threshold: Fraction (0.0-1.0) of questions that must be correct.
        shuffle_questions: Whether to randomize question order.
        show_explanations: Whether to show explanations after answering.
    """

    enabled: bool = True
    questions: tuple[QuizQuestion, ...] = field(default_factory=tuple)
    pass_threshold: float = 1.0
    shuffle_questions: bool = False
    show_explanations: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "enabled": self.enabled,
            "questions": [q.to_dict() for q in self.questions],
            "pass_threshold": self.pass_threshold,
            "shuffle_questions": self.shuffle_questions,
            "show_explanations": self.show_explanations,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Deserialize from JSON dict."""
        questions = tuple(QuizQuestion.from_dict(q) for q in data.get("questions", []))
        return cls(
            enabled=data.get("enabled", True),
            questions=questions,
            pass_threshold=data.get("pass_threshold", 1.0),
            shuffle_questions=data.get("shuffle_questions", False),
            show_explanations=data.get("show_explanations", True),
        )

    def validate(self) -> list[str]:
        """Return validation errors, if any."""
        errors = []
        if not self.questions:
            errors.append("Quiz must have at least one question")
        if not 0.0 <= self.pass_threshold <= 1.0:
            errors.append("Pass threshold must be between 0.0 and 1.0")
        # Check for duplicate question IDs
        ids = [q.id for q in self.questions]
        if len(ids) != len(set(ids)):
            errors.append("Duplicate question IDs found")
        # Validate each question
        for q in self.questions:
            errors.extend(q.validate())
        return errors

    def calculate_score(self, answers: dict[str, str | bool]) -> tuple[int, int, float]:
        """Calculate quiz score.

        Args:
            answers: Dict mapping question ID to user's answer.

        Returns:
            Tuple of (correct_count, total_count, score_fraction).
        """
        correct = 0
        for q in self.questions:
            if q.id in answers and q.check_answer(answers[q.id]):
                correct += 1
        total = len(self.questions)
        score = correct / total if total > 0 else 0.0
        return correct, total, score

    def check_passed(self, answers: dict[str, str | bool]) -> bool:
        """Check if user passed the quiz."""
        _, _, score = self.calculate_score(answers)
        return score >= self.pass_threshold


@dataclass(slots=True)
class StepInteractions:
    """Container for all interaction configurations on a wizard step.

    Presence of a non-None interaction with enabled=True indicates it is active.
    All enabled interactions must be satisfied for the user to proceed.

    Attributes:
        click: Click interaction configuration.
        time: Time-based interaction configuration.
        tos: Terms of Service interaction configuration.
        text_input: Text input validation configuration.
        quiz: Quiz interaction configuration.
    """

    click: ClickInteraction | None = None
    time: TimeInteraction | None = None
    tos: TosInteraction | None = None
    text_input: TextInputInteraction | None = None
    quiz: QuizInteraction | None = None

    def to_dict(self) -> dict[str, Any] | None:
        """Serialize to JSON-compatible dict.

        Returns None if no interactions are enabled.
        """
        result: dict[str, Any] = {}
        if self.click and self.click.enabled:
            result["click"] = self.click.to_dict()
        if self.time and self.time.enabled:
            result["time"] = self.time.to_dict()
        if self.tos and self.tos.enabled:
            result["tos"] = self.tos.to_dict()
        if self.text_input and self.text_input.enabled:
            result["text_input"] = self.text_input.to_dict()
        if self.quiz and self.quiz.enabled:
            result["quiz"] = self.quiz.to_dict()
        return result if result else None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Self:
        """Deserialize from JSON dict."""
        if not data:
            return cls()
        return cls(
            click=ClickInteraction.from_dict(data["click"])
            if "click" in data
            else None,
            time=TimeInteraction.from_dict(data["time"]) if "time" in data else None,
            tos=TosInteraction.from_dict(data["tos"]) if "tos" in data else None,
            text_input=TextInputInteraction.from_dict(data["text_input"])
            if "text_input" in data
            else None,
            quiz=QuizInteraction.from_dict(data["quiz"]) if "quiz" in data else None,
        )

    def has_any_interaction(self) -> bool:
        """Check if any interaction type is enabled."""
        return any(
            [
                self.click and self.click.enabled,
                self.time and self.time.enabled,
                self.tos and self.tos.enabled,
                self.text_input and self.text_input.enabled,
                self.quiz and self.quiz.enabled,
            ]
        )

    def get_enabled_types(self) -> list[InteractionType]:
        """Get list of enabled interaction types."""
        types = []
        if self.click and self.click.enabled:
            types.append(InteractionType.CLICK)
        if self.time and self.time.enabled:
            types.append(InteractionType.TIME)
        if self.tos and self.tos.enabled:
            types.append(InteractionType.TOS)
        if self.text_input and self.text_input.enabled:
            types.append(InteractionType.TEXT_INPUT)
        if self.quiz and self.quiz.enabled:
            types.append(InteractionType.QUIZ)
        return types

    def validate(self) -> list[str]:
        """Validate all enabled interactions."""
        errors = []
        if self.time and self.time.enabled:
            errors.extend(self.time.validate())
        if self.tos and self.tos.enabled:
            errors.extend(self.tos.validate())
        if self.text_input and self.text_input.enabled:
            errors.extend(self.text_input.validate())
        if self.quiz and self.quiz.enabled:
            errors.extend(self.quiz.validate())
        return errors
