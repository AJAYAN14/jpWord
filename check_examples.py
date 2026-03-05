#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描所有N1-N5 JSON文件，找出例句不满3个的单词
"""

import json
import os
from pathlib import Path
from collections import defaultdict

def check_examples(directory):
    """检查目录下所有JSON文件的例句数量"""
    results = defaultdict(list)
    
    for root, dirs, files in os.walk(directory):
        for file in sorted(files):
            if file.endswith('.json'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 处理可能是数组或对象的情况
                    entries = data if isinstance(data, list) else data.get('entries', [])
                    
                    for entry in entries:
                        if not isinstance(entry, dict):
                            continue
                            
                        entry_id = entry.get('id', 'unknown')
                        expression = entry.get('expression', 'unknown')
                        examples = entry.get('examples', [])
                        
                        if len(examples) < 3:
                            level = entry.get('level', 'unknown')
                            results[filepath].append({
                                'id': entry_id,
                                'expression': expression,
                                'kana': entry.get('kana', ''),
                                'meaning': entry.get('meaning', ''),
                                'current_count': len(examples),
                                'needed': 3 - len(examples),
                                'level': level
                            })
                            
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    return results

def main():
    base_dir = "e:/AndroidProjects/日语Word/new_word"
    
    print("=" * 80)
    print("扫描所有N1-N5词汇文件，找出例句不满3个的单词")
    print("=" * 80)
    
    all_results = check_examples(base_dir)
    
    total_entries = 0
    total_needed = 0
    
    for filepath in sorted(all_results.keys()):
        entries = all_results[filepath]
        if not entries:
            continue
            
        rel_path = os.path.relpath(filepath, base_dir)
        print(f"\n【{rel_path}】")
        print("-" * 60)
        
        for entry in entries:
            total_entries += 1
            total_needed += entry['needed']
            print(f"  ID: {entry['id']}")
            print(f"  单词: {entry['expression']} ({entry['kana']})")
            print(f"  释义: {entry['meaning']}")
            print(f"  当前例句数: {entry['current_count']}, 需补充: {entry['needed']}个")
            print()
    
    print("=" * 80)
    print(f"总计: {total_entries} 个单词需要补充例句")
    print(f"共需补充: {total_needed} 个例句")
    print("=" * 80)

if __name__ == "__main__":
    main()
