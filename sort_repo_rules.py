"""按仓库名排序项目目录下的 repo_rules.json。"""

import json
import os
import stat
import tempfile
from pathlib import Path


RULES_FILE = Path(__file__).resolve().parent / "repo_rules.json"


def repository_sort_key(full_name: str) -> tuple[str, str, str]:
    """生成按 repo 名称排序的键，并校验 owner/repo 格式。"""
    if full_name.count("/") != 1:
        raise ValueError(f"仓库名必须使用 owner/repo 格式: {full_name}")

    owner, repo = full_name.split("/", 1)
    if not owner or not repo:
        raise ValueError(f"仓库名必须使用 owner/repo 格式: {full_name}")

    return repo.casefold(), full_name.casefold(), full_name


def sort_rules(rules: dict) -> dict:
    """按斜杠后的仓库名排序，忽略字母大小写。"""
    for full_name, rule in rules.items():
        if not isinstance(full_name, str):
            raise ValueError("仓库名必须是字符串")
        if not isinstance(rule, dict):
            raise ValueError(f"{full_name} 的规则必须是 JSON 对象")

    return dict(
        sorted(
            rules.items(),
            key=lambda item: repository_sort_key(item[0]),
        )
    )


def load_rules(path: Path) -> dict:
    """读取并校验规则文件的顶层结构。"""
    with path.open(encoding="utf-8") as file:
        rules = json.load(file)

    if not isinstance(rules, dict):
        raise ValueError("规则文件的顶层必须是 JSON 对象")
    return rules


def save_rules_atomically(path: Path, rules: dict) -> None:
    """在同一目录写入临时文件，再原子替换原规则文件。"""
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as file:
            json.dump(rules, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        original_mode = stat.S_IMODE(path.stat().st_mode)
        temporary_path.chmod(original_mode)
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def main() -> int:
    try:
        rules = load_rules(RULES_FILE)
        sorted_rules = sort_rules(rules)
        if list(rules) == list(sorted_rules):
            print(f"无需调整，规则已经有序: {RULES_FILE}")
            return 0

        save_rules_atomically(RULES_FILE, sorted_rules)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"排序失败: {error}")
        return 1

    print(f"排序完成，共 {len(sorted_rules)} 个仓库: {RULES_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
