"""
管理员登录管理器
复刻登录页面的两步加密逻辑
"""

import requests
from typing import Optional, Dict, Tuple
import re
from urllib.parse import urljoin
import json
from pathlib import Path
import time
from .captcha_solver import CaptchaSolver


class AdminLoginManager:
    """管理员登录管理器，处理两步加密登录流程"""
    
    def __init__(self, base_url: str, session_file: str = 'temp/admin_session.json'):
        """
        初始化登录管理器
        
        Args:
            base_url: 基础URL，例如 "http://example.com"
            session_file: 会话文件路径，默认保存到 temp/admin_session.json
        """
        self.base_url = base_url.rstrip('/')
        self.session_file = Path(session_file)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        self.username = None
        self.password = None
        self.captcha_solver = CaptchaSolver()
        
    def _get_session_code(self) -> Tuple[Optional[str], Optional[str]]:
        """
        第一步：获取会话加密码 (scode) 和插入位置 (sxh)
        
        Returns:
            (scode, sxh) 元组，失败返回 (None, None)
        """
        try:
            url = urljoin(self.base_url, '/Logon.do?method=logon&flag=sess')
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # 响应格式可能是: scode,sxh 或 scode#sxh
            # 例如: "a1b2c3d4e5,2-3-1-4-2" 或 "a1b2c3d4e5#2-3-1-4-2"
            text = response.text.strip()
            
            # 尝试不同的分隔符
            separator = None
            if '#' in text:
                separator = '#'
            elif ',' in text:
                separator = ','
            
            if separator:
                parts = text.split(separator)
                scode = parts[0].strip()
                sxh = parts[1].strip()
                
                print(f"[获取会话码] scode: {scode[:10]}..., sxh: {sxh}")
                return scode, sxh
            else:
                print(f"[错误] 会话码响应格式异常: {text}")
                return None, None
                
        except Exception as e:
            print(f"[错误] 获取会话码失败: {e}")
            return None, None
    
    def _encode_credentials(self, username: str, password: str, 
                           scode: str, sxh: str) -> Tuple[str, str]:
        """
        第二步：按照 sxh 规则将 scode 插入到 username%%%password 中
        
        算法：
        1. 构建原始字符串: username + "%%%" + password
        2. 按 sxh 指定的位置和数量，将 scode 的字符插入到原始字符串中
        3. sxh 格式: "n1-n2-n3-..." 表示依次在位置 pos 插入 n1, n2, n3... 个 scode 字符
        
        Args:
            username: 用户名
            password: 密码
            scode: 会话加密码
            sxh: 插入规则字符串
            
        Returns:
            (encoded_username, encoded_password) - 编码后的用户名和密码
        """
        try:
            # 1. 构建基础字符串
            base_str = f"{username}%%%{password}"
            
            # 2. 解析 sxh 插入规则
            # sxh 可能是 "1-2-3" 或 "123" 格式
            if '-' in sxh:
                counts = [int(x) for x in sxh.split('-')]
            else:
                # 每个字符是一个数字
                counts = [int(c) for c in sxh]
            
            # 3. 使用更高效的算法：构建结果列表
            result = []
            scode_idx = 0
            base_idx = 0
            
            for count in counts:
                # 插入 count 个 scode 字符
                for _ in range(count):
                    if scode_idx < len(scode):
                        result.append(scode[scode_idx])
                        scode_idx += 1
                
                # 添加一个原始字符
                if base_idx < len(base_str):
                    result.append(base_str[base_idx])
                    base_idx += 1
            
            # 4. 添加剩余的原始字符
            while base_idx < len(base_str):
                result.append(base_str[base_idx])
                base_idx += 1
            
            # 5. 添加剩余的 scode 字符
            while scode_idx < len(scode):
                result.append(scode[scode_idx])
                scode_idx += 1
            
            encoded = ''.join(result)
            
            # 5. 分离编码后的用户名和密码
            # 编码后的字符串中仍然包含 "%%%"，以此分割
            if '%%%' in encoded:
                parts = encoded.split('%%%')
                encoded_username = parts[0]
                encoded_password = parts[1] if len(parts) > 1 else ''
            else:
                # 如果没有分隔符，整个作为用户名
                encoded_username = encoded
                encoded_password = ''
            
            print(f"[编码凭据] 原始: {username}%%%{password}")
            print(f"[编码凭据] 编码后用户名长度: {len(encoded_username)}, 密码长度: {len(encoded_password)}")
            
            return encoded_username, encoded_password
            
        except Exception as e:
            print(f"[错误] 编码凭据失败: {e}")
            return username, password
    
    def _get_captcha_url(self) -> str:
        """获取验证码图片URL"""
        return urljoin(self.base_url, '/verifycode.servlet')
    
    def get_captcha_image(self, save_path: Optional[str] = None) -> Optional[bytes]:
        """
        获取验证码图片
        
        Args:
            save_path: 可选，保存验证码图片的路径
            
        Returns:
            验证码图片的字节数据，失败返回 None
        """
        try:
            url = self._get_captcha_url()
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            image_data = response.content
            
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(image_data)
                print(f"[验证码] 已保存到: {save_path}")
            
            return image_data
            
        except Exception as e:
            print(f"[错误] 获取验证码失败: {e}")
            return None
    
    def solve_captcha(self, save_path: Optional[str] = None) -> Optional[str]:
        """
        自动识别验证码
        
        Args:
            save_path: 可选，保存验证码图片的路径
            
        Returns:
            识别结果，失败返回 None
        """
        # 获取验证码图片
        image_data = self.get_captcha_image(save_path=save_path)
        if not image_data:
            print("[错误] 无法获取验证码图片")
            return None
        
        # 识别验证码
        print("[验证码] 正在自动识别...")
        result = self.captcha_solver.solve_captcha(image_data)
        
        if result['success']:
            captcha = result['result']
            print(f"[验证码] 识别成功: {captcha} (引擎: {result.get('engine', 'unknown')})")
            return captcha
        else:
            print(f"[错误] 验证码识别失败: {result.get('message', 'unknown error')}")
            return None
    
    def login(self, username: str, password: str, captcha: Optional[str] = None, 
              userType: str = '1', auto_captcha: bool = False) -> Dict:
        """
        执行登录
        
        Args:
            username: 用户名
            password: 密码
            captcha: 验证码（可选，如果 auto_captcha=True 则自动识别）
            userType: 用户类型，默认 '1' (管理员)
            auto_captcha: 是否自动识别验证码
            
        Returns:
            登录结果字典，包含:
            - success: bool, 是否成功
            - message: str, 消息
            - response: requests.Response, 原始响应对象（如果成功）
        """
        # 处理验证码
        if auto_captcha:
            print("[登录] 启用自动验证码识别")
            captcha = self.solve_captcha()
            if not captcha:
                return {
                    'success': False,
                    'message': '验证码识别失败',
                    'response': None
                }
        elif not captcha:
            return {
                'success': False,
                'message': '未提供验证码',
                'response': None
            }
        
        # 第一步：获取会话加密码
        scode, sxh = self._get_session_code()
        if not scode or not sxh:
            return {
                'success': False,
                'message': '获取会话加密码失败',
                'response': None
            }
        
        # 第二步：编码用户名和密码
        print("[登录] 开始编码凭据...")
        encoded_username, encoded_password = self._encode_credentials(
            username, password, scode, sxh
        )
        print(f"[登录] 编码完成")
        
        # 第三步：提交登录表单
        try:
            login_url = urljoin(self.base_url, '/Logon.do?method=logon')
            print(f"[登录] 准备POST请求到: {login_url}")
            
            data = {
                'userAccount': encoded_username,
                'userPassword': encoded_password,
                'RANDOMCODE': captcha,
                'userType': userType,
                'encoded': 'true'  # 标识已编码
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': urljoin(self.base_url, '/'),
            }
            
            print(f"[登录] 提交登录请求...")
            response = self.session.post(
                login_url, 
                data=data, 
                headers=headers,
                timeout=15,
                allow_redirects=False
            )
            
            print(f"[登录] 收到响应: HTTP {response.status_code}")
            
            # 分析响应
            success = self._check_login_success(response)
            
            if success:
                # 保存用户名和密码（用于会话管理）
                self.username = username
                self.password = password
                
                # 自动保存会话
                self.save_session()
                
                return {
                    'success': True,
                    'message': '登录成功',
                    'response': response
                }
            else:
                error_msg = self._extract_error_message(response)
                return {
                    'success': False,
                    'message': error_msg or '登录失败，请检查用户名、密码和验证码',
                    'response': response
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'登录请求异常: {e}',
                'response': None
            }
    
    def _check_login_success(self, response: requests.Response) -> bool:
        """
        检查登录是否成功
        
        通常的判断标准：
        1. 有重定向到主页/管理页面
        2. 响应中包含成功标识
        3. Cookie中包含会话信息
        """
        # 检查重定向
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get('Location', '')
            print(f"[登录] 重定向到: {location}")
            # 通常重定向到主页表示成功
            if 'main' in location.lower() or 'index' in location.lower():
                return True
        
        # 检查响应内容
        content = response.text.lower()
        
        # 成功标识
        if any(keyword in content for keyword in ['success', '成功', 'welcome']):
            return True
        
        # 失败标识
        if any(keyword in content for keyword in ['error', '错误', 'fail', '失败', '验证码', '用户名', '密码']):
            return False
        
        # 检查Cookie
        if 'JSESSIONID' in self.session.cookies:
            print(f"[登录] 获得会话Cookie")
            return True
        
        return False
    
    def _extract_error_message(self, response: requests.Response) -> Optional[str]:
        """从响应中提取错误消息"""
        try:
            content = response.text
            
            # 尝试匹配常见错误消息模式
            patterns = [
                r'<div[^>]*class=["\']error["\'][^>]*>(.*?)</div>',
                r'<span[^>]*class=["\']error["\'][^>]*>(.*?)</span>',
                r'alert\(["\']([^"\']+)["\']\)',
                r'错误[：:](.*?)(?:<|$)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                if match:
                    msg = match.group(1).strip()
                    # 清理HTML标签
                    msg = re.sub(r'<[^>]+>', '', msg)
                    return msg
            
            return None
            
        except:
            return None
    
    def logout(self) -> bool:
        """
        登出
        
        Returns:
            是否成功登出
        """
        try:
            logout_url = urljoin(self.base_url, '/Logon.do?method=logout')
            response = self.session.get(logout_url, timeout=10)
            print("[登出] 已退出登录")
            return True
        except Exception as e:
            print(f"[错误] 登出失败: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """
        检查是否已登录
        
        Returns:
            是否已登录
        """
        return 'JSESSIONID' in self.session.cookies
    
    def save_session(self) -> bool:
        """
        保存会话到文件
        
        Returns:
            是否成功保存
        """
        try:
            # 确保目录存在
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            
            session_data = {
                'cookies': dict(self.session.cookies),
                'username': self.username,
                'password': self.password,  # 保存密码以支持自动重新登录
                'timestamp': time.time(),
                'base_url': self.base_url
            }
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            print(f"[会话保存] 已保存到: {self.session_file}")
            return True
            
        except Exception as e:
            print(f"[错误] 保存会话失败: {e}")
            return False
    
    def load_session(self) -> bool:
        """
        从文件加载会话
        
        Returns:
            是否成功加载
        """
        try:
            if not self.session_file.exists():
                print(f"[会话加载] 会话文件不存在: {self.session_file}")
                return False
            
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # 恢复cookies
            for name, value in session_data.get('cookies', {}).items():
                self.session.cookies.set(name, value)
            
            self.username = session_data.get('username')
            self.password = session_data.get('password')  # 恢复密码
            saved_base_url = session_data.get('base_url')
            
            # 检查URL是否匹配
            if saved_base_url != self.base_url:
                print(f"[警告] 会话URL不匹配: 保存={saved_base_url}, 当前={self.base_url}")
            
            # 显示会话时间
            timestamp = session_data.get('timestamp', 0)
            age = time.time() - timestamp
            print(f"[会话加载] 已加载会话 (用户: {self.username}, 距今: {int(age)}秒)")
            
            return True
            
        except Exception as e:
            print(f"[错误] 加载会话失败: {e}")
            return False
    
    def set_credentials(self, username: str, password: str):
        """
        设置登录凭据
        
        Args:
            username: 用户名
            password: 密码
        """
        self.username = username
        self.password = password
    
    def ensure_logged_in(self, captcha: Optional[str] = None, auto_captcha: bool = True) -> bool:
        """
        确保已登录（尝试加载会话或重新登录）
        
        Args:
            captcha: 验证码（可选，如果 auto_captcha=True 则自动识别）
            auto_captcha: 是否自动识别验证码，默认 True
            
        Returns:
            是否成功登录
        """
        # 1. 尝试加载已保存的会话
        if self.load_session() and self.is_logged_in():
            print("[会话管理] 使用已保存的会话")
            return True
        
        # 2. 如果没有凭据，无法登录
        if not self.username or not self.password:
            print("[错误] 未设置登录凭据，请先调用 set_credentials()")
            return False
        
        # 3. 需要重新登录
        if not captcha and not auto_captcha:
            print("[错误] 需要验证码或启用自动识别")
            return False
        
        print("[会话管理] 需要重新登录...")
        result = self.login(self.username, self.password, captcha, auto_captcha=auto_captcha)
        
        if result['success']:
            # 保存新会话
            self.save_session()
            return True
        else:
            print(f"[错误] 登录失败: {result['message']}")
            return False


def main():
    """示例：如何使用 AdminLoginManager"""
    
    # 1. 创建登录管理器
    base_url = "http://your-domain.com"  # 替换为实际的基础URL
    manager = AdminLoginManager(base_url)
    
    # 2. 获取验证码
    print("=" * 60)
    print("获取验证码...")
    captcha_image = manager.get_captcha_image(save_path='captcha.png')
    
    if not captcha_image:
        print("获取验证码失败！")
        return
    
    print("验证码已保存到 captcha.png，请查看并输入验证码")
    
    # 3. 输入登录信息
    username = input("用户名: ").strip()
    password = input("密码: ").strip()
    captcha = input("验证码: ").strip()
    
    # 4. 执行登录
    print("=" * 60)
    print("执行登录...")
    result = manager.login(username, password, captcha)
    
    # 5. 处理结果
    print("=" * 60)
    if result['success']:
        print("✓ 登录成功！")
        print(f"会话信息: {manager.session.cookies.get_dict()}")
        
        # 可以继续使用 manager.session 进行其他操作
        # 例如: manager.session.get('/some-admin-page')
        
        # 登出
        input("\n按回车键登出...")
        manager.logout()
    else:
        print(f"✗ 登录失败: {result['message']}")


if __name__ == '__main__':
    main()
