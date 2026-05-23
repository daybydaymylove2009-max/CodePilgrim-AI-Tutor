import asyncio
import sys
import uuid

sys.path.insert(0, ".")

from app.db.session import get_db
from app.models.models import Course, CourseChapter, KnowledgePoint
from sqlalchemy import select, delete, func

COURSES_DATA = [
    {
        "title": "Python 编程从入门到实践（第3版）",
        "subtitle": "Python Crash Course, 3rd Edition — Eric Matthes 经典畅销书",
        "author": "Eric Matthes",
        "edition": "第3版",
        "publisher": "人民邮电出版社",
        "isbn": "978-7-115-61308-8",
        "language": "python",
        "description": "本书是针对所有层次的 Python 读者而作的 Python 入门书。全书分两部分：第一部分介绍用 Python 编程所必须了解的基本概念，包括变量、列表、字典、if 语句、类、函数、文件与异常、测试等；第二部分将理论付诸实践，包含三个项目：开发一个游戏（Alien Invasion）、数据可视化、Web 应用程序（Django）。",
        "difficulty_range": "1-3",
        "estimated_hours": 60.0,
        "sort_order": 1,
        "chapters": [
            {"part": 1, "part_title": "基础知识", "chapters": [
                {"num": 1, "title": "起步", "difficulty": 1, "minutes": 30,
                 "objectives": ["在不同操作系统中搭建 Python 编程环境", "运行 Python 解释器与第一个程序", "理解 Python 的发展历史与设计哲学", "安装和配置文本编辑器"],
                 "concepts": ["Python 安装", "解释器", "VS Code", "终端运行", "hello_world.py"],
                 "kp_titles": ["变量、类型与表达式"]},
                {"num": 2, "title": "变量和简单数据类型", "difficulty": 1, "minutes": 45,
                 "objectives": ["掌握变量的命名规则与最佳实践", "理解字符串操作与格式化方法", "掌握数值运算与类型转换", "理解 Python 之禅与编码规范"],
                 "concepts": ["变量命名", "字符串方法", "f-string", "数值类型", "PEP 8"],
                 "kp_titles": ["变量、类型与表达式", "字符串处理与编码"]},
                {"num": 3, "title": "列表简介", "difficulty": 1, "minutes": 60,
                 "objectives": ["掌握列表的创建与基本操作", "理解索引、切片与遍历", "学会列表元素的增删改", "理解列表的动态特性"],
                 "concepts": ["列表索引", "append/insert", "del/pop/remove", "切片", "遍历"],
                 "kp_titles": ["数据结构：列表、元组与解构"]},
                {"num": 4, "title": "操作列表", "difficulty": 1, "minutes": 60,
                 "objectives": ["掌握 for 循环遍历列表", "学会列表推导式与数值列表", "理解元组与列表的区别", "掌握列表切片与复制"],
                 "concepts": ["for 循环", "range()", "列表推导式", "元组", "切片复制"],
                 "kp_titles": ["迭代与循环控制", "数据结构：列表、元组与解构"]},
                {"num": 5, "title": "if 语句", "difficulty": 1, "minutes": 45,
                 "objectives": ["掌握条件测试与布尔表达式", "学会 if-elif-else 结构", "理解条件与列表的结合使用", "掌握真值测试与短路求值"],
                 "concepts": ["条件测试", "if-elif-else", "布尔表达式", "in/not in", "真值测试"],
                 "kp_titles": ["条件逻辑与布尔代数"]},
                {"num": 6, "title": "字典", "difficulty": 2, "minutes": 60,
                 "objectives": ["掌握字典的创建与操作", "理解键值对与嵌套结构", "学会字典遍历与排序", "掌握在列表中存储字典等嵌套模式"],
                 "concepts": ["键值对", "字典方法", "嵌套字典", "遍历", "字典推导式"],
                 "kp_titles": ["数据结构：字典、集合与哈希"]},
                {"num": 7, "title": "用户输入和 while 循环", "difficulty": 1, "minutes": 45,
                 "objectives": ["掌握 input() 获取用户输入", "理解类型转换与输入验证", "学会 while 循环与退出条件", "掌握标志位与 break/continue"],
                 "concepts": ["input()", "int()/float()", "while 循环", "标志位", "break"],
                 "kp_titles": ["迭代与循环控制", "条件逻辑与布尔代数"]},
                {"num": 8, "title": "函数", "difficulty": 2, "minutes": 90,
                 "objectives": ["掌握函数定义与调用", "理解实参与形参的传递方式", "掌握返回值与默认参数", "学会传递任意数量的实参", "理解模块与导入"],
                 "concepts": ["def", "位置参数", "关键字参数", "默认值", "*args/**kwargs", "模块"],
                 "kp_titles": ["函数设计与作用域", "模块系统与包管理"]},
                {"num": 9, "title": "类", "difficulty": 3, "minutes": 90,
                 "objectives": ["掌握类的创建与实例化", "理解 __init__ 方法与 self", "掌握属性与方法的定义", "学会继承与重写", "理解导入类与模块组织"],
                 "concepts": ["__init__", "self", "属性", "方法", "继承", "super()", "模块组织"],
                 "kp_titles": ["面向对象设计"]},
                {"num": 10, "title": "文件和异常", "difficulty": 2, "minutes": 75,
                 "objectives": ["掌握文件读写操作", "理解 with 语句与上下文管理", "学会异常处理 try-except", "掌握 JSON 数据存储", "理解静默异常与异常设计"],
                 "concepts": ["open/read/write", "with 语句", "try-except", "JSON", "异常设计"],
                 "kp_titles": ["文件 I/O 与序列化", "错误处理与防御性编程"]},
                {"num": 11, "title": "测试代码", "difficulty": 2, "minutes": 60,
                 "objectives": ["掌握 pytest 编写单元测试", "理解测试类与测试方法", "学会断言与夹具(fixture)", "掌握测试覆盖与持续集成"],
                 "concepts": ["pytest", "断言", "测试类", "fixture", "覆盖率"],
                 "kp_titles": ["测试策略与质量保障"]},
            ]},
            {"part": 2, "part_title": "项目一：外星人入侵", "chapters": [
                {"num": 12, "title": "武装飞船", "difficulty": 2, "minutes": 90,
                 "objectives": ["掌握 Pygame 游戏开发框架", "理解游戏循环与事件驱动", "学会创建游戏窗口与渲染图像", "掌握飞船控制与按键响应"],
                 "concepts": ["Pygame", "游戏循环", "事件处理", "Surface", "blit"],
                 "kp_titles": ["迭代与循环控制", "面向对象设计"]},
                {"num": 13, "title": "外星人", "difficulty": 3, "minutes": 90,
                 "objectives": ["学会创建外星人群", "理解碰撞检测机制", "掌握游戏实体管理", "理解游戏循环中的更新与绘制"],
                 "concepts": ["精灵(Sprite)", "编组(Group)", "碰撞检测", "实体管理", "游戏循环"],
                 "kp_titles": ["面向对象设计", "迭代与循环控制"]},
                {"num": 14, "title": "计分", "difficulty": 2, "minutes": 60,
                 "objectives": ["实现游戏计分系统", "理解游戏状态管理", "学会显示文字与按钮", "掌握游戏难度递增机制"],
                 "concepts": ["状态管理", "计分板", "按钮", "难度递增", "游戏结束"],
                 "kp_titles": ["面向对象设计", "数据结构：字典、集合与哈希"]},
            ]},
            {"part": 3, "part_title": "项目二：数据可视化", "chapters": [
                {"num": 15, "title": "生成数据", "difficulty": 2, "minutes": 75,
                 "objectives": ["掌握 matplotlib 数据绘图", "学会生成随机数据与数学函数", "理解折线图与散点图", "掌握图表样式与自定义"],
                 "concepts": ["matplotlib", "pyplot", "折线图", "散点图", "随机漫步"],
                 "kp_titles": ["数据结构：列表、元组与解构", "迭代与循环控制"]},
                {"num": 16, "title": "下载数据", "difficulty": 2, "minutes": 60,
                 "objectives": ["掌握 CSV 文件读取与处理", "学会解析 JSON 数据", "理解数据清洗与转换", "掌握日期时间处理"],
                 "concepts": ["csv 模块", "JSON 解析", "数据清洗", "datetime", "异常处理"],
                 "kp_titles": ["文件 I/O 与序列化", "错误处理与防御性编程"]},
                {"num": 17, "title": "使用 API", "difficulty": 3, "minutes": 75,
                 "objectives": ["掌握 requests 库调用 Web API", "理解 RESTful API 响应格式", "学会处理分页与速率限制", "掌握数据可视化与交互式图表"],
                 "concepts": ["requests", "REST API", "JSON 响应", "分页", "Plotly"],
                 "kp_titles": ["API 设计与实现", "错误处理与防御性编程"]},
            ]},
            {"part": 4, "part_title": "项目三：Web 应用程序", "chapters": [
                {"num": 18, "title": "Django 入门", "difficulty": 3, "minutes": 90,
                 "objectives": ["掌握 Django 项目创建与配置", "理解 MTV 架构模式", "学会创建应用与模型", "掌握管理员站点配置"],
                 "concepts": ["Django", "MTV", "模型", "视图", "URL 配置", "admin"],
                 "kp_titles": ["API 设计与实现", "数据库与 ORM"]},
                {"num": 19, "title": "用户账户", "difficulty": 3, "minutes": 90,
                 "objectives": ["实现用户注册与登录系统", "理解认证与授权机制", "学会表单处理与验证", "掌握用户权限与访问控制"],
                 "concepts": ["认证", "注册/登录", "表单", "权限", "会话管理"],
                 "kp_titles": ["安全编程", "API 设计与实现"]},
                {"num": 20, "title": "设置应用程序的样式并部署", "difficulty": 3, "minutes": 75,
                 "objectives": ["掌握 Bootstrap 样式集成", "理解静态文件管理", "学会部署到云平台", "掌握生产环境安全配置"],
                 "concepts": ["Bootstrap", "静态文件", "部署", "Heroku/Platform.sh", "环境变量"],
                 "kp_titles": ["部署与容器化", "安全编程"]},
            ]},
        ]
    },
    {
        "title": "Python 学习手册（第5版）",
        "subtitle": "Learning Python, 5th Edition — Mark Lutz 经典巨著",
        "author": "Mark Lutz",
        "edition": "第5版",
        "publisher": "O'Reilly Media / 机械工业出版社",
        "isbn": "978-7-111-57539-0",
        "language": "python",
        "description": "本书是学习 Python 编程语言的权威指南，以全面深入著称。全书分为7大部分，从基础语法到高级特性，系统性地覆盖了 Python 语言的方方面面。适合希望深入理解 Python 语言本质的开发者。",
        "difficulty_range": "1-4",
        "estimated_hours": 120.0,
        "sort_order": 2,
        "chapters": [
            {"part": 1, "part_title": "Getting Started — 入门", "chapters": [
                {"num": 1, "title": "A Python Q&A Session — Python 问答", "difficulty": 1, "minutes": 30,
                 "objectives": ["了解 Python 的设计哲学与应用场景", "理解 Python 与其他语言的区别", "了解 Python 的技术优势与局限"],
                 "concepts": ["Python 哲学", "解释型语言", "动态类型", "应用领域"],
                 "kp_titles": ["变量、类型与表达式"]},
                {"num": 2, "title": "How Python Runs Programs — Python 执行模型", "difficulty": 1, "minutes": 45,
                 "objectives": ["理解 Python 解释器的工作原理", "掌握字节码编译与执行过程", "理解 CPython 的实现架构"],
                 "concepts": ["解释器", "字节码", "CPython", "虚拟机", "pyc 文件"],
                 "kp_titles": ["变量、类型与表达式"]},
                {"num": 3, "title": "How You Run Programs — 运行 Python 程序", "difficulty": 1, "minutes": 30,
                 "objectives": ["掌握多种运行 Python 程序的方式", "理解模块导入与执行的区别", "学会使用命令行与 IDE"],
                 "concepts": ["交互模式", "脚本模式", "模块导入", "shebang", "IDE"],
                 "kp_titles": ["模块系统与包管理"]},
            ]},
            {"part": 2, "part_title": "Types and Operations — 类型与操作", "chapters": [
                {"num": 4, "title": "Introducing Python Object Types — Python 对象类型", "difficulty": 1, "minutes": 60,
                 "objectives": ["理解 Python 一切皆对象的哲学", "掌握核心内置类型分类", "理解可变与不可变类型"],
                 "concepts": ["对象模型", "内置类型", "可变性", "引用语义", "类型分类"],
                 "kp_titles": ["变量、类型与表达式", "数据结构：列表、元组与解构"]},
                {"num": 5, "title": "Numeric Types — 数值类型", "difficulty": 1, "minutes": 45,
                 "objectives": ["掌握整数与浮点数操作", "理解数值精度问题", "掌握复数与分数类型", "了解小整数池与缓存"],
                 "concepts": ["整数", "浮点数", "精度", "complex", "decimal", "小整数池"],
                 "kp_titles": ["变量、类型与表达式"]},
                {"num": 6, "title": "The Dynamic Typing Interlude — 动态类型", "difficulty": 2, "minutes": 60,
                 "objectives": ["深入理解动态类型机制", "掌握引用语义与对象生命周期", "理解垃圾回收机制", "区分共享引用与拷贝"],
                 "concepts": ["引用语义", "对象生命周期", "引用计数", "GC", "深浅拷贝"],
                 "kp_titles": ["变量、类型与表达式", "数据结构：列表、元组与解构"]},
                {"num": 7, "title": "String Fundamentals — 字符串基础", "difficulty": 1, "minutes": 60,
                 "objectives": ["掌握字符串操作与方法", "理解字符串不可变性", "掌握格式化方法", "理解字节与字符串的区别"],
                 "concepts": ["字符串方法", "不可变性", "格式化", "bytes vs str", "编码"],
                 "kp_titles": ["字符串处理与编码"]},
                {"num": 8, "title": "Strings in Depth — 字符串深入", "difficulty": 2, "minutes": 75,
                 "objectives": ["掌握正则表达式高级用法", "理解 Unicode 编码体系", "掌握字符串性能优化", "学会文本处理模式"],
                 "concepts": ["正则表达式", "Unicode", "性能优化", "文本处理", "re 模块"],
                 "kp_titles": ["字符串处理与编码"]},
                {"num": 9, "title": "Lists and Dictionaries — 列表与字典", "difficulty": 2, "minutes": 90,
                 "objectives": ["掌握列表与字典的高级操作", "理解推导式与生成器表达式", "掌握字典视图与排序", "理解性能特征与选择策略"],
                 "concepts": ["列表推导式", "字典视图", "排序", "性能", "选择策略"],
                 "kp_titles": ["数据结构：列表、元组与解构", "数据结构：字典、集合与哈希"]},
                {"num": 10, "title": "Tuples, Files, and Everything Else — 元组、文件及其他", "difficulty": 2, "minutes": 75,
                 "objectives": ["掌握元组与命名元组", "理解文件操作与上下文管理", "掌握集合与冻结集合", "理解类型完整性"],
                 "concepts": ["namedtuple", "文件操作", "集合", "frozenset", "上下文管理"],
                 "kp_titles": ["数据结构：列表、元组与解构", "文件 I/O 与序列化"]},
            ]},
            {"part": 3, "part_title": "Statements and Syntax — 语句与语法", "chapters": [
                {"num": 11, "title": "Assignment, Expressions, and Print — 赋值、表达式与打印", "difficulty": 1, "minutes": 45,
                 "objectives": ["掌握赋值语句与解构赋值", "理解表达式与语句的区别", "掌握 print 与格式化输出"],
                 "concepts": ["赋值", "解构", "增强赋值", "表达式", "print"],
                 "kp_titles": ["变量、类型与表达式"]},
                {"num": 12, "title": "if Tests — 条件测试", "difficulty": 1, "minutes": 45,
                 "objectives": ["掌握 if/elif/else 语法", "理解真值测试规则", "掌握三元表达式", "学会卫语句模式"],
                 "concepts": ["真值测试", "三元表达式", "布尔运算", "短路求值", "卫语句"],
                 "kp_titles": ["条件逻辑与布尔代数"]},
                {"num": 13, "title": "while and for Loops — 循环", "difficulty": 1, "minutes": 60,
                 "objectives": ["掌握 while 和 for 循环", "理解循环 else 子句", "掌握 break/continue", "理解迭代协议"],
                 "concepts": ["while", "for", "else 子句", "迭代协议", "range"],
                 "kp_titles": ["迭代与循环控制"]},
                {"num": 14, "title": "Iterations and Comprehensions — 迭代与推导式", "difficulty": 2, "minutes": 75,
                 "objectives": ["掌握列表/字典/集合推导式", "理解生成器表达式", "掌握嵌套推导式", "理解迭代工具 itertools"],
                 "concepts": ["推导式", "生成器表达式", "itertools", "嵌套推导", "迭代工具"],
                 "kp_titles": ["迭代与循环控制", "生成器与协程"]},
            ]},
            {"part": 4, "part_title": "Functions — 函数", "chapters": [
                {"num": 15, "title": "Function Basics — 函数基础", "difficulty": 2, "minutes": 60,
                 "objectives": ["掌握函数定义与调用", "理解 def 语句与 lambda", "掌握返回值与 yield"],
                 "concepts": ["def", "lambda", "return", "yield", "作用域"],
                 "kp_titles": ["函数设计与作用域"]},
                {"num": 16, "title": "Scopes — 作用域", "difficulty": 2, "minutes": 75,
                 "objectives": ["深入理解 LEGB 作用域规则", "掌握 global 与 nonlocal", "理解闭包与自由变量", "掌握嵌套作用域"],
                 "concepts": ["LEGB", "global", "nonlocal", "闭包", "自由变量"],
                 "kp_titles": ["函数设计与作用域"]},
                {"num": 17, "title": "Arguments — 参数", "difficulty": 2, "minutes": 75,
                 "objectives": ["掌握参数传递机制", "理解 *args/**kwargs", "掌握默认参数与关键字参数", "理解参数解包"],
                 "concepts": ["位置参数", "关键字参数", "*args", "**kwargs", "默认参数陷阱"],
                 "kp_titles": ["函数设计与作用域"]},
                {"num": 18, "title": "Advanced Function Topics — 函数高级主题", "difficulty": 3, "minutes": 90,
                 "objectives": ["掌握装饰器原理与实现", "理解函数注解与类型标注", "掌握 map/filter/reduce", "学会函数式编程模式"],
                 "concepts": ["装饰器", "函数注解", "map/filter/reduce", "偏函数", "函数式编程"],
                 "kp_titles": ["函数设计与作用域", "生成器与协程"]},
            ]},
            {"part": 5, "part_title": "Modules — 模块", "chapters": [
                {"num": 19, "title": "Modules: The Big Picture — 模块全景", "difficulty": 2, "minutes": 45,
                 "objectives": ["理解模块的创建与使用", "掌握 import 语句与搜索路径", "理解模块命名空间"],
                 "concepts": ["import", "from", "搜索路径", "命名空间", "__name__"],
                 "kp_titles": ["模块系统与包管理"]},
                {"num": 20, "title": "Module Coding Basics — 模块编码基础", "difficulty": 2, "minutes": 60,
                 "objectives": ["掌握模块创建与导入", "理解 __all__ 与命名空间", "学会模块重载与测试"],
                 "concepts": ["__all__", "命名空间", "重载", "模块测试", "__main__"],
                 "kp_titles": ["模块系统与包管理"]},
                {"num": 21, "title": "Module Packages — 模块包", "difficulty": 2, "minutes": 60,
                 "objectives": ["掌握包结构与 __init__.py", "理解相对导入与绝对导入", "学会命名空间包"],
                 "concepts": ["__init__.py", "相对导入", "绝对导入", "命名空间包", "包结构"],
                 "kp_titles": ["模块系统与包管理"]},
                {"num": 22, "title": "Advanced Module Topics — 模块高级主题", "difficulty": 3, "minutes": 60,
                 "objectives": ["理解动态导入与插件模式", "掌握 pyproject.toml 配置", "学会依赖管理与虚拟环境"],
                 "concepts": ["动态导入", "插件", "pyproject.toml", "pip", "虚拟环境"],
                 "kp_titles": ["模块系统与包管理"]},
            ]},
            {"part": 6, "part_title": "Classes and OOP — 类与面向对象", "chapters": [
                {"num": 23, "title": "OOP: The Big Picture — 面向对象全景", "difficulty": 2, "minutes": 45,
                 "objectives": ["理解面向对象编程范式", "掌握类与实例的关系", "理解 Python OOP 的特殊性"],
                 "concepts": ["OOP 范式", "类与实例", "属性与方法", "多态", "封装"],
                 "kp_titles": ["面向对象设计"]},
                {"num": 24, "title": "Class Coding Basics — 类编码基础", "difficulty": 2, "minutes": 75,
                 "objectives": ["掌握类定义与实例化", "理解 __init__ 与 __new__", "掌握属性访问与方法调用"],
                 "concepts": ["__init__", "__new__", "self", "实例属性", "类属性"],
                 "kp_titles": ["面向对象设计"]},
                {"num": 25, "title": "A More Realistic Example — 实战案例", "difficulty": 3, "minutes": 90,
                 "objectives": ["学会设计完整的类层次结构", "掌握组合与继承的选择", "理解接口与抽象基类"],
                 "concepts": ["类设计", "组合 vs 继承", "ABC", "接口", "多态"],
                 "kp_titles": ["面向对象设计", "设计模式与架构原则"]},
                {"num": 26, "title": "Class Coding Details — 类编码细节", "difficulty": 3, "minutes": 90,
                 "objectives": ["理解运算符重载", "掌握描述符协议", "理解 MRO 与 super()", "掌握 __slots__"],
                 "concepts": ["运算符重载", "描述符", "MRO", "super()", "__slots__"],
                 "kp_titles": ["面向对象设计"]},
                {"num": 27, "title": "Designing with Classes — 类设计", "difficulty": 3, "minutes": 90,
                 "objectives": ["掌握常见设计模式的 Python 实现", "理解委托与组合模式", "学会数据类的使用"],
                 "concepts": ["设计模式", "委托", "组合", "dataclass", "namedtuple"],
                 "kp_titles": ["面向对象设计", "设计模式与架构原则"]},
                {"num": 28, "title": "Advanced Class Topics — 类高级主题", "difficulty": 4, "minutes": 90,
                 "objectives": ["理解元类与类装饰器", "掌握属性描述符高级用法", "理解静态方法与类方法", "掌握 __call__ 与可调用对象"],
                 "concepts": ["元类", "类装饰器", "描述符", "__call__", "类型注解"],
                 "kp_titles": ["面向对象设计", "类型系统与静态分析"]},
            ]},
            {"part": 7, "part_title": "Exceptions and Tools — 异常与工具", "chapters": [
                {"num": 29, "title": "Exception Basics — 异常基础", "difficulty": 2, "minutes": 60,
                 "objectives": ["掌握 try/except/finally", "理解异常传播机制", "掌握 raise 与 assert"],
                 "concepts": ["try/except", "异常传播", "raise", "assert", "finally"],
                 "kp_titles": ["错误处理与防御性编程"]},
                {"num": 30, "title": "Exception Coding Details — 异常编码细节", "difficulty": 3, "minutes": 75,
                 "objectives": ["掌握自定义异常设计", "理解异常链与 raise from", "学会上下文管理器与 contextlib"],
                 "concepts": ["自定义异常", "异常链", "contextlib", "上下文管理器", "异常层次"],
                 "kp_titles": ["错误处理与防御性编程"]},
                {"num": 31, "title": "Designing with Exceptions — 异常设计", "difficulty": 3, "minutes": 60,
                 "objectives": ["理解异常设计的最佳实践", "掌握异常与调试策略", "学会防御性编程模式"],
                 "concepts": ["异常设计原则", "调试", "防御性编程", "快速失败", "优雅降级"],
                 "kp_titles": ["错误处理与防御性编程", "设计模式与架构原则"]},
            ]},
        ]
    },
]


