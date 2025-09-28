#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
强智教务系统自动化工具

本包提供了与强智教务系统交互的核心功能模块。
"""

__version__ = "1.0.0"
__author__ = "JWGL Tools"
__description__ = "强智教务系统自动化工具"

# 导出主要类和函数
from .login_manager import LoginManager
from .captcha_solver import CaptchaSolver

__all__ = [
    'LoginManager',
    'CaptchaSolver'
]