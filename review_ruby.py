#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
N3等级日语词汇JSON文件注音审查脚本
检查 examples 数组中的例句是否有汉字缺少注音
规则：最后一个汉字没有[]时才视为错误，如 大変[たいへん] 是正确的
"""

import json
import os
import re
from pathlib import Path
from collections import defaultdict


def has_unannotated_kanji(text: str) -> tuple[bool, list]:
    """
    检查文本中是否有未注音的汉字
    返回: (是否有错误, 错误详情列表)
    
    规则：
    1. 匹配 [汉字][读音] 格式
    2. 最后一个汉字如果没有注音，视为错误
    3. 平假名、片假名、标点符号不检查
    """
    errors = []
    
    # 移除来源标记如 [2010年7月]、★ 等，避免干扰检测
    # 保留原始文本用于定位
    text_clean = text
    
    # 匹配注音格式：[汉字][读音] 或 [汉字][读音]々[读音] 等
    # 注音块模式：汉字/々 followed by [读音]
    ruby_pattern = r'([一-龥々〆〤]+)\[([^\]]+)\]'
    
    # 找出所有已注音的部分
    annotated_parts = []
    for match in re.finditer(ruby_pattern, text):
        annotated_parts.append((match.start(), match.end(), match.group(0)))
    
    # 构建一个标记数组，标记哪些位置已被注音
    text_length = len(text)
    annotated_positions = [False] * text_length
    
    for start, end, _ in annotated_parts:
        for i in range(start, end):
            annotated_positions[i] = True
    
    # 检查每个汉字是否在注音范围内
    kanji_pattern = r'[一-龥々〆〤]'
    
    for match in re.finditer(kanji_pattern, text):
        pos = match.start()
        kanji = match.group(0)
        
        # 检查这个汉字是否已被注音
        if not annotated_positions[pos]:
            # 获取上下文
            context_start = max(0, pos - 10)
            context_end = min(text_length, pos + 10)
            context = text[context_start:context_end]
            
            errors.append({
                'position': pos,
                'kanji': kanji,
                'context': context,
                'full_text': text
            })
    
    return len(errors) > 0, errors


def review_json_file(filepath: str) -> dict:
    """审查单个JSON文件"""
    results = {
        'file': filepath,
        'total_entries': 0,
        'entries_with_errors': 0,
        'total_examples': 0,
        'examples_with_errors': 0,
        'errors': []
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        results['error'] = f"无法解析JSON: {e}"
        return results
    
    # 处理数组格式
    if isinstance(data, list):
        entries = data
    else:
        entries = [data]
    
    results['total_entries'] = len(entries)
    
    for entry_idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
            
        # 获取条目标识
        expression = entry.get('expression', f'条目_{entry_idx}')
        
        # 只检查 examples 字段
        examples = entry.get('examples', [])
        if not examples:
            continue
            
        entry_has_error = False
        
        for ex_idx, example in enumerate(examples):
            if not isinstance(example, dict):
                continue
                
            # 获取日语例句（可能在 ja 或 japanese 字段）
            ja_text = example.get('ja') or example.get('japanese', '')
            if not ja_text:
                continue
                
            results['total_examples'] += 1
            
            # 检查注音
            has_error, error_details = has_unannotated_kanji(ja_text)
            
            if has_error:
                results['examples_with_errors'] += 1
                entry_has_error = True
                
                for err in error_details:
                    results['errors'].append({
                        'entry_idx': entry_idx,
                        'expression': expression,
                        'example_idx': ex_idx,
                        'kanji': err['kanji'],
                        'context': err['context'],
                        'full_text': ja_text
                    })
        
        if entry_has_error:
            results['entries_with_errors'] += 1
    
    return results


def main():
    """主函数"""
    import sys
    
    # 支持命令行参数指定文件或目录
    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1])
        if target_path.is_file():
            # 审查单个文件
            print("=" * 80)
            print(f"审查文件: {target_path.name}")
            print("=" * 80)
            print()
            
            result = review_json_file(str(target_path))
            
            if result.get('error'):
                print(f"错误: {result['error']}")
                return
            
            print(f"条目数: {result['total_entries']}")
            print(f"例句数: {result['total_examples']}")
            print(f"问题条目: {result['entries_with_errors']}")
            print(f"问题例句: {result['examples_with_errors']}")
            print(f"总错误数: {len(result['errors'])}")
            print()
            
            if result['errors']:
                print("=" * 80)
                print("详细错误列表")
                print("=" * 80)
                print()
                
                # 按条目分组显示错误
                errors_by_entry = defaultdict(list)
                for err in result['errors']:
                    key = (err['entry_idx'], err['expression'])
                    errors_by_entry[key].append(err)
                
                for (entry_idx, expression), errors in sorted(errors_by_entry.items()):
                    print(f"条目 [{entry_idx}]: {expression}")
                    
                    # 按例句分组
                    errors_by_example = defaultdict(list)
                    for err in errors:
                        errors_by_example[err['example_idx']].append(err)
                    
                    for ex_idx, ex_errors in sorted(errors_by_example.items()):
                        print(f"  例句 [{ex_idx}]:")
                        full_text = ex_errors[0]['full_text']
                        print(f"    原文: {full_text}")
                        print(f"    未注音汉字: ", end='')
                        for err in ex_errors:
                            print(f"'{err['kanji']}' ", end='')
                        print()
                        print()
            else:
                print("✓ 该文件所有注音格式正确！")
            
            print("=" * 80)
            return
        else:
            # 审查目录
            target_dir = target_path
            level_name = target_dir.name
    else:
        # 默认N3目录
        target_dir = Path(r'e:\AndroidProjects\日语Word\new_word\N3')
        level_name = "N3"
    
    if not target_dir.exists():
        print(f"错误: 目录不存在 {target_dir}")
        return
    
    # 获取所有JSON文件
    json_files = sorted(target_dir.glob(f'word_{level_name.lower()}_part*.json'))
    
    if not json_files:
        print(f"错误: 在 {target_dir} 中未找到匹配的JSON文件")
        return
    
    print("=" * 80)
    print(f"{level_name}等级日语词汇JSON文件注音审查报告")
    print("=" * 80)
    print(f"审查目录: {target_dir}")
    print(f"文件数量: {len(json_files)}")
    print("=" * 80)
    print()
    
    all_results = []
    total_errors = 0
    
    for json_file in json_files:
        print(f"正在审查: {json_file.name} ...", end=' ')
        result = review_json_file(str(json_file))
        all_results.append(result)
        
        error_count = len(result['errors'])
        total_errors += error_count
        
        if error_count > 0:
            print(f"发现 {error_count} 处未注音汉字")
        else:
            print("✓ 通过")
    
    print()
    print("=" * 80)
    print("详细错误报告")
    print("=" * 80)
    print()
    
    # 输出详细错误
    for result in all_results:
        if result.get('error'):
            print(f"\n【{Path(result['file']).name}】")
            print(f"  错误: {result['error']}")
            continue
            
        if result['errors']:
            print(f"\n【{Path(result['file']).name}】")
            print(f"  条目数: {result['total_entries']}, 例句数: {result['total_examples']}")
            print(f"  问题条目: {result['entries_with_errors']}, 问题例句: {result['examples_with_errors']}")
            print()
            
            # 按条目分组显示错误
            errors_by_entry = defaultdict(list)
            for err in result['errors']:
                key = (err['entry_idx'], err['expression'])
                errors_by_entry[key].append(err)
            
            for (entry_idx, expression), errors in sorted(errors_by_entry.items()):
                print(f"  条目 [{entry_idx}]: {expression}")
                
                # 按例句分组
                errors_by_example = defaultdict(list)
                for err in errors:
                    errors_by_example[err['example_idx']].append(err)
                
                for ex_idx, ex_errors in sorted(errors_by_example.items()):
                    print(f"    例句 [{ex_idx}]:")
                    # 显示完整例句
                    full_text = ex_errors[0]['full_text']
                    print(f"      原文: {full_text}")
                    print(f"      未注音汉字: ", end='')
                    for err in ex_errors:
                        print(f"'{err['kanji']}' ", end='')
                    print()
                    print()
    
    # 汇总统计
    print()
    print("=" * 80)
    print("汇总统计")
    print("=" * 80)
    print(f"审查文件数: {len(json_files)}")
    print(f"总错误数: {total_errors}")
    
    files_with_errors = sum(1 for r in all_results if r['errors'])
    print(f"有问题文件数: {files_with_errors}")
    
    if total_errors == 0:
        print("\n✓ 所有文件的注音格式正确！")
    else:
        print(f"\n⚠ 发现 {total_errors} 处未注音汉字，需要修复")
    
    print("=" * 80)


if __name__ == '__main__':
    main()
