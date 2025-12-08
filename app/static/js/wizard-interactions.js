/**
 * Wizard Interaction Handler System
 *
 * Modular system for handling user interactions in wizard steps.
 * Each interaction type has its own handler that validates when the user
 * has satisfied the interaction requirement.
 */

// ============================================================================
// Base Handler
// ============================================================================

class InteractionHandler {
  constructor(config, onSatisfied) {
    this.config = config;
    this.onSatisfied = onSatisfied;
    this.satisfied = false;
  }

  /** Initialize the handler - override in subclasses */
  init() {}

  /** Check if this interaction is satisfied */
  isSatisfied() {
    return this.satisfied;
  }

  /** Mark this interaction as satisfied */
  markSatisfied() {
    if (!this.satisfied) {
      this.satisfied = true;
      if (this.onSatisfied) {
        this.onSatisfied(this);
      }
    }
  }

  /** Clean up resources - override in subclasses */
  cleanup() {}
}

// ============================================================================
// Click Interaction Handler
// ============================================================================

class ClickInteractionHandler extends InteractionHandler {
  constructor(config, onSatisfied) {
    super(config, onSatisfied);
    this.clickHandler = null;
    this.targetSelector = config.target_selector || "a, button";
  }

  init() {
    // Find clickable elements in the wizard content
    const contentArea = document.querySelector("#wizard-body, .wizard-content");
    if (!contentArea) return;

    const targets = contentArea.querySelectorAll(this.targetSelector);
    if (targets.length === 0) {
      // No targets found, auto-satisfy (content may not have clickable elements)
      this.markSatisfied();
      return;
    }

    this.clickHandler = (e) => {
      // Check if click was on a target element
      const target = e.target.closest(this.targetSelector);
      if (target) {
        this.markSatisfied();
      }
    };

    contentArea.addEventListener("click", this.clickHandler);
  }

  cleanup() {
    if (this.clickHandler) {
      const contentArea = document.querySelector(
        "#wizard-body, .wizard-content"
      );
      if (contentArea) {
        contentArea.removeEventListener("click", this.clickHandler);
      }
      this.clickHandler = null;
    }
  }
}

// ============================================================================
// Time Interaction Handler
// ============================================================================

class TimeInteractionHandler extends InteractionHandler {
  constructor(config, onSatisfied) {
    super(config, onSatisfied);
    this.duration = config.duration_seconds || 10;
    this.showCountdown = config.show_countdown !== false;
    this.timerId = null;
    this.startTime = null;
    this.countdownElement = null;
  }

  init() {
    this.startTime = Date.now();

    // Create countdown display if configured
    if (this.showCountdown) {
      this.createCountdownUI();
      this.updateCountdown();
    }

    // Start timer
    this.timerId = setInterval(() => {
      const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
      const remaining = Math.max(0, this.duration - elapsed);

      if (this.showCountdown) {
        this.updateCountdown(remaining);
      }

      if (remaining <= 0) {
        this.markSatisfied();
        this.cleanup();
      }
    }, 100);
  }

  createCountdownUI() {
    // Find or create the interaction status area
    let statusArea = document.querySelector("#interaction-status");
    if (!statusArea) {
      statusArea = document.createElement("div");
      statusArea.id = "interaction-status";
      statusArea.className = "mt-4 space-y-3";
      const wizardBody = document.querySelector("#wizard-body, .wizard-content");
      if (wizardBody) {
        wizardBody.appendChild(statusArea);
      }
    }

    this.countdownElement = document.createElement("div");
    this.countdownElement.className =
      "flex items-center gap-3 p-3 bg-blue-50 dark:bg-blue-900/30 rounded-lg text-blue-700 dark:text-blue-300";
    this.countdownElement.innerHTML = `
      <svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <span class="countdown-text">Please wait <strong>${this.duration}</strong> seconds...</span>
    `;
    statusArea.appendChild(this.countdownElement);
  }

