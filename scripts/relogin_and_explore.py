#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新登录并探索管理员系统的学籍管理 API
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.admin_login_manager import AdminLoginManager
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin, urlparse, parse_qs
import re


def test_session_and_relogin(manager: AdminLoginManager):
    """测试会话状态，如果失效则重新登录"""
    try:
        print("=" * 80)
        print("1. 检查会话状态")
        print("=" * 80)
        
        # 尝试访问一个需要登录的页面
        test_url = urljoin(manager.base_url, '/jsxsd/framework/xsMain.jsp')
        response = manager.session.get(test_url, timeout=10, allow_redirects=False)
        
        print(f"测试 URL: {test_url}")
        print(f"状态码: {response.status_code}")
        
        # 检查是否被重定向到登录页
        if response.status_code in [301, 302, 303, 307, 308]:
            location = response.headers.get('Location', '')
            print(f"重定向到: {location}")
            print("\n✗ 会话已失效，需要重新登录")
            return False
        
        # 检查响应内容
        if '用户登录' in response.text or 'userAccount' in response.text:
            print("\n✗ 返回了登录页面，会话已失效")
            return False
        
        print("\n✓ 会话仍然有效")
        return True
        
    except Exception as e:
        print(f"✗ 检查会话失败: {e}")
        return False


