#!/usr/bin/env python3
import subprocess
import json
import sys
import os
import logging
from pathlib import Path
import re
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def cmd(cmds, cwd=None, allow_fail=False) -> bytes:
    try:
        logger.debug(f"run: {cmds}")
        result = subprocess.run(
            cmds,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            cwd=cwd,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.warning(f"Error executing git command: {cmds}")
        logger.warning(f"Error stdout: {e.stdout.strip()}")
        logger.warning(f"Error stderr: {e.stderr.strip()}")
        logger.warning(f"Error code: {e.returncode}")
        logger.warning(f"Error message: {e}")
        if allow_fail:
            # Don't exit on failure, just re-raise
            raise
        else:
            sys.exit(1)


def return_code(cmds) -> int:
    logger.debug(f"test: {cmds}")
    result = subprocess.run(
        cmds,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=False,
    )
    return result.returncode


def is_digit_in_ascii(c: int) -> bool:
    return ord("0") <= c <= ord("9")


def decode_git_ls_tree_path(content: bytes) -> str:
    escaped_array = []

    if content.startswith(b'"'):
        if not content.endswith(b'"'):
            raise RuntimeError(
                f"Invalid git ls-tree output: path ill-quoted: `{content}`"
            )
        content = content[1:-1]

    idx, end = 0, len(content)
    while idx < end:
        c = content[idx]
        if c != ord(b"\\"):
            escaped_array.append(c)
            idx += 1
            continue

        # now c is '\', check escaping
        idx += 1
        if idx >= end:
            raise RuntimeError(
                f"Invalid git ls-tree output: path ill-escaped, ending with hangling backslash: `{content}`"
            )
        escaped_alpha = content[idx]
        # check octal esaped character
        if is_digit_in_ascii(escaped_alpha):
            value_literal = content[idx : idx + 3]
            if idx + 3 > end or not all(is_digit_in_ascii(c) for c in value_literal):
                raise RuntimeError(
                    f"Invalid git ls-tree output: path ill-escaped, wrong octal escape sequence: `{content}`"
                )
            value = int(value_literal, 8)
            escaped_array.append(value)
            idx += 3
            continue
        # check 'normal' C-liked escaped character
        try:
            value_bytes = eval(rf'b"\{chr(escaped_alpha)}"')
            assert isinstance(value_bytes, bytes) and len(value_bytes) == 1
        except SyntaxWarning or SyntaxError or AssertionError:
            raise RuntimeError(
                f"Invalid git ls-tree output: path ill-escaped, wrong escaped character: `{content}`"
            )
        escaped_array.append(ord(value_bytes))
        idx += 1

    assert idx == end
    return bytes(escaped_array).decode("utf-8")


def collect_info_for_head_commit() -> dict:
    # 构建 commit-graph 以加速 git log
    cmd(["git", "commit-graph", "write", "--reachable"])

    # 准备存储文件信息的列表, path -> {size (bolb-size), time (commit-date), hash (commit-hash)}
    files_data: dict[str, dict] = {}

    # 获取文件列表和大小
    ls_tree_output = cmd(
        ["git", "ls-tree", "-r", "HEAD", "--format=%(objectsize)%x00%(path)"]
    )
    for line in ls_tree_output.splitlines():
        size, path_raw = line.split(b"\0")
        # print(path, len(path))
        path = decode_git_ls_tree_path(path_raw)
        # print(path_str, len(path_str))
        files_data[path] = {"size": int(size)}

    # 获取提交时间和哈希
    files_path = list(files_data.keys())
    for file_path in files_path:
        time_hash = cmd(
            ["git", "log", "-1", "--format=%cd%x00%H", "--date=unix", "--", file_path]
        )
        timestamp, commit_hash = time_hash.split(b"\0")

        files_data[file_path]["time"] = int(timestamp)
        files_data[file_path]["hash"] = commit_hash.decode("ascii")

    return files_data


def prepare_or_checkout_to_worktree_branch(name: str):
    try:
        cmd(["git", "checkout", name], allow_fail=True)
    except subprocess.CalledProcessError:
        logger.info(f"Creating new empty orphan worktree branch `{name}`")
        cmd(["git", "checkout", "--orphan", name])
        cmd(["git", "rm", "-rf", "."])
    logger.info(f"Switched to worktree branch `{name}`")


def prepare_user_info():
    logger.info("Setting user info")
    cmd(["git", "config", "--local", "user.email", "action@github.com"])
    cmd(["git", "config", "--local", "user.name", "GitHub Actions"])


def save_json(path: str | Path, obj):
    if isinstance(path, str):
        path = Path(path)

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    logger.info(f"Worktree info saved to `{path}`")


def collect_info_and_saved_to_another_branch(worktree_branch_name: str):
    info_commit_hash = cmd(["git", "rev-parse", "HEAD"]).decode("ascii")
    info = collect_info_for_head_commit()

    prepare_or_checkout_to_worktree_branch(worktree_branch_name)
    save_json("worktree.json", info)
    save_json(f"history/{info_commit_hash}.json", info)

    prepare_user_info()
    cmd(["git", "add", "worktree.json", "history/"])
    cmd(["git", "commit", "-m", f"update worktree info for <|{info_commit_hash}|>"])
    cmd(["git", "push", "--set-upstream", "origin", worktree_branch_name])
    logger.info("Worktree info collected and saved to another branch")


def get_last_worktree_info_target(
    worktree_branch_name: str, use_remote: bool = True
) -> str | None:
    PAT = re.compile(rb"<\|([a-z0-9]+)\|>")
    try:
        branch_name = ("origin/" if use_remote else "") + worktree_branch_name
        commit_message = cmd(
            ["git", "log", "-1", "--oneline", branch_name, "--"],
            allow_fail=True,
        )
    except subprocess.CalledProcessError as e:
        logger.info(f"Worktree branch `{worktree_branch_name}` is empty")
        return None

    logger.info(f"Last commit message: `{commit_message}`")
    match_result = PAT.findall(commit_message)
    if len(match_result) != 1:
        logger.info("Last commit message does not contain worktree info target")
        logger.debug(match_result)
        return None
    else:
        hash = match_result[0].decode("ascii")
        logger.info(f"matched last worktree info target: `{hash}`")
        return hash


def main():
    # assume worktree branch name
    worktree_branch_name = "worktree"

    # get last worktree info target
    last_worktree_info_target = get_last_worktree_info_target(worktree_branch_name)

    # if worktree branch is up-to-date, do nothing
    last_master_branch_commit = cmd(["git", "rev-parse", "HEAD"]).decode("ascii")
    logger.debug(f"last master branch commit: `{last_master_branch_commit}`")
    if last_worktree_info_target == last_master_branch_commit:
        logger.info("Worktree branch is up-to-date, do nothing")
        return

    # collect info and save to another branch
    collect_info_and_saved_to_another_branch(worktree_branch_name)


if __name__ == "__main__":
    logger.level = logging.DEBUG
    # print hash of script myself
    logger.info(
        f"Script hash: `{hashlib.sha256(open(__file__).read().encode('utf-8')).hexdigest()}`"
    )
    main()
