#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取管理员登录页面的 HTML 源码
"""

import requests
from bs4 import BeautifulSoup
import re

def fetch_admin_login_page(url):
    """获取管理员登录页面"""
    try:
        print(f"正在获取页面: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容长度: {len(response.text)} 字符")
        print("\n" + "="*80)
        print("HTML 源码:")
        print("="*80)
        print(response.text)
        
        # 保存到文件
        with open('admin_login_page.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("\n✅ HTML 源码已保存到: admin_login_page.html")
        
        # 使用 BeautifulSoup 解析
        print("\n" + "="*80)
        print("页面分析:")
        print("="*80)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找所有表单
        forms = soup.find_all('form')
        print(f"\n找到 {len(forms)} 个表单:")
        for i, form in enumerate(forms):
            print(f"\n表单 {i+1}:")
            print(f"  action: {form.get('action', 'N/A')}")
            print(f"  method: {form.get('method', 'N/A')}")
            print(f"  id: {form.get('id', 'N/A')}")
            print(f"  name: {form.get('name', 'N/A')}")
            
            # 查找表单中的输入字段
            inputs = form.find_all(['input', 'select', 'textarea'])
            print(f"  输入字段 ({len(inputs)}个):")
            for inp in inputs:
                inp_type = inp.get('type', inp.name)
                inp_name = inp.get('name', 'N/A')
                inp_id = inp.get('id', 'N/A')
                inp_value = inp.get('value', '')
                print(f"    - {inp_type}: name={inp_name}, id={inp_id}, value={inp_value}")
        
        # 查找所有 script 标签
        scripts = soup.find_all('script')
        print(f"\n\n找到 {len(scripts)} 个脚本标签:")
        for i, script in enumerate(scripts):
            src = script.get('src')
            if src:
                print(f"\n脚本 {i+1} (外部): {src}")
            else:
                content = script.string or script.get_text()
                if content and len(content.strip()) > 0:
                    print(f"\n脚本 {i+1} (内联):")
                    print(f"  长度: {len(content)} 字符")
                    # 查找加密相关的函数
                    if 'encode' in content.lower() or 'encrypt' in content.lower() or 'login' in content.lower():
                        print("  内容预览 (前500字符):")
                        print("  " + "-"*70)
                        print("  " + content.strip()[:500])
                        print("  " + "-"*70)
        
        # 查找验证码相关
        print("\n\n验证码检测:")
        captcha_img = soup.find('img', {'id': re.compile(r'.*captcha.*|.*code.*', re.I)})
        if not captcha_img:
            captcha_img = soup.find('img', src=re.compile(r'.*verify.*|.*captcha.*|.*code.*', re.I))
        
        if captcha_img:
            print(f"  ✓ 找到验证码图片:")
            print(f"    src: {captcha_img.get('src', 'N/A')}")
            print(f"    id: {captcha_img.get('id', 'N/A')}")
        else:
            print("  ✗ 未找到验证码图片")
        
        return response.text
        
    except Exception as e:
        print(f"❌ 获取页面失败: {e}")
        return None

if __name__ == "__main__":
    # 管理员登录页面 URL
    admin_url = "http://oa.csmu.edu.cn:8099/"
    
    print("="*80)
    print("强智教务系统 - 管理员登录页面分析工具")
    print("="*80)
    
    fetch_admin_login_page(admin_url)
    
    print("\n\n完成！")
