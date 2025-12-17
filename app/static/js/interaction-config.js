/**
 * Interaction Configuration Component for Admin UI
 *
 * Alpine.js component for managing wizard step interaction configurations.
 * Used in the admin wizard step creation/editing forms.
 *
 * @param {Object} initialConfig - Initial configuration from form field
 * @returns {Object} Alpine.js component data
 */
function interactionConfig(initialConfig = {}) {
  // Default configuration structure
  const defaultConfig = {
    click: {
      enabled: false,
      target_selector: 'a, button',
      description: ''
    },
    time: {
      enabled: false,
      duration_seconds: 30,
      show_countdown: true
    },
    tos: {
      enabled: false,
      content_markdown: '',
      checkbox_label: 'I agree to the Terms of Service',
      require_scroll: false,
      version: null
    },
    text_input: {
      enabled: false,
      question: '',
      answers: [],
      answers_text: '', // For textarea binding
      case_sensitive: false,
      placeholder: 'Enter your answer',
      error_message: 'Incorrect answer. Please try again.'
    },
    quiz: {
      enabled: false,
      questions: [],
      pass_threshold: 1.0,
      shuffle_questions: false,
      shuffle_answers: false,
      show_explanations: true
    }
  };

  // Merge initial config with defaults
  function mergeConfig(initial) {
    const merged = JSON.parse(JSON.stringify(defaultConfig));

    if (initial && typeof initial === 'object') {
      // Click
      if (initial.click) {
        merged.click = { ...merged.click, ...initial.click };
      }
      // Time
      if (initial.time) {
        merged.time = { ...merged.time, ...initial.time };
      }
      // ToS
      if (initial.tos) {
        merged.tos = { ...merged.tos, ...initial.tos };
      }
      // Text Input
      if (initial.text_input) {
        merged.text_input = { ...merged.text_input, ...initial.text_input };
        // Convert answers array to text for textarea
        if (Array.isArray(initial.text_input.answers)) {
          merged.text_input.answers_text = initial.text_input.answers.join('\n');
        }
      }
      // Quiz
      if (initial.quiz) {
        merged.quiz = { ...merged.quiz, ...initial.quiz };
        // Ensure questions have proper structure
        if (Array.isArray(initial.quiz.questions)) {
          merged.quiz.questions = initial.quiz.questions.map(q => {
            const options = q.options || ['', ''];
            // Compute correct_option_index from correct_answer if not already set
            let correctIndex = q.correct_option_index;
            if (correctIndex === undefined || correctIndex === null) {
              correctIndex = options.indexOf(q.correct_answer);
              if (correctIndex === -1) correctIndex = 0; // Default to first option
            }
            return {
              id: q.id || generateId(),
              question: q.question || '',
              type: q.type || 'multiple_choice',
              options: options,
              correct_option_index: correctIndex,
              correct_answer: q.correct_answer,
              explanation: q.explanation || ''
            };
          });
        }
      }
    }

    return merged;
  }

  // Generate unique ID for quiz questions
  function generateId() {
    return 'q_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  return {
    // Configuration state
    config: mergeConfig(initialConfig),

    // Main section collapsed/expanded state (collapsed by default)
    mainSectionExpanded: false,

    // Section visibility state
    sections: {
      click: false,
      time: false,
      tos: false,
      text_input: false,
      quiz: false
    },

    // JSON output for form submission
    configJson: '{}',

    /**
     * Initialize the component
     */
    init() {
      // Expand main section if any interaction type is already enabled
      // (e.g., when editing an existing step with interactions)
      if (this.hasEnabledInteractions()) {
        this.mainSectionExpanded = true;
      }

      // Expand individual sections that are enabled
      Object.keys(this.sections).forEach(key => {
        if (this.config[key]?.enabled) {
          this.sections[key] = true;
        }
      });

      // Set up watcher to sync JSON on changes
      this.$watch('config', () => this.syncJson(), { deep: true });

      // Initial sync
      this.syncJson();
    },

    /**
     * Toggle accordion section visibility
     * @param {string} name - Section name
     */
    toggleSection(name) {
      this.sections[name] = !this.sections[name];
    },

    /**
     * Sync config to JSON string for form submission
     */
    syncJson() {
      // Build clean config object (only include enabled types)
      const output = {};

      if (this.config.click.enabled) {
        output.click = {
          enabled: true,
          target_selector: this.config.click.target_selector || 'a, button',
          description: this.config.click.description || null
        };
      }

      if (this.config.time.enabled) {
        output.time = {
          enabled: true,
          duration_seconds: parseInt(this.config.time.duration_seconds, 10) || 30,
          show_countdown: this.config.time.show_countdown !== false
        };
      }

      if (this.config.tos.enabled) {
        output.tos = {
          enabled: true,
          content_markdown: this.config.tos.content_markdown || '',
          checkbox_label: this.config.tos.checkbox_label || 'I agree to the Terms of Service',
          require_scroll: this.config.tos.require_scroll || false,
          version: this.config.tos.version || null
        };
      }

      if (this.config.text_input.enabled) {
        // Parse answers from textarea
        const answers = (this.config.text_input.answers_text || '')
          .split('\n')
          .map(a => a.trim())
          .filter(a => a);

        output.text_input = {
          enabled: true,
          question: this.config.text_input.question || '',
          answers: answers,
          case_sensitive: this.config.text_input.case_sensitive || false,
          placeholder: this.config.text_input.placeholder || 'Enter your answer',
          error_message: this.config.text_input.error_message || 'Incorrect answer. Please try again.'
        };
      }

      if (this.config.quiz.enabled && this.config.quiz.questions.length > 0) {
        output.quiz = {
          enabled: true,
          questions: this.config.quiz.questions.map(q => {
            // Compute correct_answer from correct_option_index
            const filteredOptions = q.type === 'multiple_choice'
              ? q.options.filter(o => o.trim())
              : q.options;
            const correctAnswer = q.correct_option_index !== null && q.correct_option_index !== undefined
              ? q.options[q.correct_option_index]
              : q.correct_answer;
            const question = {
              id: q.id,
              question: q.question,
              type: q.type,
              correct_answer: correctAnswer,
              explanation: q.explanation || null
            };
            if (q.type === 'multiple_choice') {
              question.options = filteredOptions;
            }
            return question;
          }),
          pass_threshold: parseFloat(this.config.quiz.pass_threshold) || 1.0,
          shuffle_questions: this.config.quiz.shuffle_questions || false,
          shuffle_answers: this.config.quiz.shuffle_answers || false,
          show_explanations: this.config.quiz.show_explanations !== false
        };
      }

      this.configJson = Object.keys(output).length > 0 ? JSON.stringify(output) : '{}';
    },

    /**
     * Check if any interaction type is enabled
     * @returns {boolean}
     */
    hasEnabledInteractions() {
      return (
        this.config.click.enabled ||
        this.config.time.enabled ||
        this.config.tos.enabled ||
        this.config.text_input.enabled ||
        (this.config.quiz.enabled && this.config.quiz.questions.length > 0)
      );
    },

    // ═══════════════════════════════════════════════════════════════════════
    // Quiz Question Management
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Add a new quiz question
     */
    addQuestion() {
      this.config.quiz.questions.push({
        id: generateId(),
        question: '',
        type: 'multiple_choice',
        options: ['', ''],
        correct_option_index: 0, // Track by index, first option selected by default
        correct_answer: '',
        explanation: ''
      });
    },

    /**
     * Remove a quiz question
     * @param {number} index - Question index
     */
    removeQuestion(index) {
      this.config.quiz.questions.splice(index, 1);
    },

    /**
     * Add an option to a multiple choice question
     * @param {Object} question - Question object
     */
    addOption(question) {
      if (!question.options) {
        question.options = [];
      }
      question.options.push('');
    },

    /**
     * Remove an option from a multiple choice question
     * @param {Object} question - Question object
     * @param {number} optIdx - Option index
     */
    removeOption(question, optIdx) {
      if (question.options.length > 2) {
        question.options.splice(optIdx, 1);
        // Adjust correct_option_index when removing an option
        if (question.correct_option_index === optIdx) {
          // Removed the correct option, default to first option
          question.correct_option_index = 0;
        } else if (question.correct_option_index > optIdx) {
          // Shift index down if a prior option was removed
          question.correct_option_index--;
        }
      }
    },

    /**
     * Handle question type change between multiple_choice and true_false
     * @param {Object} question - Question object
     */
    changeQuestionType(question) {
      if (question.type === 'true_false') {
        question.options = ['True', 'False'];
        question.correct_answer = true; // Default to "True"
      } else if (question.type === 'multiple_choice') {
        // Reset to clean state for multiple choice
        question.options = ['', ''];
        question.correct_option_index = 0;
        question.correct_answer = '';
      }
    }
  };
}

// Make available globally for Alpine.js
window.interactionConfig = interactionConfig;
