# Contributing Guide

Wizarr is proud to be an open-source project. We welcome any contributions made by the community to the project.

## Getting Started

We highly recommend joining our Discord before beginning your work. There, you can discuss with the development team about what you'd like to contribute to verify it is not already in progress and avoid duplicate work.

## Prerequisites

- Python 3.10+
- pip
- npm
- node

## Guidelines

We require following conventional commit guidelines in relation to commit messages and branch naming.

[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)

[Branch and Commit Conventions](https://dev.to/varbsan/a-simplified-convention-for-naming-branches-and-commits-in-git-il4)

## Contributing to Wizarr

We highly recommend using VSCode as your IDE. There is a code workspace already created to assist in organizing the project.

1. Fork the repository in GitHub
2. Clone your forked repository with `git clone git@github.com:<YOUR_USERNAME>/wizarr.git`
3. Move into the directory `cd wizarr`
4. Run the script to setup your local environment: `./scripts/setup-build-environment.sh`
5. Use VSCode and open the `develop.code-workspace` file under File -> Open Workspace from File, or type `code develop.code-workspace` in your terminal.
6. Inside the Nx Console panel of VSCode, you have access to the project targets. Run the build target for both wizarr-backend and wizarr-frontend. Then run the serve target to begin your work.
7. Visit http://127.0.0.1:5173 (Frontend) and http://127.0.0.1:5000 (Backend) to see your changes in realtime.
8. Create a new branch from 'develop' following conventions, commit your work, and open a PR against the 'develop' branch when you are ready for the team to review your contribution.
