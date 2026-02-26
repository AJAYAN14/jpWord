# Furigana 审查报告格式

审查脚本可通过 `--output <path>` 写出 JSON 报告，便于中断后恢复。

## 顶层字段

- `target`: 本次审查目标（文件或目录）
- `total_files`: 已审查文件数量
- `total_errors`: 汇总错误数
- `results`: 每个文件的结果数组

## results[] 字段

- `file`: 文件路径
- `total_entries`: 条目数
- `entries_with_errors`: 有错误的条目数
- `total_examples`: 检查过的例句数
- `examples_with_errors`: 有错误的例句数
- `errors`: 错误明细数组

## errors[] 字段

- `entry_idx`: 条目索引
- `expression`: 条目标识词
- `example_idx`: 例句索引
- `kanji`: 未注音汉字
- `context`: 汉字附近上下文
- `full_text`: 完整原句

## 中断恢复建议

1. 先读取上一次报告中 `results[].errors` 继续修复。
2. 修复一批后重新运行脚本并覆盖 `--output` 文件。
3. 若新报告 `total_errors` 仍大于 0，继续循环直到归零。
