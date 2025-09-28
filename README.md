# 长沙医学院强智教务系统自动化工具

长沙医学院强智教务系统的自动化登录和完整API访问工具。

## 🚀 功能特性

- ✅ **自动登录** - 支持验证码自动识别和登录重试机制
- ✅ **智能会话管理** - 自动会话持久化、过期检测和重新登录
- ✅ **完整API接口** - 支持个人信息、课程表、成绩、考试安排等功能
- ✅ **智能课表解析** - 支持复杂周次格式解析（如"3-5,8,10-11,13,16-17"）
- ✅ **课程数据拆分** - 自动将课程按周次拆分为独立的课程单元
- ✅ **验证码识别** - 基于ddddocr的高准确率验证码识别
- ✅ **错误重试** - 智能重试机制，提高登录成功率
- ✅ **模块化设计** - 清晰的代码结构，易于维护和扩展

## 🧩 核心模块

### SessionManager 会话管理器
- 自动会话持久化（保存到 `session.json`）
- 会话过期检测和自动重新登录
- 统一的HTTP请求接口
- 支持会话超时配置

### JwglAPI 教务API接口
- 获取用户个人信息
- 获取课程表信息（支持复杂周次格式解析）
- 获取成绩信息（支持学期筛选）
- 获取考试安排
- 获取可用学期列表
- 连接状态测试
- 课程数据拆分（按周次生成课程单元）

### LoginManager 登录管理器
- 验证码自动识别和处理
- 登录重试机制
- 会话Cookie管理

### CaptchaSolver 验证码解决器
- ddddocr OCR识别
- 图像预处理
- 手动输入备选方案

## 📦 安装依赖

```bash
pip install -r requirements.txt
```

## 🔧 快速开始

### 推荐用法：使用SessionManager

```python
from src.session_manager import SessionManager
from src.jwgl_api import JwglAPI

# 1. 创建会话管理器
session_manager = SessionManager(
    base_url="http://58.20.60.39:8099",
    session_file="session.json",
    session_timeout=1800  # 30分钟超时
)

# 2. 设置登录凭据（首次使用）
session_manager.set_login_credentials("你的学号", "你的密码")

# 3. 确保登录状态（自动处理会话加载/登录）
if session_manager.ensure_logged_in():
    print("登录成功！")
    
    # 4. 创建API客户端
    api = JwglAPI(session=session_manager)
    
    # 5. 使用API获取信息
    user_info = api.get_user_info()        # 获取个人信息
    schedule = api.get_schedule()          # 获取课程表（拆分为课程单元）
    grades = api.get_grades()              # 获取成绩
    exams = api.get_exam_schedule()        # 获取考试安排
    
    print(f"用户信息: {user_info}")
    print(f"课程单元数量: {len(schedule)}")  # schedule 现在返回课程单元列表
    
    # 示例：查看第5周的课程安排
    week_5_courses = [unit for unit in schedule if unit['week'] == 5]
    print(f"第5周课程数量: {len(week_5_courses)}")
else:
    print("登录失败")
```

### 会话复用示例

```python
# 第二次运行时，会自动加载保存的会话
sm = SessionManager()
if sm.ensure_logged_in():  # 会尝试加载保存的会话
    print("使用已保存的会话，无需重新登录")
    api = JwglAPI(session=sm)
    # 直接使用API...
```

### 传统登录方式

```python
from src.login_manager import LoginManager

# 直接使用LoginManager
lm = LoginManager("http://58.20.60.39:8099")
result = lm.login(username="你的学号", password="你的密码", auto_captcha=True)

if result['success']:
    print("登录成功！")
    # 使用 lm.session 进行后续请求
else:
    print(f"登录失败: {result['message']}")
```

## 📁 项目结构

```
qiangzhi-jwgl/
├── src/                      # 核心源码
│   ├── __init__.py          # 包初始化
│   ├── login_manager.py     # 登录管理器
│   ├── captcha_solver.py    # 验证码识别
│   ├── jwgl_api.py          # 教务系统API
│   └── session_manager.py   # 会话管理
├── scripts/                 # 测试脚本
│   └── test_session_manager.py  # SessionManager测试
├── requirements.txt        # 依赖列表
├── example_usage.py        # 使用示例
├── test_fixed.py           # 基本测试
└── README.md              # 项目说明
```

