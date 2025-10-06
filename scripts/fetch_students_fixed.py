#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的学生数据提取脚本 - 正确处理分页
通过分析HTML保存第一页的表格,然后通过发送表单提交来获取第二页
"""

import requests
import json
from bs4 import BeautifulSoup
import csv
import os
import re

# 加载session信息
with open('temp/admin_session.json', 'r', encoding='utf-8') as f:
    session_data = json.load(f)

base_url = session_data['base_url']
jsessionid = session_data['cookies']['JSESSIONID']

# 创建session
session = requests.Session()
session.cookies.set('JSESSIONID', jsessionid)

def extract_students_from_html(html_content):
    """从HTML中提取学生数据"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 查找所有表格,找到行数最多的那个(应该是学生数据表)
    tables = soup.find_all('table')
    data_table = None
    max_rows = 0
    
    for table in tables:
        rows = table.find_all('tr')
        if len(rows) > max_rows:
            max_rows = len(rows)
            data_table = table
    
    if not data_table or max_rows <= 1:
        print("未找到数据表格")
        return [], []
    
    rows = data_table.find_all('tr')
    print(f"找到数据表格: {len(rows)} 行")
    
    # 提取表头
    header_row = rows[0]
    headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
    print(f"表头列数: {len(headers)}")
    
    # 提取数据行
    students = []
    for row in rows[1:]:
        cells = row.find_all(['td', 'th'])
        if len(cells) == len(headers):
            student_data = {}
            for i, cell in enumerate(cells):
                # 处理单元格内容
                text = cell.get_text(strip=True)
                # 检查是否有图片(照片列)
                img = cell.find('img')
                if img and img.get('src'):
                    text = f"[照片: {img.get('src')}]"
                student_data[headers[i]] = text
            students.append(student_data)
    
    return headers, students

# 主程序
print("=" * 60)
print("开始提取学生数据 (固定版本)")
print("=" * 60)

# 从保存的HTML文件读取第一页数据
print("\n正在从保存的HTML文件读取第一页数据...")
with open('temp/debug_data_page.html', 'r', encoding='utf-8') as f:
    first_page_html = f.read()

headers, first_page_students = extract_students_from_html(first_page_html)

# 提取第一页的学号列表用于去重检查
first_page_ids = set([s['学号'] for s in first_page_students if '学号' in s])

print(f"第1页: 提取了 {len(first_page_students)} 名学生")
print(f"第1页学号范围: {first_page_students[0]['学号']} 到 {first_page_students[-1]['学号']}")

# 尝试通过POST请求获取下一页
# 从HTML中查找分页相关的表单信息
print("\n尝试获取第2页...")

# 方法1: 尝试直接传递页码参数
page2_url = f'{base_url}/xszhxxAction.do?method=goQuerXsjbxx'
# 尝试不同的可能分页参数
params_list = [
    {'pageNo': '2'},
    {'page': '2'},
    {'pageNum': '2'},
    {'currentPage': '2'},
    {'pn': '2'}
]

second_page_students = []
for params in params_list:
    print(f"  尝试参数: {params}")
    try:
        response = session.post(page2_url, data=params, timeout=10)
        if response.status_code == 200 and len(response.text) > 10000:
            headers2, students2 = extract_students_from_html(response.text)
            if students2:
                # 检查是否与第一页重复
                second_ids = set([s['学号'] for s in students2 if '学号' in s])
                overlap = first_page_ids & second_ids
                if len(overlap) < len(students2) * 0.5:  # 如果重复少于50%,认为是新数据
                    print(f"  ✓ 成功获取第2页,提取了 {len(students2)} 名学生")
                    print(f"  第2页学号范围: {students2[0]['学号']} 到 {students2[-1]['学号']}")
                    second_page_students = students2
                    break
                else:
                    print(f"  ✗ 数据与第1页重复 ({len(overlap)}/{len(students2)})")
            else:
                print(f"  ✗ 未提取到学生数据")
    except Exception as e:
        print(f"  ✗ 请求失败: {e}")

# 合并数据
all_students = first_page_students
if second_page_students:
    all_students.extend(second_page_students)
    print(f"\n✓ 成功合并两页数据")
else:
    print(f"\n⚠ 仅获取了第一页数据")

# 去重 (以学号为准)
unique_students = {}
for student in all_students:
    xh = student.get('学号', '')
    if xh and xh not in unique_students:
        unique_students[xh] = student

all_students = list(unique_students.values())

# 保存结果
print(f"\n总计提取: {len(all_students)} 名学生 (去重后)")
print(f"字段数: {len(headers)}")

# 确保输出目录存在
os.makedirs('output', exist_ok=True)

# 保存为CSV
csv_file = 'output/students_fixed.csv'
with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    writer.writerows(all_students)

print(f"✓ 数据已保存到: {csv_file}")

# 保存为JSON
json_file = 'output/students_fixed.json'
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump({
        'total': len(all_students),
        'fields': headers,
        'students': all_students
    }, f, ensure_ascii=False, indent=2)

print(f"✓ 数据已保存到: {json_file}")

# 显示前3名和最后3名学生的部分信息
print("\n前3名学生示例:")
key_fields = ['学号', '姓名', '性别', '专业', '班级']
for i, student in enumerate(all_students[:3], 1):
    print(f"\n学生 {i}:")
    for field in key_fields:
        if field in student:
            print(f"  {field}: {student[field]}")

print("\n最后3名学生示例:")
for i, student in enumerate(all_students[-3:], len(all_students)-2):
    print(f"\n学生 {i}:")
    for field in key_fields:
        if field in student:
            print(f"  {field}: {student[field]}")

print("\n" + "=" * 60)
print("数据提取完成!")
print("=" * 60)