async def seed():
    async for db in get_db():
        r = await db.execute(select(Course).limit(1))
        if r.scalar_one_or_none():
            print("Clearing existing courses...")
            await db.execute(delete(CourseChapter))
            await db.execute(delete(Course))
            await db.flush()

        kp_title_to_id: dict[str, str] = {}
        r = await db.execute(select(KnowledgePoint.id, KnowledgePoint.title).where(KnowledgePoint.topic == "python"))
        for row in r:
            kp_title_to_id[row[1]] = str(row[0])
        print(f"Found {len(kp_title_to_id)} Python knowledge points")

        for course_data in COURSES_DATA:
            total_chapters = sum(len(part["chapters"]) for part in course_data["chapters"])
            course = Course(
                id=str(uuid.uuid4()),
                title=course_data["title"],
                subtitle=course_data.get("subtitle"),
                author=course_data.get("author"),
                edition=course_data.get("edition"),
                publisher=course_data.get("publisher"),
                isbn=course_data.get("isbn"),
                language=course_data["language"],
                description=course_data.get("description"),
                difficulty_range=course_data.get("difficulty_range"),
                estimated_hours=course_data.get("estimated_hours"),
                total_chapters=total_chapters,
                sort_order=course_data.get("sort_order", 0),
            )
            db.add(course)
            await db.flush()
            print(f"\nCourse: {course.title} ({total_chapters} chapters)")

            global_chapter_num = 0
            for part in course_data["chapters"]:
                for ch_data in part["chapters"]:
                    global_chapter_num += 1
                    matched_kp_ids = []
                    for kp_title in ch_data.get("kp_titles", []):
                        if kp_title in kp_title_to_id:
                            matched_kp_ids.append(kp_title_to_id[kp_title])
                        else:
                            print(f"  WARNING: KP not found: {kp_title}")

                    chapter = CourseChapter(
                        id=str(uuid.uuid4()),
                        course_id=course.id,
                        part_number=part["part"],
                        part_title=part.get("part_title"),
                        chapter_number=global_chapter_num,
                        chapter_title=ch_data["title"],
                        description=ch_data.get("description"),
                        estimated_minutes=ch_data.get("minutes"),
                        difficulty=ch_data["difficulty"],
                        kp_ids=matched_kp_ids if matched_kp_ids else None,
                        learning_objectives=ch_data.get("objectives"),
                        key_concepts=ch_data.get("concepts"),
                    )
                    db.add(chapter)
                    matched = len(matched_kp_ids)
                    total = len(ch_data.get("kp_titles", []))
                    print(f"  Ch{global_chapter_num}: {ch_data['title']} (KP: {matched}/{total})")

        await db.commit()

        r = await db.execute(select(func.count()).select_from(Course))
        course_count = r.scalar()
        r = await db.execute(select(func.count()).select_from(CourseChapter))
        chapter_count = r.scalar()
        print(f"\nSeeded {course_count} courses, {chapter_count} chapters.")
        break


if __name__ == "__main__":
    asyncio.run(seed())
