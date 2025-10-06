#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整版本 - 提取所有学生数据并处理分页
"""

import requests
import json
from bs4 import BeautifulSoup
import csv
import os

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

def fetch_page(page_num=1):
    """获取指定页的数据"""
    print(f"\n正在获取第 {page_num} 页...")
    
    # 构建查询URL
    data_url = f'{base_url}/xszhxxAction.do?method=goQuerXsjbxx'
    
    # 如果不是第一页,需要发送分页参数
    if page_num > 1:
        # 发送POST请求切换页面
        params = {
            'method': 'goQuerXsjbxx',
            'pageNo': str(page_num)
        }
        response = session.post(f'{base_url}/xszhxxAction.do', data=params)
    else:
        response = session.get(data_url)
    
    if response.status_code != 200:
        print(f"请求失败: {response.status_code}")
        return [], []
    
    print(f"响应长度: {len(response.text)} 字节")
    return extract_students_from_html(response.text)

# 主程序
print("=" * 60)
print("开始提取学生数据")
print("=" * 60)

all_students = []
all_headers = None

# 获取第一页
headers, students = fetch_page(1)
if headers and students:
    all_headers = headers
    all_students.extend(students)
    print(f"第1页: 提取了 {len(students)} 名学生")
    
    # 检查分页信息
    # 从第一页的结果判断是否有更多页
    # 根据之前的观察,总共有233条记录,第一页200条
    # 所以需要获取第2页
    
    if len(students) >= 200:  # 如果第一页满了,说明可能有第二页
        print("\n第一页数据已满,尝试获取第二页...")
        headers2, students2 = fetch_page(2)
        if students2:
            all_students.extend(students2)
            print(f"第2页: 提取了 {len(students2)} 名学生")
        else:
            print("第2页无数据或获取失败")

# 保存结果
if all_students:
    print(f"\n总计提取: {len(all_students)} 名学生")
    print(f"字段数: {len(all_headers)}")
    
    # 确保输出目录存在
    os.makedirs('output', exist_ok=True)
    
    # 保存为CSV
    csv_file = 'output/students_all.csv'
    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=all_headers)
        writer.writeheader()
        writer.writerows(all_students)
    
    print(f"✓ 数据已保存到: {csv_file}")
    
    # 保存为JSON
    json_file = 'output/students_all.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total': len(all_students),
            'fields': all_headers,
            'students': all_students
        }, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 数据已保存到: {json_file}")
    
    # 显示前3名学生的部分信息
    print("\n前3名学生示例:")
    key_fields = ['学号', '姓名', '性别', '专业', '班级']
    for i, student in enumerate(all_students[:3], 1):
        print(f"\n学生 {i}:")
        for field in key_fields:
            if field in student:
                print(f"  {field}: {student[field]}")
else:
    print("\n未提取到任何学生数据")

print("\n" + "=" * 60)
print("数据提取完成!")
print("=" * 60)
