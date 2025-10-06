#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
探索管理员系统的学籍管理相关 API
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.admin_login_manager import AdminLoginManager
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urljoin


def explore_main_page(manager: AdminLoginManager):
    """探索管理员首页"""
    try:
        print("=" * 80)
        print("1. 探索管理员首页")
        print("=" * 80)
        
        # 访问主页
        main_url = urljoin(manager.base_url, '/jsxsd/framework/xsMain.jsp')
        response = manager.session.get(main_url, timeout=15)
        
        print(f"状态码: {response.status_code}")
        print(f"内容长度: {len(response.text)} 字符")
        
        # 保存首页
        with open('temp/admin_main_page.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("✓ 首页已保存到: temp/admin_main_page.html")
        
        # 解析页面
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找所有链接
        print("\n" + "-" * 80)
        print("找到的链接:")
        print("-" * 80)
        
        links = soup.find_all('a', href=True)
        student_related = []
        
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # 筛选学籍相关的链接
            if any(keyword in text for keyword in ['学籍', '学生', '信息', '管理', '查询']):
                student_related.append({
                    'text': text,
                    'href': href,
                    'full_url': urljoin(manager.base_url, href)
                })
                print(f"\n✓ {text}")
                print(f"  URL: {href}")
        
        # 保存结果
        with open('temp/admin_links.json', 'w', encoding='utf-8') as f:
            json.dump(student_related, f, indent=2, ensure_ascii=False)
        print(f"\n✓ 找到 {len(student_related)} 个相关链接，已保存到: temp/admin_links.json")
        
        return student_related
        
    except Exception as e:
        print(f"✗ 探索首页失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def explore_menu_structure(manager: AdminLoginManager):
    """探索菜单结构"""
    try:
        print("\n" + "=" * 80)
        print("2. 探索菜单结构")
        print("=" * 80)
        
        # 尝试访问可能的菜单页面
        menu_urls = [
            '/jsxsd/framework/main.jsp',
            '/jsxsd/framework/left.jsp',
            '/jsxsd/framework/mainV.jsp',
            '/jsxsd/xsxxxggl.do',  # 学生信息管理
            '/jsxsd/xjgl/',  # 学籍管理
        ]
        
        found_pages = []
        
        for path in menu_urls:
            try:
                url = urljoin(manager.base_url, path)
                print(f"\n尝试访问: {url}")
                response = manager.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    print(f"  ✓ 成功 (长度: {len(response.text)} 字符)")
                    
                    # 保存页面
                    filename = f"temp/admin_{path.replace('/', '_')}.html"
                    os.makedirs('temp', exist_ok=True)
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    print(f"  ✓ 已保存到: {filename}")
                    
                    found_pages.append({
                        'url': url,
                        'path': path,
                        'file': filename
                    })
                    
                    # 解析页面中的链接
                    soup = BeautifulSoup(response.text, 'html.parser')
                    links = soup.find_all('a', href=True)
                    
                    print(f"  找到 {len(links)} 个链接")
                    for link in links[:10]:  # 只显示前10个
                        text = link.get_text(strip=True)
                        href = link.get('href', '')
                        if text and '学' in text:
                            print(f"    - {text}: {href}")
                    
                else:
                    print(f"  ✗ 失败 (状态码: {response.status_code})")
                    
            except Exception as e:
                print(f"  ✗ 错误: {e}")
        
        return found_pages
        
    except Exception as e:
        print(f"✗ 探索菜单失败: {e}")
        return []


def analyze_student_management_apis(manager: AdminLoginManager):
    """分析学籍管理相关的API"""
    try:
        print("\n" + "=" * 80)
        print("3. 分析学籍管理 API")
        print("=" * 80)
        
        # 可能的学籍管理 API 路径
        api_paths = [
            '/jsxsd/xjgl/xjgl_list',  # 学籍管理列表
            '/jsxsd/xjgl/xjgl_query',  # 学籍查询
            '/jsxsd/xsxxxggl.do?method=queryxsxx',  # 学生信息查询
            '/jsxsd/xsxxxggl.do?method=list',  # 学生列表
            '/jsxsd/framework/xsMain.jsp',  # 主页
            '/jsxsd/framework/mainV.jsp',  # 主框架
        ]
        
        results = []
        
        for path in api_paths:
            try:
                url = urljoin(manager.base_url, path)
                print(f"\n尝试访问: {path}")
                
                response = manager.session.get(url, timeout=10, allow_redirects=True)
                
                info = {
                    'path': path,
                    'url': url,
                    'status_code': response.status_code,
                    'content_length': len(response.text),
                    'content_type': response.headers.get('Content-Type', 'unknown'),
                    'success': response.status_code == 200
                }
                
                if response.status_code == 200:
                    print(f"  ✓ 成功")
                    print(f"  - 状态码: {response.status_code}")
                    print(f"  - 内容类型: {info['content_type']}")
                    print(f"  - 内容长度: {info['content_length']} 字符")
                    
                    # 保存响应
                    filename = f"temp/api_{path.replace('/', '_').replace('?', '_')}.html"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    print(f"  - 已保存到: {filename}")
                    info['saved_file'] = filename
                    
                    # 分析内容
                    content_lower = response.text.lower()
                    if 'form' in content_lower:
                        print(f"  - 包含表单")
                    if 'table' in content_lower:
                        print(f"  - 包含表格")
                    if 'script' in content_lower:
                        print(f"  - 包含脚本")
                    
                else:
                    print(f"  ✗ 失败 (状态码: {response.status_code})")
                
                results.append(info)
                
            except Exception as e:
                print(f"  ✗ 错误: {e}")
                results.append({
                    'path': path,
                    'url': url,
                    'error': str(e),
                    'success': False
                })
        
        # 保存结果
        with open('temp/api_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n✓ API 分析结果已保存到: temp/api_analysis.json")
        
        return results
        
    except Exception as e:
        print(f"✗ 分析 API 失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def find_dwr_calls(manager: AdminLoginManager):
    """查找 DWR 调用（常用于数据交互）"""
    try:
        print("\n" + "=" * 80)
        print("4. 查找 DWR 调用")
        print("=" * 80)
        
        # 访问主页获取可能的 DWR 配置
        main_url = urljoin(manager.base_url, '/jsxsd/framework/xsMain.jsp')
        response = manager.session.get(main_url, timeout=10)
        
        # 查找 DWR 相关脚本
        soup = BeautifulSoup(response.text, 'html.parser')
        scripts = soup.find_all('script', src=True)
        
        dwr_scripts = []
        for script in scripts:
            src = script.get('src', '')
            if 'dwr' in src.lower():
                dwr_scripts.append(src)
                print(f"✓ 找到 DWR 脚本: {src}")
        
        # 查找内联脚本中的 DWR 调用
        inline_scripts = soup.find_all('script', src=False)
        dwr_calls = []
        
        for script in inline_scripts:
            content = script.string or script.get_text()
            if content and 'dwr' in content.lower():
                # 提取 DWR 方法调用
                patterns = [
                    r'(\w+)\.(\w+)\s*\(',  # ClassName.methodName(
                    r'DWRUtil\.(\w+)',  # DWRUtil.xxx
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        if isinstance(match, tuple):
                            call = '.'.join(match)
                        else:
                            call = match
                        if call not in dwr_calls:
                            dwr_calls.append(call)
        
        if dwr_calls:
            print(f"\n找到 {len(dwr_calls)} 个 DWR 调用:")
            for call in dwr_calls:
                print(f"  - {call}")
        
        return {
            'scripts': dwr_scripts,
            'calls': dwr_calls
        }
        
    except Exception as e:
        print(f"✗ 查找 DWR 调用失败: {e}")
        return {'scripts': [], 'calls': []}


def main():
    """主函数"""
    print("=" * 80)
    print("强智教务系统 - 管理员 API 探索工具")
    print("=" * 80)
    
    # 创建管理器并加载会话
    manager = AdminLoginManager(
        base_url="http://58.20.60.39:8099",
        session_file="temp/admin_session.json"
    )
    
    # 加载保存的会话
    if not manager.load_session():
        print("✗ 无法加载会话，请先登录")
        return
    
    if not manager.is_logged_in():
        print("✗ 会话已过期，需要重新登录")
        return
    
    print(f"✓ 已加载会话 (用户: {manager.username})")
    print()
    
    # 创建临时目录
    os.makedirs('temp', exist_ok=True)
    
    # 1. 探索首页
    links = explore_main_page(manager)
    
    # 2. 探索菜单结构
    pages = explore_menu_structure(manager)
    
    # 3. 分析学籍管理 API
    apis = analyze_student_management_apis(manager)
    
    # 4. 查找 DWR 调用
    dwr_info = find_dwr_calls(manager)
    
    # 总结
    print("\n" + "=" * 80)
    print("探索完成！")
    print("=" * 80)
    print(f"✓ 找到 {len(links)} 个相关链接")
    print(f"✓ 探索了 {len(pages)} 个页面")
    print(f"✓ 分析了 {len(apis)} 个 API")
    print(f"✓ 找到 {len(dwr_info['calls'])} 个 DWR 调用")
    print("\n所有结果已保存到 temp/ 目录")


if __name__ == '__main__':
    main()
