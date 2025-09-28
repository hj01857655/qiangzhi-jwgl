#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
强智教务系统 API接口
主要功能：获取个人信息、课程表、成绩、考试安排等
"""

import requests
from typing import Dict, Any, List, Optional, Union
import json
from datetime import datetime
import logging
import re
from bs4 import BeautifulSoup

try:
    from .login_manager import LoginManager
    from .session_manager import SessionManager
except ImportError:
    from login_manager import LoginManager
    from session_manager import SessionManager


class JwglAPI:
    """
    强智教务系统 API接口类
    
    使用已登录的session进行各种教务信息查询
    支持传入 requests.Session 或 SessionManager
    """
    
    def __init__(self, session: Union[requests.Session, SessionManager] = None, 
                 base_url: str = "http://58.20.60.39:8099"):
        """
        初始化API客户端
        
        Args:
            session: 已登录的requests.Session对象或SessionManager实例
            base_url: 教务系统基础URL
        """
        self.base_url = base_url.rstrip('/')
        self.logger = logging.getLogger(__name__)
        
        if isinstance(session, SessionManager):
            self.session_manager = session
            self.session = session.session
            self._use_session_manager = True
        elif isinstance(session, requests.Session):
            self.session = session
            self.session_manager = None
            self._use_session_manager = False
        else:
            # 创建默认的SessionManager
            self.session_manager = SessionManager(base_url=base_url)
            self.session = self.session_manager.session
            self._use_session_manager = True
            
        self.user_info = {}
    
    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        发起HTTP请求的通用方法
        
        Args:
            method: HTTP方法
            url: 请求URL
            **kwargs: requests参数
            
        Returns:
            Response对象
        """
        if self._use_session_manager and self.session_manager:
            # 使用SessionManager发起请求（自动处理会话）
            return self.session_manager.request(method, url, **kwargs)
        else:
            # 使用原始session发起请求
            if not url.startswith('http'):
                url = f"{self.base_url}{url}"
            
            # 设置默认请求头
            headers = kwargs.get('headers', {})
            default_headers = {
                'Referer': f"{self.base_url}/jsxsd/framework/xsMain.jsp",
                'User-Agent': self.session.headers.get('User-Agent', 'Mozilla/5.0')
            }
            default_headers.update(headers)
            kwargs['headers'] = default_headers
            
            return self.session.request(method, url, **kwargs)
    
    def get_user_info(self) -> Dict[str, Any]:
        """
        获取用户个人信息
        
        Returns:
            用户信息字典
        """
        try:
            # 访问个人信息页面
            response = self._request('GET', '/jsxsd/grxx/xsxx')
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            user_info = {}
            
            # 解析学籍卡片表格
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    # 处理院系、专业、班级、学号行
                    text = row.get_text(strip=True)
                    if '院系：' in text and '专业：' in text:
                        # 解析：院系：护理学院 | 专业：护理学 | 学制：4 | 班级：23本护理4班 | 学号：12023050204013
                        parts = text.split('|') if '|' in text else row.get_text('|').split('|')
                        for part in parts:
                            if '：' in part:
                                k, v = part.split('：', 1)
                                user_info[k.strip()] = v.strip()
                    
                    # 处理标准的键值对行
                    cells = row.find_all(['td', 'th'])
                    
                    # 姓名、性别、姓名拼音等行
                    if len(cells) >= 6:
                        # 处理: 姓名 | 付佳鹭 | 性别 | 女 | 姓名拼音 | fujialu
                        for i in range(0, len(cells)-1, 2):
                            key = cells[i].get_text(strip=True).replace('：', '').replace(':', '')
                            if i+1 < len(cells):
                                value = cells[i+1].get_text(strip=True)
                                if key and value and key in ['姓名', '性别', '姓名拼音', '出生日期', '婚否', '本人电话',
                                                             '专业方向', '政治面貌', '籍贯', '入党团时间', '民族',
                                                             '学习形式', '学习层次', '外语种类', '家庭现住址',
                                                             '下车火车站', '邮政编码', '家庭电话', '联系人',
                                                             '入学日期', '毕业日期', '入学考号', '身份证编号']:
                                    user_info[key] = value
                    # 处理简单的键值对
                    elif len(cells) == 4:
                        # 处理: 入学日期 | 202309 | 毕业日期 | 
                        for i in range(0, len(cells)-1, 2):
                            key = cells[i].get_text(strip=True).replace('：', '').replace(':', '')
                            if i+1 < len(cells):
                                value = cells[i+1].get_text(strip=True)
                                if key and value and any('一' <= c <= '鿿' for c in key):
                                    user_info[key] = value
            
            # 缓存用户信息
            self.user_info = user_info
            
            self.logger.info(f"获取用户信息成功: {len(user_info)}个字段")
            return user_info
            
        except Exception as e:
            self.logger.error(f"获取用户信息失败: {str(e)}")
            return {}
    
    def get_schedule(self, year: str = None, semester: str = None) -> List[Dict[str, Any]]:
        """
        获取课程表（按周拆分成独立的课程单元）
        
        Args:
            year: 学年，如"2023-2024"
            semester: 学期，如"1"或"2"
            
        Returns:
            按周拆分的课程单元列表，每个单元代表某一周的一次完整课程
            保持完整的节次格式（如 09-10-11节）
        """
        try:
            url = '/jsxsd/xskb/xskb_list.do'
            
            # 首先通过GET请求获取课程表页面和隐藏字段
            response = self._request('GET', url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 构建参数
            data = {
                'cj0701id': '',
                'zc': '',  # 周次
                'demo': '',
                'sfFD': '1'  # 放大显示
            }
            
            # 设置学期参数
            if year and semester:
                data['xnxq01id'] = f"{year}-{semester}"
            elif year:
                data['xnxq01id'] = year
            else:
                # 获取默认学期
                semester_select = soup.find('select', {'name': 'xnxq01id'})
                if semester_select:
                    selected_option = semester_select.find('option', selected=True)
                    if selected_option:
                        data['xnxq01id'] = selected_option.get('value', '')
            
            # 获取所有隐藏字段 - 这些是必需的
            hidden_inputs = soup.find_all('input', type='hidden')
            for hidden_input in hidden_inputs:
                name = hidden_input.get('name')
                value = hidden_input.get('value', '')
                if name:
                    if name in data:
                        # 如果已存在，转换为列表
                        if isinstance(data[name], list):
                            data[name].append(value)
                        else:
                            data[name] = [data[name], value]
                    else:
                        data[name] = value
            
            # 设置请求头
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': f"{self.base_url}/jsxsd/xskb/xskb_list.do"
            }
            
            # 发送POST请求
            response = self._request('POST', url, data=data, headers=headers)
            response.raise_for_status()
            
            print(f"🔍 HTTP响应状态: {response.status_code}")
            print(f"🔍 响应内容长度: {len(response.text)}")
            
            # 解析课程表HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找课程表格 - 基于MCP分析的实际结构
            schedule_table = soup.find('table', {'id': 'kbtable'})
            
            if not schedule_table:
                self.logger.warning("未找到课程表数据表格")
                return []
            
            courses = []
            rows = schedule_table.find_all('tr')
            
            # 预定义的时间段映射 - 根据MCP分析的正确结果
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
                    
                    # 解析单元格中的课程 - 处理由---------------------分隔的多个课程
                    cell_courses = self._parse_course_from_cell(cell_text)
                    
                    for course in cell_courses:
                        course.update({
                            'time_slot': time_slot,  # 使用正确的时间段
                            'day_of_week': day_idx,
                            'day_name': weekday
                        })
                        courses.append(course)
            
            self.logger.info(f"获取课程表成功，共{len(courses)}门课程")
            
            # 按周拆分成课程单元
            semester_id = data.get('xnxq01id', '')
            schedule_units = self._split_courses_by_weeks(courses, semester_id)
            self.logger.info(f"按周拆分后，共{len(schedule_units)}个课程单元")
            return schedule_units
            
        except Exception as e:
            self.logger.error(f"获取课程表失败: {str(e)}")
            return []
    
    def _parse_course_from_cell(self, cell_content: str) -> List[Dict[str, Any]]:
        """
        解析课程表单元格内容，处理由---------------------分隔的多个课程
        基于MCP分析的真实结构进行解析
        
        Args:
            cell_content: 单元格的文本内容
            
        Returns:
            解析后的课程列表
        """
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
                'time_periods': '',
                'classroom': '',
                'raw_info': block
            }
            
            # 第1行通常是课程名称
            course_info['course_name'] = lines[0]
            
            # 第2行通常是教师姓名
            if len(lines) > 1:
                course_info['teacher'] = lines[1]
            
            # 第3行通常包含周次和节次信息，如："1-3,6,11-12(周)[01-02节]"
            if len(lines) > 2:
                time_info = lines[2]
                
                # 提取周次信息
                weeks_match = re.search(r'([0-9,-]+)\(周\)', time_info)
                if weeks_match:
                    course_info['weeks'] = weeks_match.group(1)
                
                # 提取节次信息
                periods_match = re.search(r'\[([0-9-]+)节\]', time_info)
                if periods_match:
                    course_info['time_periods'] = periods_match.group(1)
            
            # 第4行通常是教室
            if len(lines) > 3:
                course_info['classroom'] = lines[3]
            
            # 只有有课程名的才添加
            if course_info['course_name']:
                courses.append(course_info)
        
        return courses
    
    def get_grades(self, year: str = None, semester: str = None, course_name: str = None, course_nature: str = None, show_all: bool = True, use_post: bool = True) -> Dict[str, Any]:
        """
        获取成绩信息
        
        Args:
            year: 学年，如"2023-2024"
            semester: 学期，如"1"或"2" 
            course_name: 课程名称（模糊搜索）
            course_nature: 课程性质，可选值：
                        - "01" 或 "公共课"
                        - "02" 或 "公共基础课"
                        - "03" 或 "专业基础课"
                        - "04" 或 "专业课"
                        - "05" 或 "专业选修课"
                        - "06" 或 "公共选修课"
                        - "07" 或 "其它"
            show_all: 是否显示全部成绩（默认True=显示全部成绩，False=只显示最好成绩）
            use_post: 是否使用POST请求（默认True，False则使用GET）
                     注意：GET请求只支持kksj参数，其他参数会被忽略！
                     如需使用多个筛选条件，请使用POST请求
            
        Returns:
            成绩信息
        """
        try:
            url = '/jsxsd/kscj/cjcx_list'
            
            # 构建参数 - 根据实际网络请求分析结果优化
            params = {
                'kksj': '',  # 开课时间
                'kcxz': '',  # 课程性质
                'kcmc': '',  # 课程名称
                'xsfs': 'all' if show_all else 'max'  # 显示方式（max=显示最好成绩，all=显示全部成绩）
            }
            
            # 如果指定了学年和学期，构建kksj参数
            if year and semester:
                params['kksj'] = f"{year}-{semester}"
            elif year:
                params['kksj'] = year
                
            # 如果指定了课程名称
            if course_name:
                params['kcmc'] = course_name
                
            # 如果指定了课程性质
            if course_nature:
                # 课程性质中文到代码的映射（实际使用01、02等代码）
                nature_map = {
                    '公共课': '01',
                    '公共基础课': '02', 
                    '专业基础课': '03',
                    '专业课': '04',
                    '专业选修课': '05',
                    '公共选修课': '06',
                    '其它': '07'
                }
                # 如果传入的是中文，转换为代码
                if course_nature in nature_map:
                    params['kcxz'] = nature_map[course_nature]
                else:
                    # 否则直接使用传入的值（可能是代码）
                    params['kcxz'] = course_nature
            
            # 根据请求方式发送请求
            if use_post:
                # POST请求：参数在body中
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': f'{self.base_url}/jsxsd/kscj/cjcx_query'
                }
                response = self._request('POST', url, data=params, headers=headers)
            else:
                # GET请求：参数在URL中
                response = self._request('GET', url, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找成绩表格 - 根据HTML结构分析结果优化
            grade_table = soup.find('table', {'id': 'dataList'}) or \
                         soup.find('table', class_='Nsb_r_list Nsb_table') or \
                         soup.find('table', class_='Nsb_r_list')
            
            if not grade_table:
                self.logger.warning("未找到成绩数据表格")
                return {'grades': [], 'error': '未找到成绩数据'}
            
            grades = []
            
            # 解析成绩数据行
            rows = grade_table.find_all('tr')[1:]  # 跳过表头
            
            for row in rows:
                cells = row.find_all('td')
                
                # 检查是否是"未查询到数据"的情况
                if len(cells) == 1 and '未查询到数据' in cells[0].get_text():
                    self.logger.info(f"学期 {params.get('kksj', '全部')} 暂无成绩数据")
                    return {
                        'grades': [],
                        'total_count': 0,
                        'year': year,
                        'semester': semester,
                        'message': '未查询到数据'
                    }
                
                # 解析成绩数据 - 根据HTML结构分析结果优化的16列结构
                if len(cells) >= 16:
                    # 使用辅助函数提取清洁的文本内容
                    def extract_clean_text(cell):
                        """Extract clean text from cell, handling links and special formatting"""
                        # 如果包含链接，优先获取链接的文本内容
                        link = cell.find('a')
                        if link:
                            return link.get_text(strip=True)
                        return cell.get_text(strip=True)
                    
                    grade = {
                        '序号': extract_clean_text(cells[0]),
                        '开课学期': extract_clean_text(cells[1]),
                        '课程编号': extract_clean_text(cells[2]),
                        '课程名称': extract_clean_text(cells[3]),
                        '总成绩': extract_clean_text(cells[4]),  # 可能包含链接
                        '技能成绩': extract_clean_text(cells[5]),
                        '平时成绩': extract_clean_text(cells[6]),
                        '卷面成绩': extract_clean_text(cells[7]),
                        '成绩标志': extract_clean_text(cells[8]),
                        '学分': extract_clean_text(cells[9]),
                        '考试性质': extract_clean_text(cells[10]),
                        '总学时': extract_clean_text(cells[11]),
                        '绩点': extract_clean_text(cells[12]),
                        '考核方式': extract_clean_text(cells[13]),
                        '课程属性': extract_clean_text(cells[14]),
                        '课程性质': extract_clean_text(cells[15])
                    }
                    
                    # 不添加额外字段，保持原始表格列结构
                    grades.append(grade)
            
            self.logger.info(f"获取成绩成功，共{len(grades)}门课程")
            
            # 直接返回成绩列表，不包装额外信息
            return grades
            
        except Exception as e:
            self.logger.error(f"获取成绩失败: {str(e)}")
            return {'grades': [], 'error': str(e)}
    
    def get_exam_schedule(self) -> Dict[str, Any]:
        """
        获取考试安排
        
        Returns:
            考试安排信息
        """
        try:
            url = '/jsxsd/xsks/xsksap_list'
            
            # GET和POST都支持，默认使用POST（更稳定）
            response = self._request('POST', url, data=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找考试安排表格（使用正确的ID）
            exam_table = soup.find('table', {'id': 'dataList'})
            if not exam_table:
                # 尝试使用class查找
                exam_table = soup.find('table', {'class': 'Nsb_r_list Nsb_table'})
            
            if not exam_table:
                self.logger.warning("未找到考试安排数据")
                return {'exams': [], 'error': '未找到考试安排数据'}
            
            exams = []
            
            # 解析表头
            header_row = exam_table.find('tr')
            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
            
            # 解析考试数据
            rows = exam_table.find_all('tr')[1:]  # 跳过表头
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= len(headers):
                    exam = {}
                    for i, header in enumerate(headers):
                        if i < len(cells):
                            exam[header] = cells[i].get_text(strip=True)
                    exams.append(exam)
            
            self.logger.info(f"获取考试安排成功，共{len(exams)}场考试")
            return {
                'exams': exams,
                'total_count': len(exams)
            }
            
        except Exception as e:
            self.logger.error(f"获取考试安排失败: {str(e)}")
            return {'exams': [], 'error': str(e)}
    
    def get_available_semesters(self) -> List[Dict[str, str]]:
        """
        获取可用的学年学期列表
        
        Returns:
            学年学期列表
        """
        try:
            # 访问成绩查询页面获取学期选项
            response = self._request('GET', '/jsxsd/kscj/cjcx_list')
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            semesters = []
            
            # 查找学期下拉选择框
            semester_select = soup.find('select', {'name': 'xnxq01id'})
            
            if semester_select:
                options = semester_select.find_all('option')
                for option in options:
                    value = option.get('value', '')
                    text = option.get_text(strip=True)
                    if value and text:
                        semesters.append({
                            'value': value,
                            'text': text
                        })
            
            self.logger.info(f"获取学期列表成功，共{len(semesters)}个学期")
            return semesters
            
        except Exception as e:
            self.logger.error(f"获取学期列表失败: {str(e)}")
            return []
    
    def test_connection(self) -> bool:
        """
        测试连接是否正常
        
        Returns:
            连接是否正常
        """
        try:
            response = self._request('GET', '/jsxsd/framework/xsMain.jsp')
            return response.status_code == 200 and '学生个人中心' in response.text
            
        except Exception as e:
            self.logger.error(f"测试连接失败: {str(e)}")
            return False
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        获取当前会话信息
        
        Returns:
            会话信息
        """
        info = {
            'use_session_manager': self._use_session_manager,
            'user_info': self.user_info,
            'base_url': self.base_url
        }
        
        if self._use_session_manager and self.session_manager:
            info.update(self.session_manager.get_session_info())
        
        return info
    
    def _parse_weeks(self, week_str: str) -> List[int]:
        """
        解析周次字符串，返回所有周次的列表
        例如: "3-5,7" -> [3, 4, 5, 7]
        """
        weeks = []
        if not week_str:
            return weeks
        
        parts = week_str.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                # 处理范围，如 "3-5"
                start, end = part.split('-')
                weeks.extend(range(int(start), int(end) + 1))
            else:
                # 处理单个周次，如 "7"
                weeks.append(int(part))
        
        return sorted(weeks)
    
    def _split_courses_by_weeks(self, courses: List[Dict[str, Any]], semester: str = "") -> List[Dict[str, Any]]:
        """
        将课程按周拆分成独立的课程单元
        
        Args:
            courses: 原始课程列表
            semester: 学期标识
            
        Returns:
            按周拆分的课程单元列表，去掉多余字段
        """
        all_units = []
        
        for course in courses:
            weeks = self._parse_weeks(course.get('weeks', ''))
            
            # 为每个周次创建一个课程单元
            for week in weeks:
                unit = {
                    'semester': semester,
                    'week': week,
                    'weekday': course.get('day_name', ''),
                    'weekday_num': course.get('day_of_week', 0),
                    'time_slot_name': course.get('time_slot', ''),
                    'periods': course.get('time_periods', ''),  # 保持完整格式如 "09-10-11"
                    'course_name': course.get('course_name', ''),
                    'teacher': course.get('teacher', ''),
                    'classroom': course.get('classroom', '')
                    # 不包含 original_weeks, original_periods, raw_info 等字段
                }
                all_units.append(unit)
        
        return all_units
