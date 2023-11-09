const { promises: fs } = require('fs')
const path = require('path')

/**
 * @typedef {import('./types').SentryOrganizationReleaseFile} SentryOrganizationReleaseFile
 */
/**
 * @param {string} dir - Path of source files.
 * @param {string} urlPrefix - Path of source files.
 * @param {boolean} [appendPath=false] -.
 * @param {string[]} [extensions=['.js', '.map', '.jsbundle', '.bundle']] - Extension allowed.
 * @returns {Promise<SentryOrganizationReleaseFile[]>} - Array of files.
 * @example
 * const sourcefiles = await getFiles(path.resolve(ctx.cwd, pluginConfig.sourcemaps))
 */
async function getFiles(
  dir,
  urlPrefix,
  appendPath = false,
  extensions = ['.js', '.map', '.jsbundle', '.bundle'],
) {
  // eslint-disable-next-line security/detect-non-literal-fs-filename
  const entries = await fs.readdir(dir, { withFileTypes: true })

  // Get files within the current directory and add a path key to the file objects
  const files = entries
    .filter((file) => !file.isDirectory())
    .filter((file) => extensions.includes(path.extname(file.name)))
    .map((file) => {
      const paths = [urlPrefix]
      if (appendPath) paths.push(path.basename(dir))
      paths.push(file.name)
      return { name: path.join(...paths), file: path.resolve(dir, file.name) }
    })

  // Get folders within the current directory
  const folders = entries.filter((folder) => folder.isDirectory())

  /*
    Add the found files within the subdirectory to the files array by calling the
    current function itself
  */
  for (const folder of folders) {
    files.push(
      ...(await getFiles(path.join(dir, folder.name), urlPrefix, true)),
    )
  }

  return files
}

module.exports = getFiles
