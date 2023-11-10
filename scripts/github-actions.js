/**
 * This script allows you to delete actions for a workflow in a Github repository.
 * 
 * Just run `node scripts/github-actions.js` and follow the prompts.
 * 
 * You will need to create a `github_token.txt` file in the `scripts` directory
 * with a Github Personal Access Token with the `repo` scope.
 * 
 * USE THIS SCRIPT AT YOUR OWN RISK! I AM NOT RESPONSIBLE FOR ANY DATA LOSS!
 * 
 * MIT License (c) 2023 Ashley Bailey
 */
const run = async () => {
    const { Octokit } = require("octokit");
    const prompts = require('prompts');

    // Read Github Token from github_token.txt
    const getToken = () => {
        const fs = require("fs");
        const path = require("path");
        const filePath = path.join(__dirname, "github_token.txt");
        const token = fs.readFileSync(filePath, "utf8");
        return token;
    };

    // Get authenticated Octokit client instance
    const getOctokit = () => {
        const token = getToken();
        return new Octokit({ auth: token });
    }

    // Get a list of all repositories for the authenticated user
    /**
     * @param {Octokit} octokit
     * @param {string} type
     * @param {string} org
     * @return {Promise<import("@octokit/types").OctokitResponse<import("@octokit/types").ReposListForAuthenticatedUserResponse>>}
     */
    const getRepositories = async (octokit, type, org = null) => {
        if (type === 'personal') {
            return await octokit.rest.repos.listForAuthenticatedUser();
        } else if (type === 'organization') {
            return await octokit.rest.repos.listForOrg({
                org: org
            });
        }
    }

    // Get a list of all organizations for the authenticated user
    /**
     * @param {Octokit} octokit
     * @return {Promise<import("@octokit/types").OctokitResponse<import("@octokit/types").OrgsListResponse>>}
     */
    const getOrganizations = async (octokit) => {
        return await octokit.rest.orgs.listForAuthenticatedUser();
    }

    /**
     * @param {string} username
     */
    const resetCLI = (username) => {
        console.clear();
        console.log(`Hello, ${username}!`);
        console.log(`Welcome to the Github Actions CLI!\n`);
    }

    const octokit = getOctokit();
    const { data: { login: username } } = await octokit.rest.users.getAuthenticated();

    resetCLI(username);

    // Get use to select an account or organization
    const { account } = await prompts({
        type: 'select',
        name: 'account',
        message: 'Select an account or organization',
        choices: [
            { title: 'Personal', value: 'personal' },
            { title: 'Organization', value: 'organization' },
        ],
        initial: 0
    });

    resetCLI(username);

    // Get a list of all organizations for the authenticated user if the user selected organization
    const { data: organizations } = account === 'organization' ? await getOrganizations(octokit) : { data: [] };

    // Get user to select an organization if the user selected organization
    const { organization } = account === 'organization' ? await prompts({
        type: 'select',
        name: 'organization',
        message: 'Select an organization',
        choices: organizations.map(({ login }) => ({ title: login, value: login })),
        initial: 0
    }) : { organization: null };

    resetCLI(username);

    // Get a user to select a repository for the selected account or organization
    const { data: repositories } = await getRepositories(octokit, account, organization);

    const { repository } = await prompts({
        type: 'select',
        name: 'repository',
        message: 'Select a repository',
        choices: repositories.map(({ name }) => ({ title: name, value: name })),
        initial: 0
    });

    resetCLI(username);

    // Get user to select an action to perform on the selected repository
    const { action } = await prompts({
        type: 'select',
        name: 'action',
        message: 'Select an action',
        choices: [
            { title: 'Delete actions for a workflow', value: 'delete' },
            // { title: 'Delete all failed actions', value: 'delete-failed' },
            // { title: 'Delete all successful actions', value: 'delete-successful' },
            // { title: 'Delete all cancelled actions', value: 'delete-cancelled' },
            // { title: 'Delete all actions', value: 'delete-all' },
        ],
        initial: 0
    });

    resetCLI(username);

    // Get a list of all actions for the selected workflow
    const { data: { workflows } } = await octokit.rest.actions.listRepoWorkflows({
        owner: organization || username,
        repo: repository
    });

    // Get user to select a workflow
    const { workflow } = await prompts({
        type: 'select',
        name: 'workflow',
        message: 'Select a workflow',
        choices: workflows.map(({ name }) => ({ title: name, value: name })),
        initial: 0
    });

    resetCLI(username);

    // Get some information about the selected workflow
    const { data: { total_count, workflow_runs } } = await octokit.rest.actions.listWorkflowRuns({
        owner: organization || username,
        repo: repository,
        workflow_id: workflows.find(({ name }) => name === workflow).id,
    });

    // Show a warning message if they are about to delete all actions for the selected workflow
    // with a count of the number of actions that will be deleted
    const { confirm } = await prompts({
        type: 'confirm',
        name: 'confirm',
        message: `Are you sure you want to delete all actions for the ${workflow} workflow?\n  This will delete ${total_count} actions.`,
        initial: false
    });

    if (!confirm) return;

    resetCLI(username);

    // Delete all actions for the selected workflow
    Object.values(workflow_runs).forEach(async ({ id }) => {
        console.log(`Deleting action ${id}...`);
        await octokit.rest.actions.deleteWorkflowRun({ owner: organization || username, repo: repository, run_id: id });
    });
}

run()