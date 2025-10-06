#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用已保存的 cookie 在浏览器中探索管理员系统
需要先启动 Chrome DevTools Protocol
"""

import json
import sys
import os

def load_session():
    """加载保存的会话"""
    session_file = "temp/admin_session.json"
    
    if not os.path.exists(session_file):
        print(f"✗ 会话文件不存在: {session_file}")
        return None
    
    with open(session_file, 'r', encoding='utf-8') as f:
        session_data = json.load(f)
    
    return session_data


def main():
    """主函数"""
    print("=" * 80)
    print("强智教务系统 - 浏览器探索工具")
    print("=" * 80)
    
    # 加载会话
    session = load_session()
    if not session:
        return
    
    print(f"\n✓ 已加载会话:")
    print(f"  用户名: {session['username']}")
    print(f"  Base URL: {session['base_url']}")
    print(f"  JSESSIONID: {session['cookies']['JSESSIONID']}")
    
    print("\n" + "=" * 80)
    print("接下来请使用 MCP 浏览器工具:")
    print("=" * 80)
    print(f"""
1. 打开浏览器并访问: {session['base_url']}

2. 使用浏览器开发者工具设置 Cookie:
   - 按 F12 打开开发者工具
   - 切换到 Console 标签
   - 执行以下命令:
   
   document.cookie = "JSESSIONID={session['cookies']['JSESSIONID']}; path=/";
   
3. 刷新页面，应该就能看到登录后的界面了

4. 然后可以手动探索学籍管理相关的页面
""")
    
    # 输出一些可能的 URL
    print("\n可能的管理页面 URL:")
    print("-" * 80)
    urls = [
        "/jsxsd/framework/xsMain_new.jsp",
        "/jsxsd/framework/xsMainV.jsp", 
        "/jsxsd/",
        "/jsxsd/framework/main.jsp",
    ]
    
    for url in urls:
        print(f"  {session['base_url']}{url}")


if __name__ == '__main__':
    main()
