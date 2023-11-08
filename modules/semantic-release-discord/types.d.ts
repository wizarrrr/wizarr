// @ts-ignore
import { Config as SemanticReleaseConfig, Context as SemanticReleaseContext, Result as SemanticReleaseResult, Commit } from "semantic-release";

// @ts-ignore
export interface Context extends SemanticReleaseContext, SemanticReleaseConfig, SemanticReleaseResult {
    commits?: Commit[];
    message?: string;
    logger?: any;
    options?: any;
    nextRelease?: any;
}

export interface Config {
    webhookUrl: string;
}

export enum PATCH_SET_TYPES {
    ADD = "A",
    MODIFY = "M",
    DELETE = "D",
    RENAME = "R",
}

export enum GIT_DIFF_TREE_TYPES {
    RAW_DATA = "RAW DATA",
    PATCH_DATA = "PATCH DATA",
    FILE_STATS = "FILE STATS",
    NO_SHOW = "noshow",
}

export interface GitDiffTreeData {
    toFile: string;
    status: PATCH_SET_TYPES;
}
