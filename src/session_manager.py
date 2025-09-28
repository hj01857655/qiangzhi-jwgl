#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
会话管理器
负责会话的创建、持久化、复用和自动刷新
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional, Callable
import requests
from datetime import datetime, timedelta

try:
    from .login_manager import LoginManager
except ImportError:
    from login_manager import LoginManager


class SessionManager:
    """
    会话管理器
    
    功能：
    1. 自动管理登录会话
    2. 会话持久化和自动加载
    3. 会话过期检测和自动重新登录
    4. 提供统一的请求接口，自动处理会话
    """
    
    def __init__(self, base_url: str = "http://58.20.60.39:8099", 
                 session_file: str = "temp/session.json",
                 session_timeout: int = 1800):  # 30分钟超时
        """
        初始化会话管理器
        
        Args:
            base_url: 教务系统基础URL
            session_file: 会话保存文件路径
            session_timeout: 会话超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.session_file = session_file
        self.session_timeout = session_timeout
        
        self.login_manager = LoginManager(base_url)
        self.session = self.login_manager.session  # 直接使用LoginManager的session，已经配置好代理
        
        self.logger = logging.getLogger(__name__)
        
        # 会话状态
        self._is_logged_in = False
        self._last_activity = None
        self._login_credentials = None
        
        # 自动加载会话
        self._auto_load_session()
    
    def set_login_credentials(self, username: str, password: str):
        """
        设置登录凭据（用于自动重新登录）
        
        Args:
            username: 用户名
            password: 密码
        """
        self._login_credentials = {
            'username': username,
            'password': password
        }
        self.logger.info("登录凭据已设置")
    
    def ensure_logged_in(self) -> bool:
        """
        确保已登录状态
        
        Returns:
            是否成功确保登录状态
        """
        # 1. 检查当前登录状态
        if self._is_session_valid():
            self.logger.debug("会话仍然有效")
            return True
        
        # 2. 尝试加载保存的会话
        if self._load_session():
            if self._is_session_valid():
                self.logger.info("加载的会话有效")
                return True
        
        # 3. 需要重新登录
        return self._auto_login()
    
    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        发起HTTP请求（自动处理会话）
        
        Args:
            method: HTTP方法
            url: 请求URL
            **kwargs: requests参数
            
        Returns:
            Response对象
            
        Raises:
            Exception: 当无法建立有效会话时
        """
        # 确保登录状态
        if not self.ensure_logged_in():
            raise Exception("无法建立有效的登录会话")
        
        # 处理URL
        if not url.startswith('http'):
            url = f"{self.base_url}{url}"
        
        # 设置默认请求头
        headers = kwargs.get('headers', {})
        default_headers = {
            'Referer': f"{self.base_url}/jsxsd/framework/xsMain.jsp",
            'User-Agent': self.session.headers.get('User-Agent')
        }
        default_headers.update(headers)
        kwargs['headers'] = default_headers
        
        try:
            # 发起请求
            response = self.session.request(method, url, **kwargs)
            
            # 更新最后活动时间
            self._last_activity = time.time()
            
            # 检查是否被重定向到登录页（会话过期）
            if self._is_login_redirect(response):
                self.logger.warning("检测到会话过期，尝试重新登录")
                if self._auto_login():
                    # 重新发起请求
                    response = self.session.request(method, url, **kwargs)
                    self._last_activity = time.time()
                else:
                    raise Exception("会话过期且重新登录失败")
            
            self.logger.debug(f"{method} {url} - Status: {response.status_code}")
            return response
            
        except Exception as e:
            self.logger.error(f"请求失败: {method} {url} - {str(e)}")
            raise
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """GET请求"""
        return self.request('GET', url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """POST请求"""
        return self.request('POST', url, **kwargs)
    
    def save_session(self) -> bool:
        """
        保存当前会话
        
        Returns:
            是否保存成功
        """
        try:
            # 处理重复的cookie名称问题
            cookies_dict = {}
            for cookie in self.session.cookies:
                # 如果有重复的cookie名称，保留最新的
                cookies_dict[cookie.name] = {
                    'value': cookie.value,
                    'domain': cookie.domain,
                    'path': cookie.path,
                    'secure': cookie.secure
                }
            
            session_data = {
                'logged_in': self._is_logged_in,
                'last_activity': self._last_activity,
                'cookies': cookies_dict,
                'user_info': getattr(self.login_manager, 'user_info', {}),
                'saved_time': time.time(),
                'base_url': self.base_url
            }
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"会话已保存到: {self.session_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存会话失败: {str(e)}")
            return False
    
    def clear_session(self):
        """清除会话"""
        self._is_logged_in = False
        self._last_activity = None
        self.session.cookies.clear()
        self.login_manager.logged_in = False
        self.login_manager.user_info = {}
        
        # 删除会话文件
        if os.path.exists(self.session_file):
            try:
                os.remove(self.session_file)
                self.logger.info("会话文件已删除")
            except Exception as e:
                self.logger.warning(f"删除会话文件失败: {str(e)}")
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        获取会话信息
        
        Returns:
            会话信息字典
        """
        return {
            'is_logged_in': self._is_logged_in,
            'last_activity': self._last_activity,
            'last_activity_formatted': datetime.fromtimestamp(self._last_activity).strftime('%Y-%m-%d %H:%M:%S') if self._last_activity else None,
            'session_age': time.time() - self._last_activity if self._last_activity else None,
            'base_url': self.base_url,
            'session_file': self.session_file,
            'has_credentials': self._login_credentials is not None,
            'user_info': getattr(self.login_manager, 'user_info', {})
        }
    
    def _auto_load_session(self):
        """自动加载会话"""
        if os.path.exists(self.session_file):
            self.logger.info("发现会话文件，尝试自动加载...")
            if self._load_session():
                if self._is_session_valid():
                    self.logger.info("会话自动加载成功")
                else:
                    self.logger.info("加载的会话已过期")
    
    def _load_session(self) -> bool:
        """
        加载保存的会话
        
        Returns:
            是否加载成功
        """
        try:
            if not os.path.exists(self.session_file):
                return False
            
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # 检查会话是否过期
            saved_time = session_data.get('saved_time', 0)
            if time.time() - saved_time > self.session_timeout:
                self.logger.info("保存的会话已过期")
                return False
            
            # 恢复会话状态
            self._is_logged_in = session_data.get('logged_in', False)
            self._last_activity = session_data.get('last_activity', time.time())
            
            # 恢复cookies
            cookies = session_data.get('cookies', {})
            for name, cookie_info in cookies.items():
                if isinstance(cookie_info, dict):
                    # 新格式：包含cookie详细信息
                    self.session.cookies.set(
                        name, 
                        cookie_info['value'],
                        domain=cookie_info.get('domain'),
                        path=cookie_info.get('path')
                    )
                else:
                    # 兼容旧格式：直接是值
                    self.session.cookies.set(name, cookie_info)
            
            # 恢复用户信息
            self.login_manager.user_info = session_data.get('user_info', {})
            self.login_manager.logged_in = self._is_logged_in
            
            self.logger.info("会话加载成功")
            return True
            
        except Exception as e:
            self.logger.error(f"加载会话失败: {str(e)}")
            return False
    
    def _is_session_valid(self) -> bool:
        """
        检查会话是否有效
        
        Returns:
            会话是否有效
        """
        if not self._is_logged_in or not self._last_activity:
            return False
        
        # 检查超时
        if time.time() - self._last_activity > self.session_timeout:
            self.logger.info("会话已超时")
            return False
        
        # 检查登录状态（直接使用session，避免触发SessionManager的自动重新登录）
        try:
            # 直接使用原始session请求，不通过SessionManager的request方法
            test_response = self.session.get(
                f"{self.base_url}/jsxsd/framework/xsMain.jsp", 
                timeout=5,
                allow_redirects=True  # 允许重定向，这样我们可以检查最终URL
            )
            
            # 检查是否被重定向到登录页
            if self._is_login_redirect(test_response):
                self.logger.info("会话已过期（被重定向到登录页）")
                return False
            
            return test_response.status_code == 200
            
        except Exception as e:
            self.logger.warning(f"会话验证失败: {str(e)}")
            return False
    
    def _is_login_redirect(self, response: requests.Response) -> bool:
        """检查响应是否为登录重定向"""
        # 检查URL是否包含登录相关路径
        login_indicators = ['/login', '/Login', '/jsxsd/xk/LoginToXk', '/jsxsd/$']
        
        if any(indicator in response.url for indicator in login_indicators):
            return True
        
        # 检查响应内容是否包含登录表单
        if '登录' in response.text or 'login' in response.text.lower():
            return True
        
        return False
    
    def _auto_login(self) -> bool:
        """
        自动登录
        
        Returns:
            是否登录成功
        """
        if not self._login_credentials:
            self.logger.error("无法自动登录：未设置登录凭据")
            return False
        
        self.logger.info("开始自动登录...")
        
        try:
            result = self.login_manager.login(
                username=self._login_credentials['username'],
                password=self._login_credentials['password'],
                auto_captcha=True,
                max_retries=3
            )
            
            if result['success']:
                self._is_logged_in = True
                self._last_activity = time.time()
                
                # 保存会话
                self.save_session()
                
                self.logger.info("自动登录成功")
                return True
            else:
                self.logger.error(f"自动登录失败: {result['message']}")
                return False
                
        except Exception as e:
            self.logger.error(f"自动登录异常: {str(e)}")
            return False