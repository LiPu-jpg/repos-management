# 组织仓库管理脚本

[中文](README.zh-CN.md) | [English](README.md)

</div>

该仓库中的脚本旨在管理组织内的仓库，特别是 HITSZ-OpenAuto 组织。它们简化了获取仓库名称、批准拉取请求、添加工作流以及管理许可证和密钥等任务。

## 环境要求

- 操作系统：Linux
- 工具依赖：
  - Git
  - [GitHub CLI](https://cli.github.com/)
  - Python 3（推荐 3.9 及以上）

## 创建 Personal Access Token

1. 登录 GitHub CLI

    ```bash
    gh auth login
    ```

2. 在 GitHub 中创建 Token：<https://github.com/settings/tokens/new>

3. 权限要求：至少包含 `repo` 和 `workflow`

4. 在 macOS 或 Linux 系统上导出环境变量

   ```bash
   export PERSONAL_ACCESS_TOKEN=<your_token_here>
   ```

5. 要运行 shell 脚本，请使用以下命令格式：

   ```bash
   bash ./scripts/<script_name>.sh
   ```

## 脚本说明

### fetch_repos.py

获取所有仓库名（排除 'HITSZ-OpenAuto'、'.github' 与 'hoa-moe'）

### repos_list.txt

组织下所有仓库的列表

- 注意：行尾序列应为 LF（Linux 换行符）

### approve_pr.sh

批量批准 [`repos_list.txt`](./repos_list.txt) 下所有仓库的最新 PR

- 通常用于更新仓库的 workflow 等

### add_workflow.sh

批量为 [`repos_list.txt`](./repos_list.txt) 下所有仓库添加/覆写 workflow 文件。文件内容来自线上仓库 `HITSZ-OpenAuto/repos-management` 根目录下的 `call_worktree_update.yml` 文件

### pull_or_clone.py

对所有仓库执行：

- 若本地存在对应文件夹 → 拉取主分支
- 若不存在 → 克隆仓库
- 可通过 `bypass_list` 列表指定排除的仓库

### collect_worktree_info.sh

收集仓库文件信息（含文件名、大小、修改时间等），保存为 `.json` 格式文件

### add_licenses.py

批量为 [`repos_list.txt`](./repos_list.txt) 下所有仓库添加许可证文件

### add_secrets.py

批量为 [`repos_list.txt`](./repos_list.txt) 下所有仓库添加 Secrets