  updateCountdown(remaining) {
    if (!this.countdownElement) return;

    remaining =
      remaining ?? Math.max(0, this.duration - Math.floor((Date.now() - this.startTime) / 1000));

    const textEl = this.countdownElement.querySelector(".countdown-text");
    if (textEl) {
      if (remaining > 0) {
        textEl.innerHTML = `Please wait <strong>${remaining}</strong> second${remaining !== 1 ? "s" : ""}...`;
      } else {
        textEl.innerHTML = `<span class="text-green-600 dark:text-green-400">Time complete!</span>`;
        // Change icon to checkmark
        const svg = this.countdownElement.querySelector("svg");
        if (svg) {
          svg.classList.remove("animate-spin");
          svg.innerHTML = `<path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>`;
        }
      }
    }
  }

  cleanup() {
    if (this.timerId) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
  }
}

// ============================================================================
// Terms of Service Interaction Handler
// ============================================================================

class TosInteractionHandler extends InteractionHandler {
  constructor(config, onSatisfied) {
    super(config, onSatisfied);
    this.requireScroll = config.require_scroll !== false;
    this.checkboxLabel = config.checkbox_label || "I have read and agree to the terms";
    this.content = config.content_markdown || "";
    this.scrollHandler = null;
    this.hasScrolledToBottom = false;
    this.tosElement = null;
  }

  init() {
    this.createTosUI();

    if (this.requireScroll) {
      const scrollContainer = this.tosElement?.querySelector(".tos-content");
      if (scrollContainer) {
        this.scrollHandler = () => this.checkScroll(scrollContainer);
        scrollContainer.addEventListener("scroll", this.scrollHandler);
        // Check initial state
        this.checkScroll(scrollContainer);
      }
    } else {
      this.hasScrolledToBottom = true;
    }
  }

  createTosUI() {
    let statusArea = document.querySelector("#interaction-status");
    if (!statusArea) {
      statusArea = document.createElement("div");
      statusArea.id = "interaction-status";
      statusArea.className = "mt-4 space-y-3";
      const wizardBody = document.querySelector("#wizard-body, .wizard-content");
      if (wizardBody) {
        wizardBody.appendChild(statusArea);
      }
    }

    this.tosElement = document.createElement("div");
    this.tosElement.className = "border dark:border-gray-700 rounded-lg overflow-hidden";
    this.tosElement.innerHTML = `
      <div class="tos-content max-h-48 overflow-y-auto p-4 bg-gray-50 dark:bg-gray-800 text-sm prose dark:prose-invert prose-sm">
        ${this.content || "<p>Terms of Service content</p>"}
      </div>
      <div class="p-3 bg-white dark:bg-gray-900 border-t dark:border-gray-700">
        <label class="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" class="tos-checkbox w-4 h-4 rounded border-gray-300 dark:border-gray-600" ${!this.requireScroll || this.hasScrolledToBottom ? "" : "disabled"}>
          <span class="text-sm text-gray-700 dark:text-gray-300">${this.checkboxLabel}</span>
        </label>
        ${this.requireScroll ? '<p class="scroll-hint mt-1 text-xs text-gray-500">Please scroll to the bottom to enable the checkbox</p>' : ""}
      </div>
    `;

    const checkbox = this.tosElement.querySelector(".tos-checkbox");
    if (checkbox) {
      checkbox.addEventListener("change", (e) => {
        if (e.target.checked && (!this.requireScroll || this.hasScrolledToBottom)) {
          this.markSatisfied();
        }
      });
    }

    statusArea.appendChild(this.tosElement);
  }

  checkScroll(container) {
    const isAtBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight < 20;
    if (isAtBottom && !this.hasScrolledToBottom) {
      this.hasScrolledToBottom = true;
      const checkbox = this.tosElement?.querySelector(".tos-checkbox");
      const hint = this.tosElement?.querySelector(".scroll-hint");
      if (checkbox) {
        checkbox.disabled = false;
      }
      if (hint) {
        hint.textContent = "You may now accept the terms";
        hint.classList.add("text-green-600", "dark:text-green-400");
      }
    }
  }

  cleanup() {
    if (this.scrollHandler && this.tosElement) {
      const scrollContainer = this.tosElement.querySelector(".tos-content");
      if (scrollContainer) {
        scrollContainer.removeEventListener("scroll", this.scrollHandler);
      }
    }
  }
}

// ============================================================================
// Text Input Validation Handler
// ============================================================================

class TextValidationHandler extends InteractionHandler {
  constructor(config, onSatisfied) {
    super(config, onSatisfied);
    this.question = config.question || "Please answer the question:";
    this.answers = config.answers || [];
    this.caseSensitive = config.case_sensitive === true;
    this.errorMessage = config.error_message || "Incorrect answer. Please try again.";
    this.inputElement = null;
  }

