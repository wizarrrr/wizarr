const SemanticReleaseError = require('@semantic-release/error')
const ERROR_DEFINITIONS = require('./errors.cjs')

/** @typedef {import('./types').Context} Context */
/**
 * @param {string} code -.
 * @param {Context} ctx -.
 * @returns {Error} -.
 * @example
 * const throw getError('CUSTOMERROR')
 */
module.exports = (code, ctx) => {
    const { message, details } = ERROR_DEFINITIONS.get(code)(ctx)
    return new SemanticReleaseError(message, code, details)
}