## 🧪 测试脚本

项目提供了多个测试脚本：

```bash
# 完整的SessionManager功能测试
python scripts/test_session_manager.py

# 基本登录功能测试
python test_fixed.py

# 使用示例
python example_usage.py
```

## 📅 课表解析功能

### 智能周次格式解析

支持解析各种复杂的周次格式：

- **单个周次**: `5`
- **连续周次**: `3-6`, `10-15`
- **多个周次**: `1,3,5,7`
- **复杂混合**: `3-5,8,10-11,13,16-17`
- **不规则格式**: `1-3周,5-7周`, `第1,3,5周`

### 课程单元拆分

自动将原始课程数据按周次拆分为独立的课程单元：

```python
# 原始数据：一门课在多个周次
{
    "course_name": "高等数学",
    "weeks": "3-5,8,10-11",
    "weekday": "周一",
    "periods": "1-2节"
}

# 拆分后：5个独立的课程单元
[
    {"course_name": "高等数学", "week": 3, "weekday": "周一", "periods": "1-2节", "weeks": "3-5,8,10-11"},
    {"course_name": "高等数学", "week": 4, "weekday": "周一", "periods": "1-2节", "weeks": "3-5,8,10-11"},
    {"course_name": "高等数学", "week": 5, "weekday": "周一", "periods": "1-2节", "weeks": "3-5,8,10-11"},
    {"course_name": "高等数学", "week": 8, "weekday": "周一", "periods": "1-2节", "weeks": "3-5,8,10-11"},
    {"course_name": "高等数学", "week": 10, "weekday": "周一", "periods": "1-2节", "weeks": "3-5,8,10-11"},
    {"course_name": "高等数学", "week": 11, "weekday": "周一", "periods": "1-2节", "weeks": "3-5,8,10-11"}
]
```

### 数据结构

每个课程单元包含以下字段：

```python
{
    "semester": "2024-2025-1",           # 学期
    "week": 5,                           # 具体周次
    "weekday": "周一",                  # 星期
    "time_slot_name": "一二",           # 时间段名称
    "periods": "1-2节",                 # 节次详情
    "course_name": "高等数学",       # 课程名
    "teacher": "张三",                # 教师
    "classroom": "教学楼101",         # 教室
    "weeks": "3-5,8,10-11"             # 原始周次字符串
}
```

## 💯 主要优势

### 会话持久化
- 登录一次，多次使用
- 自动检测会话过期
- 过期时自动重新登录

### API接口完整
- 个人信息查询
- 课程表获取（支持复杂周次解析）
- 成绩查询（支持学期筛选）
- 考试安排查询
- 学期列表获取
- 课程数据智能拆分

### 高可靠性
- 自动重试机制
- 错误恢复能力
- 详细的日志记录
- 异常处理完善

## ⚙️ 配置选项

### SessionManager配置

```python
session_manager = SessionManager(
    base_url="http://58.20.60.39:8099",  # 教务系统URL
    session_file="session.json",          # 会话保存文件
    session_timeout=1800                  # 会话超时时间（秒）
)
```

### LoginManager配置

```python
result = login_manager.login(
    username="your_username",
    password="your_password",
    auto_captcha=True,      # 自动识别验证码
    max_retries=3          # 最大重试次数
)
```

## 🔒 安全说明

- 本工具仅用于个人学习和便利，请勿用于非法用途
- 用户名和密码仅在本地使用，不会上传到任何服务器
- 建议使用配置文件管理敏感信息，避免硬编码

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目基于 MIT 许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

## ⚠️ 免责声明

本工具仅供学习研究使用，使用者需自行承担使用风险。开发者不对因使用本工具而产生的任何后果负责。

## 📞 联系方式

如有问题或建议，请通过 GitHub Issues 联系。