  init() {
    this.createTextInputUI();
  }

  createTextInputUI() {
    let statusArea = document.querySelector("#interaction-status");
    if (!statusArea) {
      statusArea = document.createElement("div");
      statusArea.id = "interaction-status";
      statusArea.className = "mt-4 space-y-3";
      const wizardBody = document.querySelector("#wizard-body, .wizard-content");
      if (wizardBody) {
        wizardBody.appendChild(statusArea);
      }
    }

    this.inputElement = document.createElement("div");
    this.inputElement.className = "p-4 border dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800";
    this.inputElement.innerHTML = `
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">${this.question}</label>
      <div class="flex gap-2">
        <input type="text" class="text-answer flex-1 px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white" placeholder="Type your answer...">
        <button type="button" class="check-answer px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">Check</button>
      </div>
      <p class="feedback mt-2 text-sm hidden"></p>
    `;

    const input = this.inputElement.querySelector(".text-answer");
    const button = this.inputElement.querySelector(".check-answer");
    const feedback = this.inputElement.querySelector(".feedback");

    const checkAnswer = () => {
      const userAnswer = input.value.trim();
      const normalizedUser = this.caseSensitive ? userAnswer : userAnswer.toLowerCase();

      const isCorrect = this.answers.some((answer) => {
        const normalizedAnswer = this.caseSensitive ? answer : answer.toLowerCase();
        return normalizedUser === normalizedAnswer;
      });

      if (isCorrect) {
        feedback.textContent = "Correct!";
        feedback.className = "feedback mt-2 text-sm text-green-600 dark:text-green-400";
        feedback.classList.remove("hidden");
        input.disabled = true;
        button.disabled = true;
        button.textContent = "Correct";
        button.className = "px-4 py-2 bg-green-600 text-white rounded-lg cursor-not-allowed";
        this.markSatisfied();
      } else {
        feedback.textContent = this.errorMessage;
        feedback.className = "feedback mt-2 text-sm text-red-600 dark:text-red-400";
        feedback.classList.remove("hidden");
        input.classList.add("border-red-500");
        setTimeout(() => {
          input.classList.remove("border-red-500");
        }, 2000);
      }
    };

    button.addEventListener("click", checkAnswer);
    input.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        checkAnswer();
      }
    });

    statusArea.appendChild(this.inputElement);
  }

  cleanup() {}
}

// ============================================================================
// Quiz Interaction Handler
// ============================================================================

class QuizInteractionHandler extends InteractionHandler {
  constructor(config, onSatisfied) {
    super(config, onSatisfied);
    this.questions = config.questions || [];
    this.passThreshold = config.pass_threshold ?? 1.0;
    this.shuffleQuestions = config.shuffle_questions === true;
    this.showExplanations = config.show_explanations !== false;
    this.quizElement = null;
    this.currentQuestion = 0;
    this.correctCount = 0;
    this.userAnswers = [];
  }

  init() {
    if (this.questions.length === 0) {
      this.markSatisfied();
      return;
    }

    if (this.shuffleQuestions) {
      this.questions = this.shuffleArray([...this.questions]);
    }

    this.createQuizUI();
  }

  shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
  }

  createQuizUI() {
    let statusArea = document.querySelector("#interaction-status");
    if (!statusArea) {
      statusArea = document.createElement("div");
      statusArea.id = "interaction-status";
      statusArea.className = "mt-4 space-y-3";
      const wizardBody = document.querySelector("#wizard-body, .wizard-content");
      if (wizardBody) {
        wizardBody.appendChild(statusArea);
      }
    }

    this.quizElement = document.createElement("div");
    this.quizElement.className = "border dark:border-gray-700 rounded-lg overflow-hidden";
    statusArea.appendChild(this.quizElement);

    this.renderQuestion();
  }

  renderQuestion() {
    if (!this.quizElement) return;

    const question = this.questions[this.currentQuestion];
    const progress = `Question ${this.currentQuestion + 1} of ${this.questions.length}`;

    this.quizElement.innerHTML = `
      <div class="p-4 bg-gray-50 dark:bg-gray-800">
        <div class="flex justify-between items-center mb-3">
          <span class="text-xs font-medium text-gray-500 dark:text-gray-400">${progress}</span>
          <span class="text-xs text-gray-500 dark:text-gray-400">${this.correctCount} correct</span>
        </div>
        <p class="font-medium text-gray-900 dark:text-white mb-4">${question.question}</p>
        <div class="space-y-2 quiz-options">
          ${this.renderOptions(question)}
        </div>
        <div class="quiz-feedback mt-4 hidden"></div>
      </div>
    `;

    // Add click handlers to options
    const options = this.quizElement.querySelectorAll(".quiz-option");
    options.forEach((option) => {
      option.addEventListener("click", (e) => this.selectAnswer(e, question));
    });
  }

  renderOptions(question) {
    if (question.type === "true_false") {
      return `
        <button type="button" class="quiz-option w-full text-left px-4 py-3 border dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors" data-value="true">True</button>
        <button type="button" class="quiz-option w-full text-left px-4 py-3 border dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors" data-value="false">False</button>
      `;
    }

    // Multiple choice
    const options = question.options || [];
    return options
      .map(
        (opt, i) => `
        <button type="button" class="quiz-option w-full text-left px-4 py-3 border dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors" data-value="${opt}">${opt}</button>
      `
      )
      .join("");
  }

  selectAnswer(e, question) {
    const selectedValue = e.target.dataset.value;
    const correctAnswer = String(question.correct_answer);
    const isCorrect = selectedValue === correctAnswer;

    if (isCorrect) {
      this.correctCount++;
    }

    this.userAnswers.push({
      question: question.question,
      selected: selectedValue,
      correct: correctAnswer,
      isCorrect,
    });

    // Show feedback
    const options = this.quizElement.querySelectorAll(".quiz-option");
    options.forEach((opt) => {
      opt.disabled = true;
      opt.classList.remove("hover:bg-gray-100", "dark:hover:bg-gray-700");

      if (opt.dataset.value === correctAnswer) {
        opt.classList.add("bg-green-100", "dark:bg-green-900/30", "border-green-500");
      } else if (opt.dataset.value === selectedValue && !isCorrect) {
        opt.classList.add("bg-red-100", "dark:bg-red-900/30", "border-red-500");
      }
    });

    const feedback = this.quizElement.querySelector(".quiz-feedback");
    if (feedback && this.showExplanations && question.explanation) {
      feedback.innerHTML = `
        <p class="text-sm ${isCorrect ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}">
          ${isCorrect ? "Correct!" : "Incorrect."} ${question.explanation}
        </p>
      `;
      feedback.classList.remove("hidden");
    }

    // Move to next question after a delay
    setTimeout(() => {
      this.currentQuestion++;
      if (this.currentQuestion < this.questions.length) {
        this.renderQuestion();
      } else {
        this.showResults();
      }
    }, 1500);
  }

  showResults() {
    if (!this.quizElement) return;

    const score = this.correctCount / this.questions.length;
    const passed = score >= this.passThreshold;
    const percentage = Math.round(score * 100);

    this.quizElement.innerHTML = `
      <div class="p-4 ${passed ? "bg-green-50 dark:bg-green-900/20" : "bg-red-50 dark:bg-red-900/20"}">
        <h3 class="font-bold text-lg ${passed ? "text-green-700 dark:text-green-300" : "text-red-700 dark:text-red-300"} mb-2">
          ${passed ? "Quiz Passed!" : "Quiz Not Passed"}
        </h3>
        <p class="text-gray-700 dark:text-gray-300 mb-3">
          You got ${this.correctCount} out of ${this.questions.length} correct (${percentage}%).
          ${passed ? "You may continue." : `You need ${Math.round(this.passThreshold * 100)}% to pass.`}
        </p>
        ${!passed ? '<button type="button" class="retry-quiz px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">Try Again</button>' : ""}
      </div>
    `;

    if (passed) {
      this.markSatisfied();
    } else {
      const retryBtn = this.quizElement.querySelector(".retry-quiz");
      if (retryBtn) {
        retryBtn.addEventListener("click", () => this.resetQuiz());
      }
    }
  }

  resetQuiz() {
    this.currentQuestion = 0;
    this.correctCount = 0;
    this.userAnswers = [];
    if (this.shuffleQuestions) {
      this.questions = this.shuffleArray([...this.questions]);
    }
    this.renderQuestion();
  }

  cleanup() {}
}

