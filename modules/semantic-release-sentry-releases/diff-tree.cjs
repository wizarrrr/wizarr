const gitDiffTree = require('git-diff-tree')
const path = require('path')

/**
 * @typedef {import('./types').SentryReleasePatchSet} SentryReleasePatchSet
 * @typedef {import('./types').GitDiffTreeData} GitDiffTreeData
 * @typedef {import('./types').GIT_DIFF_TREE_TYPES} GIT_DIFF_TREE_TYPES
 */

const GIT_DIFF_TREE_TYPES = {
  RAW_DATA: 'raw',
  PATCH_DATA: 'patch',
  FILE_STATS: 'stats',
  NO_SHOW: 'noshow',
}

const PATCH_SET_TYPES = {
  ADD: 'A',
  MODIFY: 'M',
  DELETE: 'D',
  RENAME: 'R',
}
/**
 * @param {string} basedir -.
 * @param {string} rev -.
 * @returns {Promise<Array<SentryReleasePatchSet>>} -.
 * @example
 * const patchSet = await getCommitPatchSet('abcdef')
 */
const getCommitPatchSet = (basedir, rev = 'HEAD') => {
  return new Promise((resolve, reject) => {
    /** @type {Array<SentryReleasePatchSet>} */
    const patchSet = []
    const repoPath = path.join(basedir, '.git')
    gitDiffTree(repoPath, { rev })
      .on(
        'data',
        // eslint-disable-next-line valid-jsdoc, jsdoc/require-example
        /**
         * @param {GIT_DIFF_TREE_TYPES} type -.
         * @param {GitDiffTreeData} data -.
         */
        (type, data) => {
          if (
            type === GIT_DIFF_TREE_TYPES.RAW_DATA &&
            data.status !== PATCH_SET_TYPES.RENAME
          ) {
            patchSet.push({ path: data.toFile, type: data.status })
          }
        },
      )
      .on('error', (err) => reject(err))
      .on('end', () => {
        resolve(patchSet)
      })
  })
}

module.exports = getCommitPatchSet
