from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
import re


KANA_FIELD_RE = re.compile(r'("kana"\s*:\s*")([^"]*)(")')


@dataclass
class Hit:
    file: str
    item_index: int
    word_id: str | int | None
    expression: str | None
    original_kana: str
    fixed_kana: str
    replacements: int


@dataclass
class ApplyStat:
    file: str
    replacements: int
    backup: str | None


def is_kana_char(ch: str) -> bool:
    if not ch:
        return False
    code = ord(ch)
    return (0x3041 <= code <= 0x3096) or (0x30A1 <= code <= 0x30FA) or ch == "ー"


def fix_kana_value(value: str) -> tuple[str, int]:
    out: list[str] = []
    replaced = 0
    prev: str | None = None
    for ch in value:
        if ch == "一" and prev is not None and is_kana_char(prev):
            out.append("ー")
            replaced += 1
        else:
            out.append(ch)
        prev = ch
    return "".join(out), replaced


def collect_json_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix.lower() == ".json" else []
    return sorted(target.rglob("*.json"))


def iter_word_items(data: object) -> list[tuple[int, dict]]:
    if isinstance(data, list):
        return [(idx, item) for idx, item in enumerate(data) if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("items", "data", "words", "list"):
            sub = data.get(key)
            if isinstance(sub, list):
                return [(idx, item) for idx, item in enumerate(sub) if isinstance(item, dict)]
    return []


def scan_file(file_path: Path) -> list[Hit]:
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    hits: list[Hit] = []
    for idx, item in iter_word_items(payload):
        kana = item.get("kana")
        if not isinstance(kana, str) or "一" not in kana:
            continue
        fixed, count = fix_kana_value(kana)
        if count == 0 or fixed == kana:
            continue
        hits.append(
            Hit(
                file=str(file_path),
                item_index=idx,
                word_id=item.get("id"),
                expression=item.get("expression"),
                original_kana=kana,
                fixed_kana=fixed,
                replacements=count,
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
    total_replacements = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal total_replacements
        original = match.group(2)
        fixed, count = fix_kana_value(original)
        total_replacements += count
        return f"{match.group(1)}{fixed}{match.group(3)}"

    replaced_text = KANA_FIELD_RE.sub(repl, text)
    if total_replacements == 0:
        return ApplyStat(file=str(file_path), replacements=0, backup=None)

    backup_path_str: str | None = None
    if backup_root is not None:
        backup_path = build_backup_path(file_path, backup_root)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text(text, encoding="utf-8")
        backup_path_str = str(backup_path)

    file_path.write_text(replaced_text, encoding="utf-8")
    return ApplyStat(file=str(file_path), replacements=total_replacements, backup=backup_path_str)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="审查 kana 字段中的「一」并替换为「ー」")
    parser.add_argument(
        "targets",
        nargs="*",
        default=["e:/AndroidProjects/日语Word/new_word", "e:/AndroidProjects/日语Word/old_word"],
        help="目标 JSON 文件或目录，默认 new_word + old_word",
    )
    parser.add_argument("--output", help="输出 JSON 报告路径（仅写报告，不改源数据）")
    parser.add_argument("--show", type=int, default=200, help="终端最多展示多少条命中")
    parser.add_argument("--apply", action="store_true", help="一键应用替换并写回文件")
    parser.add_argument(
        "--backup-dir",
        default="e:/AndroidProjects/日语Word/.trae/kana_ichi_backups",
        help="备份根目录（仅 apply 生效）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    targets = [Path(t) for t in args.targets]
    for t in targets:
        if not t.exists():
            raise SystemExit(f"错误: 目标不存在 -> {t}")

    files: list[Path] = []
    for t in targets:
        files.extend(collect_json_files(t))
    files = sorted(set(files))
    if not files:
        raise SystemExit("错误: 未找到 JSON 文件")

    all_hits: list[Hit] = []
    per_file: dict[str, int] = {}
    per_dir: dict[str, int] = {}

    for file in files:
        hits = scan_file(file)
        if not hits:
            continue
        all_hits.extend(hits)
        per_file[str(file)] = sum(h.replacements for h in hits)
        try:
            owner = str(next(p for p in targets if file.is_relative_to(p)))
        except StopIteration:
            owner = str(file.parent)
        per_dir[owner] = per_dir.get(owner, 0) + per_file[str(file)]

    sorted_files = sorted(per_file.items(), key=lambda x: x[1], reverse=True)
    sorted_dirs = sorted(per_dir.items(), key=lambda x: x[1], reverse=True)
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
        per_dir = {}
        for file in files:
            hits = scan_file(file)
            if not hits:
                continue
            all_hits.extend(hits)
            per_file[str(file)] = sum(h.replacements for h in hits)
            try:
                owner = str(next(p for p in targets if file.is_relative_to(p)))
            except StopIteration:
                owner = str(file.parent)
            per_dir[owner] = per_dir.get(owner, 0) + per_file[str(file)]
        sorted_files = sorted(per_file.items(), key=lambda x: x[1], reverse=True)
        sorted_dirs = sorted(per_dir.items(), key=lambda x: x[1], reverse=True)

    print("=== kana「一」->「ー」审查结果 ===")
    print("目标:")
    for t in targets:
        print(f"  - {t}")
    if args.apply:
        print("模式: apply（已写回）")
        print(f"备份根目录: {backup_root}")
        print(f"改动文件数: {len(apply_stats)}")
        print(f"总替换数: {sum(s.replacements for s in apply_stats)}")
    print(f"扫描文件数: {len(files)}")
    print(f"命中文件数: {len(sorted_files)}")
    print(f"总替换数（命中统计）: {sum(per_file.values())}")

    if sorted_dirs:
        print()
        print("按目录统计（降序）:")
        for d, count in sorted_dirs:
            print(f"  {count:>5}  {d}")

    if sorted_files:
        print()
        print("按文件统计（降序）:")
        for file, count in sorted_files:
            print(f"  {count:>5}  {file}")

    if all_hits:
        print()
        print(f"命中明细（最多显示 {args.show} 条）:")
        for hit in all_hits[: args.show]:
            word = f"{hit.expression}" if hit.expression else "-"
            wid = f"{hit.word_id}" if hit.word_id is not None else "-"
            print(
                f"- {hit.file} | idx={hit.item_index} id={wid} {word} | {hit.original_kana} -> {hit.fixed_kana}"
            )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "targets": [str(t) for t in targets],
            "total_files": len(files),
            "files_with_hits": len(sorted_files),
            "total_replacements": sum(per_file.values()),
            "applied": args.apply,
            "apply_stats": [asdict(s) for s in apply_stats],
            "dir_stats": [{"dir": d, "count": c} for d, c in sorted_dirs],
            "file_stats": [{"file": f, "count": c} for f, c in sorted_files],
            "hits": [asdict(h) for h in all_hits],
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print()
        print(f"报告已写入: {output_path}")


if __name__ == "__main__":
    main()