// ============================================================================
// Interaction Coordinator
// ============================================================================

class InteractionCoordinator {
  constructor(config, onAllSatisfied) {
    this.config = config || {};
    this.onAllSatisfied = onAllSatisfied;
    this.handlers = [];
    this.allSatisfied = false;
  }

  /**
   * Initialize the coordinator with interaction config.
   * Spawns handlers for each enabled interaction type.
   */
  init() {
    // Clear any existing interaction status
    const existingStatus = document.querySelector("#interaction-status");
    if (existingStatus) {
      existingStatus.remove();
    }

    // Create handlers for enabled interactions
    if (this.config.click?.enabled) {
      this.handlers.push(
        new ClickInteractionHandler(this.config.click, () => this.checkAllSatisfied())
      );
    }

    if (this.config.time?.enabled) {
      this.handlers.push(
        new TimeInteractionHandler(this.config.time, () => this.checkAllSatisfied())
      );
    }

    if (this.config.tos?.enabled) {
      this.handlers.push(
        new TosInteractionHandler(this.config.tos, () => this.checkAllSatisfied())
      );
    }

    if (this.config.text_input?.enabled) {
      this.handlers.push(
        new TextValidationHandler(this.config.text_input, () => this.checkAllSatisfied())
      );
    }

    if (this.config.quiz?.enabled) {
      this.handlers.push(
        new QuizInteractionHandler(this.config.quiz, () => this.checkAllSatisfied())
      );
    }

    // Initialize all handlers
    this.handlers.forEach((h) => h.init());

    // If no handlers, auto-satisfy
    if (this.handlers.length === 0) {
      this.allSatisfied = true;
      if (this.onAllSatisfied) {
        this.onAllSatisfied();
      }
    }
  }

  /**
   * Check if all interactions are satisfied.
   */
  checkAllSatisfied() {
    if (this.allSatisfied) return;

    const allDone = this.handlers.every((h) => h.isSatisfied());
    if (allDone) {
      this.allSatisfied = true;
      if (this.onAllSatisfied) {
        this.onAllSatisfied();
      }
    }
  }

  /**
   * Check if navigation should be enabled.
   */
  isNavigationEnabled() {
    return this.allSatisfied;
  }

  /**
   * Clean up all handlers.
   */
  cleanup() {
    this.handlers.forEach((h) => h.cleanup());
    this.handlers = [];
    this.allSatisfied = false;
  }
}

// ============================================================================
// Global Instance & Alpine Integration
// ============================================================================

// Global coordinator instance for the current step
window.wizardInteractionCoordinator = null;

/**
 * Initialize interactions for a wizard step.
 * Called from wizard-steps.js when a new step is loaded.
 *
 * @param {Object} config - Interaction configuration from server
 * @param {Function} onAllSatisfied - Callback when all interactions are satisfied
 * @returns {InteractionCoordinator}
 */
function initWizardInteractions(config, onAllSatisfied) {
  // Cleanup previous coordinator
  if (window.wizardInteractionCoordinator) {
    window.wizardInteractionCoordinator.cleanup();
  }

  // Create new coordinator
  const coordinator = new InteractionCoordinator(config, onAllSatisfied);
  coordinator.init();

  window.wizardInteractionCoordinator = coordinator;
  return coordinator;
}

/**
 * Check if current step interactions are satisfied.
 * Used by wizard navigation to determine if user can proceed.
 */
function areInteractionsSatisfied() {
  if (!window.wizardInteractionCoordinator) {
    return true; // No coordinator = no requirements
  }
  return window.wizardInteractionCoordinator.isNavigationEnabled();
}

/**
 * Clean up current interactions.
 * Called when navigating away from a step.
 */
function cleanupWizardInteractions() {
  if (window.wizardInteractionCoordinator) {
    window.wizardInteractionCoordinator.cleanup();
    window.wizardInteractionCoordinator = null;
  }
}

// Export for use by wizard-steps.js
window.initWizardInteractions = initWizardInteractions;
window.areInteractionsSatisfied = areInteractionsSatisfied;
window.cleanupWizardInteractions = cleanupWizardInteractions;
