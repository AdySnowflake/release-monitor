"""按仓库名排序项目目录下的 repo_rules.json。"""

import json
from pathlib import Path

RULES_FILE = Path(__file__).resolve().parent / "repo_rules.json"


def repository_sort_key(full_name: str) -> tuple[str, str, str]:
    """生成按 repo 名称排序的键。"""
    repo = full_name.split("/", 1)[-1]
    return repo.casefold(), full_name.casefold(), full_name


def sort_rules(rules: dict) -> dict:
    """按斜杠后的仓库名排序，忽略字母大小写。"""
    return dict(
        sorted(
            rules.items(),
            key=lambda item: repository_sort_key(item[0]),
        )
    )


def load_rules(path: Path) -> dict:
    """读取规则文件。"""
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    rules = load_rules(RULES_FILE)
    sorted_rules = sort_rules(rules)
    if list(rules) == list(sorted_rules):
        print(f"无需调整，规则已经有序: {RULES_FILE}")
        return 0

    with RULES_FILE.open("w", encoding="utf-8") as file:
        json.dump(sorted_rules, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(f"排序完成，共 {len(sorted_rules)} 个仓库: {RULES_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
