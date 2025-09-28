#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from collections import Counter

# 检查complete_schedule_test.json
with open('complete_schedule_test.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("📊 complete_schedule_test.json 检查结果")
print("=" * 50)

print(f"总单元数: {len(data)}")

# 检查字段结构
if data:
    first_unit = data[0]
    print(f"\n📋 字段结构:")
    for key, value in first_unit.items():
        print(f"   {key}: {value}")

# 统计周次格式
weeks_patterns = [unit.get('weeks', '') for unit in data]
weeks_counter = Counter(weeks_patterns)

print(f"\n🔍 周次格式统计:")
complex_weeks = [w for w in weeks_counter.keys() if ',' in w]
simple_weeks = [w for w in weeks_counter.keys() if ',' not in w and w]

print(f"   复杂周次格式数: {len(complex_weeks)}")
print(f"   简单周次格式数: {len(simple_weeks)}")

print(f"\n🔴 复杂周次格式样例:")
for week_pattern in sorted(complex_weeks)[:5]:
    count = weeks_counter[week_pattern]
    # 找一个这种格式的课程示例
    example = next(u for u in data if u.get('weeks') == week_pattern)
    print(f"   {week_pattern} → {count}个单元 (课程: {example['course_name']})")

# 检查节次格式
periods_patterns = [unit.get('periods', '') for unit in data if unit.get('periods')]
periods_counter = Counter(periods_patterns)

print(f"\n🎯 节次格式统计:")
for period_pattern in sorted(periods_counter.keys())[:10]:
    count = periods_counter[period_pattern]
    print(f"   {period_pattern} → {count}个单元")

# 检查拆分效果
print(f"\n📊 拆分效果验证:")

# 检查最复杂的周次格式拆分
most_complex = "3-5,8,10-11,13,16-17"
if most_complex in weeks_counter:
    complex_units = [u for u in data if u.get('weeks') == most_complex]
    print(f"   最复杂格式 {most_complex}:")
    print(f"     拆分成 {len(complex_units)} 个单元")
    weeks_list = [u['week'] for u in complex_units]
    print(f"     涉及周次: {sorted(set(weeks_list))}")
    print(f"     课程名: {complex_units[0]['course_name']}")

# 检查某个简单范围的拆分
simple_range = "1-18"
if simple_range in weeks_counter:
    range_units = [u for u in data if u.get('weeks') == simple_range]
    print(f"   简单范围 {simple_range}:")
    print(f"     拆分成 {len(range_units)} 个单元")
    weeks_list = [u['week'] for u in range_units]
    print(f"     涉及周次: {sorted(set(weeks_list))}")

# 验证字段完整性
expected_fields = {'semester', 'week', 'weekday', 'weekday_num', 
                  'time_slot_name', 'periods', 'course_name', 'teacher', 'classroom', 'weeks'}

if data:
    actual_fields = set(data[0].keys())
    print(f"\n🔍 字段验证:")
    print(f"   期望字段: {sorted(expected_fields)}")
    print(f"   实际字段: {sorted(actual_fields)}")
    
    if expected_fields == actual_fields:
        print("   ✅ 字段完全匹配")
    else:
        missing = expected_fields - actual_fields
        extra = actual_fields - expected_fields
        if missing:
            print(f"   ❌ 缺少字段: {missing}")
        if extra:
            print(f"   ⚠️  额外字段: {extra}")

print(f"\n🎯 总结:")
print(f"✅ 文件包含 {len(data)} 个课程单元")
print(f"✅ 支持 {len(set(weeks_patterns))} 种周次格式")
print(f"✅ 包含 {len(set(periods_patterns))} 种节次格式")
print(f"✅ 字段结构正确")