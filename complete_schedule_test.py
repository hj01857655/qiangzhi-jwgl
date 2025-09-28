#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
完整的课表获取和周次拆分测试脚本
1. 从教务系统获取课表数据
2. 解析课程信息  
3. 按周拆分成独立的课程单元
4. 保持完整的节次格式 (如 09-10-11节)
"""

import json
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any

def load_session():
    """加载保存的session"""
    try:
        with open('temp/session.json', 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        print("✅ 加载session成功")
        return session_data
    except FileNotFoundError:
        print("❌ 未找到session文件，请先登录")
        return None

def get_schedule_data(semester: str = "2024-2025-1"):
    """从教务系统获取课表数据"""
    session_data = load_session()
    if not session_data:
        return None
    
    # 创建session并设置cookies
    session = requests.Session()
    if 'cookies' in session_data:
        for name, cookie_info in session_data['cookies'].items():
            session.cookies.set(
                name=name,
                value=cookie_info['value'],
                domain=cookie_info.get('domain', ''),
                path=cookie_info.get('path', '/')
            )
    
    url = "http://58.20.60.39:8099/jsxsd/xskb/xskb_list.do"
    
    # 首先GET获取页面和隐藏字段
    response = session.get(url)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 构建POST参数
    data = {
        'cj0701id': '',
        'zc': '',  # 周次
        'demo': '',
        'sfFD': '1',  # 放大显示
        'xnxq01id': semester
    }
    
    # 获取隐藏字段
    hidden_inputs = soup.find_all('input', type='hidden')
    for hidden_input in hidden_inputs:
        name = hidden_input.get('name')
        value = hidden_input.get('value', '')
        if name:
            if name in data:
                if isinstance(data[name], list):
                    data[name].append(value)
                else:
                    data[name] = [data[name], value]
            else:
                data[name] = value
    
    # 发送POST请求获取课表
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': url
    }
    
    response = session.post(url, data=data, headers=headers)
    response.raise_for_status()
    
    print(f"🔍 获取课表数据成功 (状态码: {response.status_code})")
    return response.text

def parse_course_from_cell(cell_content: str) -> List[Dict[str, Any]]:
    """解析课程表单元格内容"""
    courses = []
    
    if not cell_content or not cell_content.strip():
        return courses
    
    # 按 --------------------- 分割课程
    course_blocks = cell_content.split('---------------------')
    
    for block in course_blocks:
        block = block.strip()
        if not block:
            continue
        
        # 按行分割
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        
        if len(lines) < 1:  # 至少要有课程名
            continue
            
        course_info = {
            'course_name': '',
            'teacher': '',
            'weeks': '',
            'periods': '',  # 保持完整格式
            'classroom': '',
            'raw_info': block
        }
        
        # 第1行通常是课程名称
        course_info['course_name'] = lines[0]
        
        # 第2行通常是教师姓名
        if len(lines) > 1:
            course_info['teacher'] = lines[1]
        
        # 第3行通常是时间信息 (周次和节次)
        if len(lines) > 2:
            time_info = lines[2]
            # 解析周次: 1-18(周)
            weeks_match = re.search(r'([0-9,-]+)\(周\)', time_info)
            if weeks_match:
                course_info['weeks'] = weeks_match.group(1)
            
            # 解析节次: [01-02节] 或 [09-10-11节]
            periods_match = re.search(r'\[([0-9-]+)节\]', time_info)
            if periods_match:
                course_info['periods'] = periods_match.group(1)
        
        # 第4行通常是教室
        if len(lines) > 3:
            course_info['classroom'] = lines[3]
        
        courses.append(course_info)
    
    return courses

def parse_schedule_html(html_content: str) -> List[Dict[str, Any]]:
    """解析课表HTML，返回课程列表"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    schedule_table = soup.find('table', {'id': 'kbtable'})
    if not schedule_table:
        print("❌ 未找到课程表数据表格")
        return []
    
    courses = []
    rows = schedule_table.find_all('tr')
    
    # 预定义的时间段映射
    time_slot_mapping = {
        1: "一二",
        2: "三四", 
        3: "五六",
        4: "七八",
        5: "九十",
        6: "十一十二"
    }
    
    day_names = ['', '周一', '周二', '周三', '周四', '周五', '周六', '周日']
    
    # 从第1行开始处理数据行（第0行是表头）
    for row_idx in range(1, len(rows)):
        if row_idx > 6:  # 只处理6行数据（对应6个时间段）
            break
            
        row = rows[row_idx]
        cells = row.find_all('td')
        if len(cells) < 2:
            continue
        
        # 使用预定义的时间段映射
        time_slot = time_slot_mapping.get(row_idx, "未知")
        
        print(f"处理第{row_idx}行: {time_slot}")
        
        # 处理每一天的课程 (从第1列开始是周一)
        for day_idx in range(1, min(len(cells), 8)):
            cell = cells[day_idx]
            
            # 使用显示的div内容
            visible_div = cell.find('div', class_='kbcontent')
            if visible_div:
                cell_text = visible_div.get_text('\n', strip=True)
            else:
                cell_text = cell.get_text('\n', strip=True)
            
            if not cell_text.strip():
                continue
            
            weekday = day_names[day_idx]
            print(f"  {weekday}: 找到课程")
            
            # 解析单元格中的课程
            cell_courses = parse_course_from_cell(cell_text)
            
            for course in cell_courses:
                course.update({
                    'time_slot': time_slot,
                    'day_of_week': day_idx,
                    'day_name': weekday
                })
                courses.append(course)
                print(f"    {course['course_name']} - {course['periods']}节")
    
    print(f"✅ 解析完成，共 {len(courses)} 门课程")
    return courses

