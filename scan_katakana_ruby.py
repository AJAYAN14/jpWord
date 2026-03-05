#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from dataclasses import asdict, dataclass
from pathlib import Path

PATTERN = re.compile(r"([ァ-ヺー]+)\[([ぁ-ゖァ-ヺー]+)\]")


@dataclass
class Hit:
    file: str
    line: int
    column: int
    original: str
    replacement: str
    context: str


@dataclass
class ApplyStat:
    file: str
    replacements: int
    backup: str | None


def collect_json_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix.lower() == ".json" else []
    return sorted(target.rglob("*.json"))


def scan_file(file_path: Path) -> list[Hit]:
    hits: list[Hit] = []
    lines = file_path.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines, start=1):
        for match in PATTERN.finditer(line):
            katakana = match.group(1)
            original = match.group(0)
            replacement = katakana
            start = max(0, match.start() - 25)
            end = min(len(line), match.end() + 25)
            context = line[start:end]
            hits.append(
                Hit(
                    file=str(file_path),
                    line=idx,
                    column=match.start() + 1,
                    original=original,
                    replacement=replacement,
                    context=context,
                )
            )
    return hits


def build_backup_path(file_path: Path, backup_root: Path) -> Path:
    try:
        rel = file_path.relative_to(Path.cwd())
    except ValueError:
        rel = Path(file_path.name)
    return backup_root / rel


def apply_file(file_path: Path, backup_root: Path | None) -> ApplyStat:
    text = file_path.read_text(encoding="utf-8")
    replaced_text, count = PATTERN.subn(r"\1", text)
    if count == 0:
        return ApplyStat(file=str(file_path), replacements=0, backup=None)

    backup_path_str: str | None = None
    if backup_root is not None:
        backup_path = build_backup_path(file_path, backup_root)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text(text, encoding="utf-8")
        backup_path_str = str(backup_path)

    file_path.write_text(replaced_text, encoding="utf-8")
    return ApplyStat(file=str(file_path), replacements=count, backup=backup_path_str)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="扫描片假名误注音：カタカナ[かな]")
    parser.add_argument(
        "target",
        nargs="?",
        default="e:/AndroidProjects/日语Word/new_word",
        help="目标 JSON 文件或目录，默认 new_word",
    )
    parser.add_argument("--output", help="输出 JSON 报告路径（仅写报告，不改源数据）")
    parser.add_argument("--show", type=int, default=200, help="终端最多展示多少条命中")
    parser.add_argument("--apply", action="store_true", help="一键应用替换并写回文件")
    parser.add_argument(
        "--backup-dir",
        default="e:/AndroidProjects/日语Word/.trae/katakana_ruby_backups",
        help="备份根目录，默认 .trae/katakana_ruby_backups",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target = Path(args.target)
    if not target.exists():
        raise SystemExit(f"错误: 目标不存在 -> {target}")

    files = collect_json_files(target)
    if not files:
        raise SystemExit(f"错误: 未找到 JSON 文件 -> {target}")

    all_hits: list[Hit] = []
    per_file: dict[str, int] = {}

    for file in files:
        hits = scan_file(file)
        if not hits:
            continue
        all_hits.extend(hits)
        per_file[str(file)] = len(hits)

    sorted_files = sorted(per_file.items(), key=lambda x: x[1], reverse=True)
    apply_stats: list[ApplyStat] = []

    if args.apply:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_root = Path(args.backup_dir) / stamp
        for file in files:
            stat = apply_file(file, backup_root)
            if stat.replacements > 0:
                apply_stats.append(stat)

        all_hits = []
        per_file = {}
        for file in files:
            hits = scan_file(file)
            if not hits:
                continue
            all_hits.extend(hits)
            per_file[str(file)] = len(hits)
        sorted_files = sorted(per_file.items(), key=lambda x: x[1], reverse=True)

    print("=== 片假名误注音扫描结果 ===")
    print(f"目标: {target}")
    if args.apply:
        print("模式: apply（已写回）")
        print(f"备份根目录: {backup_root}")
        print(f"改动文件数: {len(apply_stats)}")
        print(f"总替换数: {sum(s.replacements for s in apply_stats)}")
    print(f"命中文件数: {len(sorted_files)}")
    print(f"总命中数: {len(all_hits)}")
    print()
    print("按文件统计（降序）:")
    for file, count in sorted_files:
        print(f"  {count:>4}  {file}")

    if all_hits:
        print()
        print(f"命中明细（最多显示 {args.show} 条）:")
        for hit in all_hits[: args.show]:
            print(
                f"- {hit.file}:{hit.line}:{hit.column} | {hit.original} -> {hit.replacement} | {hit.context}"
            )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "target": str(target),
            "total_files": len(files),
            "files_with_hits": len(sorted_files),
            "total_hits": len(all_hits),
            "applied": args.apply,
            "apply_stats": [asdict(s) for s in apply_stats],
            "file_stats": [{"file": f, "count": c} for f, c in sorted_files],
            "hits": [asdict(h) for h in all_hits],
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print()
        print(f"报告已写入: {output_path}")


if __name__ == "__main__":
    main()
