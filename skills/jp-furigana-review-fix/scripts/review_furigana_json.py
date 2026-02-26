#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审查日语词汇 JSON 文件中 examples 例句的注音情况。
规则：凡是未被 "汉字[读音]" 注音块覆盖的汉字，都会被标记为错误。
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

KANJI_PATTERN = re.compile(r"[一-龥々〆〤]")
RUBY_PATTERN = re.compile(r"([一-龥々〆〤]+)\[([^\]]+)\]")


def has_unannotated_kanji(text: str) -> tuple[bool, list[dict[str, Any]]]:
    """检查文本中是否有未注音汉字，返回 (has_error, errors)。"""
    errors: list[dict[str, Any]] = []
    text_length = len(text)

    annotated_positions = [False] * text_length
    for match in RUBY_PATTERN.finditer(text):
        start, end = match.span()
        for i in range(start, end):
            annotated_positions[i] = True

    for match in KANJI_PATTERN.finditer(text):
        pos = match.start()
        if annotated_positions[pos]:
            continue

        context_start = max(0, pos - 10)
        context_end = min(text_length, pos + 10)
        errors.append(
            {
                "position": pos,
                "kanji": match.group(0),
                "context": text[context_start:context_end],
                "full_text": text,
            }
        )

    return len(errors) > 0, errors


def review_json_file(filepath: Path) -> dict[str, Any]:
    """审查单个 JSON 文件。"""
    results: dict[str, Any] = {
        "file": str(filepath),
        "total_entries": 0,
        "entries_with_errors": 0,
        "total_examples": 0,
        "examples_with_errors": 0,
        "errors": [],
    }

    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        results["error"] = f"无法解析JSON: {exc}"
        return results

    entries = data if isinstance(data, list) else [data]
    results["total_entries"] = len(entries)

    for entry_idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue

        expression = entry.get("expression", f"条目_{entry_idx}")
        examples = entry.get("examples", [])
        if not isinstance(examples, list) or not examples:
            continue

        entry_has_error = False

        for ex_idx, example in enumerate(examples):
            if not isinstance(example, dict):
                continue

            ja_text = example.get("ja") or example.get("japanese", "")
            if not isinstance(ja_text, str) or not ja_text:
                continue

            results["total_examples"] += 1
            has_error, error_details = has_unannotated_kanji(ja_text)
            if not has_error:
                continue

            results["examples_with_errors"] += 1
            entry_has_error = True

            for err in error_details:
                results["errors"].append(
                    {
                        "entry_idx": entry_idx,
                        "expression": expression,
                        "example_idx": ex_idx,
                        "kanji": err["kanji"],
                        "context": err["context"],
                        "full_text": ja_text,
                    }
                )

        if entry_has_error:
            results["entries_with_errors"] += 1

    return results


def collect_json_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(target.glob("*.json"))


def print_single_result(result: dict[str, Any]) -> None:
    filename = Path(result["file"]).name
    print("=" * 80)
    print(f"审查文件: {filename}")
    print("=" * 80)

    if result.get("error"):
        print(f"错误: {result['error']}")
        print("=" * 80)
        return

    print(f"条目数: {result['total_entries']}")
    print(f"例句数: {result['total_examples']}")
    print(f"问题条目: {result['entries_with_errors']}")
    print(f"问题例句: {result['examples_with_errors']}")
    print(f"总错误数: {len(result['errors'])}")
    print()

    if not result["errors"]:
        print("✓ 该文件所有注音格式正确！")
        print("=" * 80)
        return

    print("详细错误列表")
    print("-" * 80)
    errors_by_entry: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for err in result["errors"]:
        key = (err["entry_idx"], err["expression"])
        errors_by_entry[key].append(err)

    for (entry_idx, expression), errors in sorted(errors_by_entry.items()):
        print(f"条目 [{entry_idx}]: {expression}")
        errors_by_example: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for err in errors:
            errors_by_example[err["example_idx"]].append(err)

        for ex_idx, ex_errors in sorted(errors_by_example.items()):
            print(f"  例句 [{ex_idx}]:")
            full_text = ex_errors[0]["full_text"]
            chars = " ".join(f"'{err['kanji']}'" for err in ex_errors)
            print(f"    原文: {full_text}")
            print(f"    未注音汉字: {chars}")
            print()

    print("=" * 80)


def print_multi_result(results: list[dict[str, Any]], target: Path) -> None:
    print("=" * 80)
    print(f"目录审查: {target}")
    print(f"文件数量: {len(results)}")
    print("=" * 80)

    total_errors = 0
    for result in results:
        file_name = Path(result["file"]).name
        if result.get("error"):
            print(f"{file_name}: 错误 -> {result['error']}")
            continue

        file_error_count = len(result["errors"])
        total_errors += file_error_count
        if file_error_count == 0:
            print(f"{file_name}: ✓ 通过")
        else:
            print(f"{file_name}: 发现 {file_error_count} 处未注音汉字")

    print("-" * 80)
    print(f"总错误数: {total_errors}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="审查 examples 例句中的日文注音")
    parser.add_argument("target", help="目标 JSON 文件或目录")
    parser.add_argument("--output", help="可选：将完整审查结果写入 JSON 文件")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target = Path(args.target)

    if not target.exists():
        raise SystemExit(f"错误: 目标不存在 -> {target}")

    files = collect_json_files(target)
    if not files:
        raise SystemExit(f"错误: 未找到 JSON 文件 -> {target}")

    results = [review_json_file(file) for file in files]

    if target.is_file():
        print_single_result(results[0])
    else:
        print_multi_result(results, target)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "target": str(target),
            "total_files": len(results),
            "total_errors": sum(len(r.get("errors", [])) for r in results if not r.get("error")),
            "results": results,
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"报告已写入: {out_path}")


if __name__ == "__main__":
    main()