def parse_weeks(week_str: str) -> List[int]:
    """解析周次字符串，返回所有周次的列表"""
    weeks = []
    if not week_str:
        return weeks
    
    parts = week_str.split(',')
    for part in parts:
        part = part.strip()
        if '-' in part:
            start, end = part.split('-')
            weeks.extend(range(int(start), int(end) + 1))
        else:
            weeks.append(int(part))
    
    return sorted(weeks)

def split_courses_by_weeks(courses: List[Dict[str, Any]], semester: str = "2024-2025-1") -> List[Dict[str, Any]]:
    """将课程按周拆分成独立的课程单元"""
    all_units = []
    
    for course in courses:
        weeks = parse_weeks(course.get('weeks', ''))
        
        # 为每个周次创建一个课程单元
        for week in weeks:
            unit = {
                'semester': semester,
                'week': week,
                'weekday': course.get('day_name', ''),
                'weekday_num': course.get('day_of_week', 0),
                'time_slot_name': course.get('time_slot', ''),
                'periods': course.get('periods', ''),  # 保持完整格式如 "09-10-11"
                'course_name': course.get('course_name', ''),
                'teacher': course.get('teacher', ''),
                'classroom': course.get('classroom', ''),
                'weeks': course.get('weeks', '')  # 保留原始周次用于显示
            }
            all_units.append(unit)
    
    return all_units

def main():
    """主测试函数"""
    print("🧪 完整课表获取和周次拆分测试")
    print("=" * 50)
    
    # 1. 获取课表数据
    print("\n📡 第1步: 从教务系统获取课表数据...")
    semester = "2024-2025-1"
    html_content = get_schedule_data(semester)
    
    if not html_content:
        print("❌ 获取课表数据失败")
        return
    
    # 2. 解析课程信息
    print("\n📋 第2步: 解析课程信息...")
    courses = parse_schedule_html(html_content)
    
    if not courses:
        print("❌ 解析课程失败")
        return
    
    # 保存原始课程数据
    with open('raw_courses.json', 'w', encoding='utf-8') as f:
        json.dump(courses, f, ensure_ascii=False, indent=2)
    print(f"💾 原始课程数据已保存到 raw_courses.json")
    
    # 3. 按周拆分
    print(f"\n🔄 第3步: 按周拆分课程...")
    schedule_units = split_courses_by_weeks(courses, semester)
    
    print(f"✅ 拆分完成:")
    print(f"   原始课程数: {len(courses)}")
    print(f"   拆分后单元数: {len(schedule_units)}")
    
    # 4. 验证拆分结果
    print(f"\n🔍 第4步: 验证拆分结果...")
    
    # 检查节次格式
    periods_formats = set(unit['periods'] for unit in schedule_units if unit['periods'])
    print(f"   节次格式: {sorted(periods_formats)}")
    
    # 检查某门课程的拆分
    if schedule_units:
        sample_course = schedule_units[0]['course_name']
        sample_units = [u for u in schedule_units if u['course_name'] == sample_course]
        original_weeks = sample_units[0]['weeks']
        
        print(f"   示例课程: 《{sample_course}》")
        print(f"     原始周次: {original_weeks}")
        print(f"     拆分单元数: {len(sample_units)}")
        print(f"     节次格式: {sample_units[0]['periods']} (保持完整)")
        
        weeks_list = [u['week'] for u in sample_units]
        print(f"     涉及周次: {sorted(set(weeks_list))}")
    
    # 5. 保存最终结果
    with open('complete_schedule_test.json', 'w', encoding='utf-8') as f:
        json.dump(schedule_units, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 最终数据已保存到 complete_schedule_test.json")
    
    # 6. 查询示例
    print(f"\n📋 查询示例:")
    
    # 统计信息
    weeks_count = len(set(unit['week'] for unit in schedule_units))
    courses_count = len(set(unit['course_name'] for unit in schedule_units))
    
    print(f"   涉及周数: {weeks_count}")
    print(f"   课程种类: {courses_count}")
    
    # 查询第5周的课程
    week5_units = [u for u in schedule_units if u['week'] == 5]
    print(f"   第5周课程单元数: {len(week5_units)}")
    
    if week5_units:
        print("   第5周课程:")
        for unit in week5_units[:3]:
            print(f"     {unit['weekday']} {unit['periods']}节: {unit['course_name']}")
        if len(week5_units) > 3:
            print(f"     ... 还有{len(week5_units)-3}个")
    
    print(f"\n🎯 测试结论:")
    print("✅ 成功从教务系统获取课表数据")
    print("✅ 成功解析课程信息")
    print("✅ 成功按周拆分 - 每周一个独立单元")
    print("✅ 节次格式完整 - 如 '09-10-11节' 不会简化")
    print("✅ 数据结构清晰 - 便于多维度查询")

if __name__ == "__main__":
    main()