def relogin(manager: AdminLoginManager):
    """重新登录"""
    try:
        print("\n" + "=" * 80)
        print("2. 重新登录")
        print("=" * 80)
        
        # 从会话文件读取凭据
        if not manager.username or not manager.password:
            print("✗ 未找到保存的凭据")
            
            # 手动输入
            username = input("请输入管理员用户名: ").strip()
            password = input("请输入密码: ").strip()
            manager.set_credentials(username, password)
        
        print(f"使用用户名: {manager.username}")
        print("开始登录（启用自动验证码识别）...")
        
        # 执行登录
        result = manager.login(
            manager.username, 
            manager.password, 
            auto_captcha=True
        )
        
        if result['success']:
            print("\n✓ 登录成功！")
            return True
        else:
            print(f"\n✗ 登录失败: {result['message']}")
            return False
            
    except Exception as e:
        print(f"✗ 登录异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def explore_main_page(manager: AdminLoginManager):
    """探索主页框架"""
    try:
        print("\n" + "=" * 80)
        print("3. 探索主页框架")
        print("=" * 80)
        
        # 可能的主页面
        main_pages = [
            '/jsxsd/',
            '/jsxsd/framework/xsMain.jsp',
            '/jsxsd/framework/xsMain_new.jsp',
            '/jsxsd/framework/main.jsp',
            '/jsxsd/framework/mainV.jsp',
        ]
        
        for page in main_pages:
            try:
                url = urljoin(manager.base_url, page)
                print(f"\n尝试: {page}")
                
                response = manager.session.get(url, timeout=10, allow_redirects=True)
                
                if response.status_code == 200:
                    # 检查是否是登录页
                    if '用户登录' in response.text or 'userAccount' in response.text:
                        print("  ✗ 返回登录页")
                        continue
                    
                    print(f"  ✓ 成功 (长度: {len(response.text)} 字符)")
                    
                    # 保存页面
                    filename = f"temp/main_{page.replace('/', '_')}.html"
                    os.makedirs('temp', exist_ok=True)
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    print(f"  ✓ 已保存: {filename}")
                    
                    # 分析页面结构
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 查找框架
                    frames = soup.find_all(['frame', 'iframe'])
                    if frames:
                        print(f"  找到 {len(frames)} 个框架:")
                        for frame in frames:
                            src = frame.get('src', '')
                            name = frame.get('name', 'unnamed')
                            print(f"    - {name}: {src}")
                    
                    # 查找链接
                    links = soup.find_all('a', href=True)
                    print(f"  找到 {len(links)} 个链接")
                    
                    return url, response.text
                else:
                    print(f"  ✗ 状态码: {response.status_code}")
                    
            except Exception as e:
                print(f"  ✗ 错误: {e}")
        
        return None, None
        
    except Exception as e:
        print(f"✗ 探索主页失败: {e}")
        return None, None


def explore_left_menu(manager: AdminLoginManager):
    """探索左侧菜单"""
    try:
        print("\n" + "=" * 80)
        print("4. 探索左侧菜单")
        print("=" * 80)
        
        # 左侧菜单通常在这些页面
        menu_pages = [
            '/jsxsd/framework/blankPage.jsp',
            '/jsxsd/framework/left.jsp',
            '/jsxsd/framework/leftMenu.jsp',
        ]
        
        for page in menu_pages:
            try:
                url = urljoin(manager.base_url, page)
                print(f"\n尝试: {page}")
                
                response = manager.session.get(url, timeout=10)
                
                if response.status_code == 200 and len(response.text) > 1000:
                    print(f"  ✓ 成功 (长度: {len(response.text)} 字符)")
                    
                    # 保存页面
                    filename = f"temp/menu_{page.replace('/', '_')}.html"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    print(f"  ✓ 已保存: {filename}")
                    
                    # 解析菜单
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 查找所有链接
                    links = soup.find_all('a', href=True)
                    
                    student_menu = []
                    for link in links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        
                        # 筛选学籍相关
                        if any(keyword in text for keyword in ['学籍', '学生', '信息', '管理', '查询', '名单']):
                            student_menu.append({
                                'text': text,
                                'href': href,
                                'full_url': urljoin(manager.base_url, href)
                            })
                    
                    if student_menu:
                        print(f"\n  找到 {len(student_menu)} 个学籍相关菜单:")
                        for item in student_menu:
                            print(f"    ✓ {item['text']}")
                            print(f"      {item['href']}")
                        
                        # 保存结果
                        with open('temp/student_menu.json', 'w', encoding='utf-8') as f:
                            json.dump(student_menu, f, indent=2, ensure_ascii=False)
                        print(f"\n  ✓ 已保存到: temp/student_menu.json")
                        
                        return student_menu
                    
            except Exception as e:
                print(f"  ✗ 错误: {e}")
        
        return []
        
    except Exception as e:
        print(f"✗ 探索菜单失败: {e}")
        return []


def test_student_apis(manager: AdminLoginManager, menu_items):
    """测试学籍管理相关的 API"""
    try:
        print("\n" + "=" * 80)
        print("5. 测试学籍管理 API")
        print("=" * 80)
        
        # 如果没有菜单项，使用默认列表
        if not menu_items:
            print("使用默认 API 列表...")
            menu_items = [
                {'text': '学生信息管理', 'href': '/jsxsd/xsxxxggl.do'},
                {'text': '学籍管理', 'href': '/jsxsd/xjgl/xjgl_list'},
                {'text': '学生查询', 'href': '/jsxsd/xsxxxggl.do?method=list'},
            ]
        
        results = []
        
        for item in menu_items[:5]:  # 只测试前5个
            try:
                href = item['href']
                text = item['text']
                
                url = urljoin(manager.base_url, href)
                print(f"\n测试: {text}")
                print(f"URL: {url}")
                
                response = manager.session.get(url, timeout=10)
                
                info = {
                    'name': text,
                    'url': url,
                    'status': response.status_code,
                    'length': len(response.text),
                    'content_type': response.headers.get('Content-Type', '')
                }
                
                if response.status_code == 200:
                    print(f"  ✓ 成功")
                    print(f"  - 长度: {info['length']} 字符")
                    print(f"  - 类型: {info['content_type']}")
                    
                    # 保存响应
                    filename = f"temp/api_{href.replace('/', '_').replace('?', '_')[:50]}.html"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    print(f"  - 已保存: {filename}")
                    info['file'] = filename
                    
                    # 分析内容
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 查找表单
                    forms = soup.find_all('form')
                    if forms:
                        print(f"  - 包含 {len(forms)} 个表单")
                        for form in forms:
                            action = form.get('action', '')
                            if action:
                                print(f"    表单action: {action}")
                    
                    # 查找表格
                    tables = soup.find_all('table')
                    if tables:
                        print(f"  - 包含 {len(tables)} 个表格")
                    
                    # 查找 API 调用（Ajax、DWR等）
                    scripts = soup.find_all('script')
                    api_calls = []
                    for script in scripts:
                        content = script.string or script.get_text()
                        if content:
                            # 查找 Ajax 调用
                            ajax_patterns = [
                                r'url\s*:\s*["\']([^"\']+)["\']',
                                r'\.get\(["\']([^"\']+)["\']',
                                r'\.post\(["\']([^"\']+)["\']',
                            ]
                            for pattern in ajax_patterns:
                                matches = re.findall(pattern, content)
                                api_calls.extend(matches)
                    
                    if api_calls:
                        api_calls = list(set(api_calls))  # 去重
                        print(f"  - 找到 {len(api_calls)} 个 API 调用:")
                        for call in api_calls[:5]:
                            print(f"    • {call}")
                        info['api_calls'] = api_calls
                else:
                    print(f"  ✗ 失败 (状态码: {response.status_code})")
                
                results.append(info)
                
            except Exception as e:
                print(f"  ✗ 错误: {e}")
        
        # 保存结果
        with open('temp/api_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n✓ 测试结果已保存到: temp/api_test_results.json")
        
        return results
        
    except Exception as e:
        print(f"✗ 测试 API 失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def main():
    """主函数"""
    print("=" * 80)
    print("强智教务系统 - 管理员系统探索工具 (含重新登录)")
    print("=" * 80)
    
    # 创建管理器
    manager = AdminLoginManager(
        base_url="http://58.20.60.39:8099",
        session_file="temp/admin_session.json"
    )
    
    # 加载会话
    manager.load_session()
    
    # 1. 测试会话状态
    session_valid = test_session_and_relogin(manager)
    
    # 2. 如果会话失效，重新登录
    if not session_valid:
        if not relogin(manager):
            print("\n✗ 无法登录，退出")
            return
    
    # 3. 探索主页
    main_url, main_content = explore_main_page(manager)
    
    # 4. 探索左侧菜单
    menu_items = explore_left_menu(manager)
    
    # 5. 测试学籍管理 API
    api_results = test_student_apis(manager, menu_items)
    
    # 总结
    print("\n" + "=" * 80)
    print("探索完成！")
    print("=" * 80)
    print(f"✓ 找到 {len(menu_items)} 个菜单项")
    print(f"✓ 测试了 {len(api_results)} 个 API")
    print("\n所有结果已保存到 temp/ 目录")


if __name__ == '__main__':
    main()
