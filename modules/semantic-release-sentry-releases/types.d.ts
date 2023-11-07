import {
  Config as SemanticReleaseConfig,
  Context as SemanticReleaseContext,
  Result as SemanticReleaseResult,
  Commit,
} from 'semantic-release'

export interface Context
  extends SemanticReleaseContext,
    SemanticReleaseConfig,
    SemanticReleaseResult {
  commits?: Commit[]
  message?: string
  logger?: any
  options?: any
  nextRelease?: any
}

export interface Config {
  // Set url of repository tags. Ex: https://gitlab.com/my-org/my-repo
  repositoryUrl?: string
  // Set url of repository tags. Ex: https://gitlab.com/my-org/my-repo/-/tags
  tagsUrl?: string
  environment?: string
  deployName?: string
  deployUrl?: string
  org?: string
  url?: string
  project?: string
  sourcemaps?: string
  urlPrefix?: string
  rewrite?: boolean
  releasePrefix?: string
  pathToGitFolder?: string
}

export enum PATCH_SET_TYPES {
  ADD = 'A',
  MODIFY = 'M',
  DELETE = 'D',
  RENAME = 'R',
}

export enum GIT_DIFF_TREE_TYPES {
  RAW_DATA = 'RAW DATA',
  PATCH_DATA = 'PATCH DATA',
  FILE_STATS = 'FILE STATS',
  NO_SHOW = 'noshow',
}
export interface SentryProject {
  name: string
  slug: string
}

export interface SentryReleaseSuccessResponse {
  authors: any[]
  commitCount: number
  data: any
  dateCreated: string
  dateReleased?: string
  deployCount: number
  firstEvent?: string
  lastCommit?: string
  lastDeploy?: string
  lastEvent?: string
  newGroups: number
  owner?: string
  projects: SentryProject[]
  ref: string
  shortVersion: string
  url?: string
  version: string
}

export interface SentryDeploySuccessResponse {
  dateFinished: string
  dateStarted: string
  environment: string
  id: string
  name: string
  url: string
}

export interface SentryReleasePatchSet {
  path: string
  type: PATCH_SET_TYPES
}

export interface SentryReleaseCommit {
  author_email?: string
  author_name?: string
  id: string
  message?: string
  patch_set?: SentryReleasePatchSet[]
  repository?: string
  timestamp?: string
}

export interface SentryReleaseParams {
  commits?: SentryReleaseCommit[]
  dateReleased?: Date
  projects: string[]
  ref?: string
  refs?: string[]
  url?: string
  version: string
}

export interface SentryDeployParams {
  dateFinished?: string
  dateStarted?: string
  environment: string
  name?: string
  url?: string
}

export interface PublishResult {
  release: SentryReleaseSuccessResponse
  deploy: SentryDeploySuccessResponse
}

export interface GitDiffTreeData {
  toFile: string
  status: PATCH_SET_TYPES
}

export interface SentryOrganizationReleaseFile {
  name: string
  file: string
}

export interface SentryOrganizationRepositoryProvider {
  id: string
  name: string
}

export interface SentryOrganizationRepository {
  id: string
  name: string
  url: string
  provider: SentryOrganizationRepositoryProvider
  status: string
  dateCreated: string
  integrationId: string
  externalSlug: number
}
