#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取信息工程学院2024级所有学生信息
"""

import requests
import json
from bs4 import BeautifulSoup
import time

# 加载session信息
with open('temp/admin_session.json', 'r', encoding='utf-8') as f:
    session_data = json.load(f)

base_url = session_data['base_url']
jsessionid = session_data['cookies']['JSESSIONID']

# 创建session
session = requests.Session()
session.cookies.set('JSESSIONID', jsessionid)

# 查询参数
query_data = {
    'xjzt': '01',      # 在校
    'yx': '21',        # 信息工程学院
    'rxnf': '2024',    # 2024级
    'zy': '',
    'bj': '',
    'dqzt': '',
    'zxzt': '',
    'zzmm': '',
    'gjdqm': '',
    'xb': '',
    'xh': '',
    'xm': '',
    'sfzhm': '',
    'pycc': '',
    'xz': '',
    'stutype': ''
}

print("正在查询信息工程学院2024级学生数据...")

# 发送查询请求
response = session.post(
    f'{base_url}/xszhxxAction.do?method=goSosoXsxx',
    data=query_data,
    headers={
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': f'{base_url}/xszhxxAction.do?method=allXjzt',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
)

if response.status_code != 200:
    print(f"请求失败: {response.status_code}")
    exit(1)

# 解析HTML
soup = BeautifulSoup(response.text, 'html.parser')

# 查找所有iframe
iframes = soup.find_all('iframe')
print(f"找到 {len(iframes)} 个iframe")

# 尝试从响应中找到frameset或直接找表格
# 这个系统可能返回frameset结构，我们需要再次请求实际的数据页面

# 查找学生数据表格的URL
# 通常在frameset中会有指向实际数据页面的URL
frame_src = None
for iframe in iframes:
    src = iframe.get('src', '')
    if 'goQuerXsjbxx' in src or 'xszhxx' in src.lower():
        frame_src = src
        break

if frame_src:
    print(f"发现数据iframe: {frame_src}")
    # 构建完整URL
    if not frame_src.startswith('http'):
        frame_src = base_url + '/' + frame_src.lstrip('/')
    
    # 请求实际的数据页面
    data_response = session.get(frame_src)
    soup = BeautifulSoup(data_response.text, 'html.parser')

# 查找表格
table = soup.find('table')
if not table:
    # 尝试查找所有table
    tables = soup.find_all('table')
    print(f"找到 {len(tables)} 个table")
    if tables:
        # 选择最大的表格
        table = max(tables, key=lambda t: len(t.find_all('tr')))

if not table:
    print("未找到数据表格")
    # 保存HTML用于调试
    with open('temp/debug_response.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print("响应已保存到 temp/debug_response.html")
    exit(1)

# 提取表头
headers = []
header_row = table.find('tr')
if header_row:
    for th in header_row.find_all(['th', 'td']):
        header_text = th.get_text(strip=True)
        if header_text and header_text not in ['', ' ']:
            headers.append(header_text)

print(f"表头字段: {headers[:10]}...")

# 提取学生数据
students = []
rows = table.find_all('tr')[1:]  # 跳过表头

for row in rows:
    cells = row.find_all(['td', 'th'])
    if len(cells) < 5:  # 数据行至少有5列
        continue
    
    # 检查是否是有效的学生数据行
    cell_texts = [cell.get_text(strip=True) for cell in cells]
    
    # 跳过空行或特殊行
    if not cell_texts[0] or cell_texts[0] in ['序号', '', ' ']:
        if len(cell_texts) > 1 and not cell_texts[1]:
            continue
    
    # 尝试判断是否是学生数据（学号通常是数字）
    if len(cell_texts) > 1 and cell_texts[1].isdigit() and len(cell_texts[1]) > 10:
        student = {}
        for i, header in enumerate(headers):
            if i < len(cell_texts):
                student[header] = cell_texts[i]
        students.append(student)

print(f"\n成功提取 {len(students)} 名学生信息")

# 显示前5个学生信息
print("\n前5名学生信息：")
for i, student in enumerate(students[:5], 1):
    print(f"\n学生 {i}:")
    # 只显示关键字段
    key_fields = ['学号', '姓名', '性别', '专业名称', '班级', '入学年份']
    for field in key_fields:
        if field in student:
            print(f"  {field}: {student[field]}")

# 保存到JSON文件
output_file = 'output/students_2024_info_engineering.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(students, f, ensure_ascii=False, indent=2)

print(f"\n所有学生信息已保存到: {output_file}")

# 生成统计报告
print("\n统计信息:")
if students:
    # 按班级统计
    class_count = {}
    for student in students:
        class_name = student.get('班级', '未知')
        class_count[class_name] = class_count.get(class_name, 0) + 1
    
    print("\n各班级人数:")
    for class_name, count in sorted(class_count.items()):
        print(f"  {class_name}: {count}人")
    
    # 按性别统计
    gender_count = {}
    for student in students:
        gender = student.get('性别', '未知')
        gender_count[gender] = gender_count.get(gender, 0) + 1
    
    print("\n性别分布:")
    for gender, count in gender_count.items():
        print(f"  {gender}: {count}人")

print("\n完成！")
