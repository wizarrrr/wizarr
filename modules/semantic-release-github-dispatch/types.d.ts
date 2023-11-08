// @ts-ignore
import { Config as SemanticReleaseConfig, PublishContext as SemanticReleaseContext, Result as SemanticReleaseResult, Commit } from "semantic-release";

// @ts-ignore
export interface Context extends SemanticReleaseContext, SemanticReleaseConfig, SemanticReleaseResult {}

export interface Config {
    repo: string;
    owner: string;
    githubToken: string;
    eventName: string;
    payload: {
        version?: string;
        image: string;
        branch: string;
    };
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
