#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
强智教务系统登录管理模块 - 修复版
专门负责用户认证、Session管理等登录相关功能
"""

import requests
import base64
import time
import random
import logging
from typing import Dict, Any
import re
import json
import os

try:
    from .captcha_solver import CaptchaSolver
except ImportError:
    from captcha_solver import CaptchaSolver


class LoginManager:
    """强智教务系统登录管理器 - 修复版"""
    
    def __init__(self, base_url: str = "http://58.20.60.39:8099"):
        """
        初始化登录管理器
        
        Args:
            base_url: 教务系统基础URL（默认为长沙医学院）
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.logged_in = False
        self.user_info = {}
        self.captcha_solver = CaptchaSolver()
        
        # 禁用代理（用于教务系统直连）
        self.session.proxies = {
            'http': None,
            'https': None
        }
        
        # 设置通用请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                         '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        
        self.logger = logging.getLogger(__name__)
        
    def _encode_inp(self, input_str: str) -> str:
        """
        Base64编码（encodeInp函数）
        
        Args:
            input_str: 输入字符串
            
        Returns:
            Base64编码的结果
        """
        return base64.b64encode(input_str.encode('utf-8')).decode('ascii')
        
    def _get_captcha_image(self, save_path: str = None) -> Dict[str, Any]:
        """
        获取验证码图片（在同一会话中）
        
        Args:
            save_path: 保存路径（可选）
            
        Returns:
            验证码图片信息
        """
        try:
            timestamp = int(time.time() * 1000)
            captcha_url = f"{self.base_url}/jsxsd/verifycode.servlet"
            captcha_params = {
                't': str(timestamp), 
                '_': str(timestamp + random.randint(1, 999))
            }
            captcha_headers = {
                'Referer': f"{self.base_url}/jsxsd/",
                'Accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            }
            
            response = self.session.get(captcha_url, params=captcha_params, 
                                       headers=captcha_headers, timeout=10)
            
            self.logger.info(f"验证码响应: {response.status_code}, 长度: {len(response.content)} bytes")
            
            if response.status_code != 200 or len(response.content) == 0:
                return {'success': False, 'message': '验证码获取失败'}
            
            if save_path:
                with open(save_path, "wb") as f:
                    f.write(response.content)
            
            return {
                'success': True,
                'image_data': response.content
            }
            
        except Exception as e:
            self.logger.error(f"获取验证码失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def login(self, username: str, password: str, captcha: str = "", auto_captcha: bool = True, max_retries: int = 3) -> Dict[str, Any]:
        """
        执行登录操作（修复版）
        
        Args:
            username: 用户名
            password: 密码
            captcha: 验证码（如果为空且auto_captcha=True，将自动识别）
            auto_captcha: 是否自动识别验证码
            max_retries: 验证码错误时的最大重试次数
            
        Returns:
            登录结果
        """
        for retry_count in range(max_retries):
            try:
                self.logger.info(f"开始登录尝试 {retry_count + 1}/{max_retries} - 用户名: {username}")
                
                # 1. 建立会话（只在第一次或重试时建立新会话）
                if retry_count == 0:
                    self.logger.info("步骤1: 建立会话...")
                    main_response = self.session.get(f"{self.base_url}/jsxsd/", timeout=10)
                    if main_response.status_code != 200:
                        return {'success': False, 'message': f'主页访问失败: {main_response.status_code}'}
                    
                    self.logger.info(f"会话建立成功，Cookie: {list(self.session.cookies.keys())}")
                    # 等待会话建立完成
                    time.sleep(2)
                
                # 2. 获取验证码（每次尝试都重新获取）
                current_captcha = captcha
                if not current_captcha and auto_captcha:
                    self.logger.info(f"步骤2: 自动获取验证码... (第{retry_count + 1}次)")
                    captcha_info = self._get_captcha_image(f"temp/captcha_retry_{retry_count}.png")
                    if captcha_info['success']:
                        # 自动识别
                        ocr_result = self.captcha_solver.solve_captcha(captcha_info['image_data'])
                        if ocr_result and ocr_result['success']:
                            current_captcha = ocr_result['result']  # 不要改变大小写！
                            self.logger.info(f"验证码识别成功: {current_captcha}")
                        else:
                            self.logger.warning("验证码OCR识别失败")
                            if retry_count == max_retries - 1:  # 最后一次尝试
                                return {'success': False, 'message': '验证码识别失败'}
                            continue
                    else:
                        self.logger.warning(f"验证码获取失败: {captcha_info['message']}")
                        if retry_count == max_retries - 1:
                            return {'success': False, 'message': f'验证码获取失败: {captcha_info["message"]}'}
                        continue
                
                if not current_captcha:
                    return {'success': False, 'message': '需要验证码'}
                
                # 3. 准备登录数据
                self.logger.info("步骤3: 准备登录数据...")
                encoded_username = self._encode_inp(username.strip())
                encoded_password = self._encode_inp(password)
                encoded_value = f"{encoded_username}%%%{encoded_password}"
                
                login_data = {
                    'encoded': encoded_value,
                    'RANDOMCODE': current_captcha  # 保持原始大小写！
                }
                
                self.logger.info(f"登录数据准备完成: encoded={encoded_value[:30]}..., captcha={current_captcha}")
                
                # 4. 立即执行登录（不要再等待！）
                self.logger.info("步骤4: 执行登录...")
                login_headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': f"{self.base_url}/jsxsd/",
                    'Origin': self.base_url
                }
                
                login_response = self.session.post(f"{self.base_url}/jsxsd/xk/LoginToXk", 
                                                 data=login_data, headers=login_headers, timeout=10)
                
                self.logger.info(f"登录响应: {login_response.status_code}, URL: {login_response.url}")
                
                # 5. 检查结果
                if login_response.url == f"{self.base_url}/jsxsd/framework/xsMain.jsp":
                    self.logged_in = True
                    self.logger.info("登录成功!")
                    return {
                        'success': True,
                        'message': '登录成功',
                        'redirect_url': login_response.url
                    }
                else:
                    # 查找错误信息
                    error_message = re.findall(r'<font.*?color.*?>(.*?)</font>', login_response.text)
                    if error_message:
                        error = error_message[0].strip()
                        self.logger.info(f"登录失败: {error}")
                        
                        # 如果是验证码错误，尝试重试
                        if "验证码" in error and retry_count < max_retries - 1:
                            self.logger.info(f"验证码错误，将重试 ({retry_count + 2}/{max_retries})...")
                            continue
                        
                        return {'success': False, 'message': error}
                    else:
                        return {'success': False, 'message': '登录失败，原因未知'}
                        
            except Exception as e:
                self.logger.error(f"登录尝试 {retry_count + 1} 异常: {e}")
                if retry_count == max_retries - 1:
                    return {'success': False, 'message': str(e)}
                continue
        
        return {'success': False, 'message': f'登录失败，已重试{max_retries}次'}
    
    def check_login_status(self) -> bool:
        """
        检查登录状态
        
        Returns:
            是否已登录
        """
        if not self.logged_in:
            return False
            
        try:
            # 尝试访问主页检查登录状态
            response = self.session.get(f"{self.base_url}/jsxsd/framework/xsMain.jsp", timeout=5)
            return response.status_code == 200 and "xsMain" in response.url
        except:
            return False
    
    def get_user_info(self) -> Dict[str, Any]:
        """
        获取用户信息
        
        Returns:
            用户信息字典
        """
        return self.user_info.copy()
    
    def logout(self) -> bool:
        """
        退出登录
        
        Returns:
            是否成功退出
        """
        try:
            if self.logged_in:
                self.session.get(f"{self.base_url}/jsxsd/logout", timeout=5)
            
            self.logged_in = False
            self.user_info = {}
            self.session.cookies.clear()
            return True
        except:
            return False
    
    def save_session(self, file_path: str) -> bool:
        """
        保存会话到文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否成功保存
        """
        try:
            session_data = {
                'logged_in': self.logged_in,
                'user_info': self.user_info,
                'cookies': dict(self.session.cookies)
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            self.logger.error(f"保存会话失败: {e}")
            return False
    
    def load_session(self, file_path: str) -> bool:
        """
        从文件加载会话
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否成功加载
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            self.logged_in = session_data.get('logged_in', False)
            self.user_info = session_data.get('user_info', {})
            
            cookies = session_data.get('cookies', {})
            for name, value in cookies.items():
                self.session.cookies.set(name, value)
            
            # 验证会话是否仍然有效
            if self.logged_in and not self.check_login_status():
                self.logged_in = False
                self.user_info = {}
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"加载会话失败: {e}")
            return False