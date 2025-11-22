<div align="center">

# Organization Repository Management Scripts

[English](README.md) | [中文](README.zh-CN.md)

</div>

<br>

The scripts in this repository are designed to manage repositories within an organization, specifically for the HITSZ-OpenAuto organization. They facilitate tasks such as fetching repository names, approving pull requests, adding workflows, and managing licenses and secrets.

## Environment Requirements

- Operating System: Linux
- Tool Dependencies:
  - Git
  - [GitHub CLI](https://cli.github.com/)
  - Python 3 (Recommended 3.9 or higher)

## Create Personal Access Token

1. Log in to GitHub CLI

    ```bash
    gh auth login
    ```

2. Create a Token in GitHub: <https://github.com/settings/tokens/new>

3. Required Permissions: At least `repo` and `workflow`

4. Export an environment variable on macOS or Linux systems

   ```bash
   export PERSONAL_ACCESS_TOKEN=<your_token_here>
   ```

5. To run a shell script, use the following command format:

   ```bash
   bash ./scripts/<script_name>.sh
   ```

## Script Documentation

### fetch_repos.py

Fetch all repository names (excluding 'HITSZ-OpenAuto', '.github', and 'hoa-moe')

### repos_list.txt

List of all repositories in the organization

- Note: Line endings should be LF (Linux newline character)

### approve_pr.sh

Batch approve the latest PRs for all repositories listed in [`repos_list.txt`](./repos_list.txt)

- Typically used for updating repository workflows

### add_workflow.sh

Batch add/overwrite workflow files for all repositories listed in [`repos_list.txt`](./repos_list.txt). The workflow content is sourced from the root-level `call_worktree_update.yml` in the online repository `HITSZ-OpenAuto/repos-management`

### pull_or_clone.py

Perform the following for all repositories:

- If the local folder exists → Pull the main branch
- If the folder doesn't exist → Clone the repository
- Exclude specific repositories using the `bypass_list` list

### collect_worktree_info.sh

Collect repository file information (including filenames, sizes, and modification times), saved as a `.json` formatted file

### add_licenses.py

Batch add license files to all repositories listed in [`repos_list.txt`](./repos_list.txt)

### add_secrets.py

Batch add Secrets to all repositories listed in [`repos_list.txt`](./repos_list.txt)