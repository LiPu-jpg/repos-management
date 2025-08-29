<div align="center">

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

1. 在 GitHub 网页版的 `Settings` → `Developer settings` → `Personal access tokens` 中创建 Token

2. 权限要求：至少包含 `repo` 和 `workflow`

3. 保存至 `.env` 文件：

   ```bash
   PERSONAL_ACCESS_TOKEN=<your_token_here>
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

批量为 [`repos_list.txt`](./repos_list.txt) 下所有仓库添加/覆写 workflow 文件

- 若需覆写，请将更新内容写在 `cat << EOF` 后面

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