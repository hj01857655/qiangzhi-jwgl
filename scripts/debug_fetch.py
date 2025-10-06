#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试版本 - 保存HTML响应用于分析
"""

import requests
import json
from bs4 import BeautifulSoup

# 加载session信息
with open('temp/admin_session.json', 'r', encoding='utf-8') as f:
    session_data = json.load(f)

base_url = session_data['base_url']
jsessionid = session_data['cookies']['JSESSIONID']

# 创建session
session = requests.Session()
session.cookies.set('JSESSIONID', jsessionid)

print("步骤1: 请求数据页面...")
# 直接请求数据列表页面
data_url = f'{base_url}/xszhxxAction.do?method=goQuerXsjbxx'
response = session.get(data_url)

print(f"响应状态: {response.status_code}")
print(f"响应长度: {len(response.text)} 字节")

# 保存原始HTML
with open('temp/debug_data_page.html', 'w', encoding='utf-8') as f:
    f.write(response.text)

print("HTML已保存到: temp/debug_data_page.html")

# 解析并查找表格
soup = BeautifulSoup(response.text, 'html.parser')

# 查找所有表格
tables = soup.find_all('table')
print(f"\n找到 {len(tables)} 个table")

if tables:
    # 分析每个表格
    for i, table in enumerate(tables):
        rows = table.find_all('tr')
        print(f"\nTable {i+1}: {len(rows)} 行")
        
        if len(rows) > 0:
            # 显示前3行的内容
            for j, row in enumerate(rows[:3]):
                cells = row.find_all(['td', 'th'])
                print(f"  行 {j+1}: {len(cells)} 列")
                if cells and len(cells) <= 10:
                    texts = [c.get_text(strip=True)[:20] for c in cells]
                    print(f"    内容: {texts}")

# 查找包含"学号"的文本
if "学号" in response.text:
    print("\n✓ 响应中包含'学号'文本")
else:
    print("\n✗ 响应中未找到'学号'文本")

if "12024050701001" in response.text or "包乙婷" in response.text:
    print("✓ 响应中包含学生数据")
else:
    print("✗ 响应中未找到学生数据")

print("\n请检查 temp/debug_data_page.html 文件了解页面结构")
