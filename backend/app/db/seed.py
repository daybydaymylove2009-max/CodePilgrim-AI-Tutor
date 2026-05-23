import asyncio
import sys
import uuid

sys.path.insert(0, ".")

from app.db.session import get_db
from app.models.models import KnowledgePoint, KnowledgeEdge
from sqlalchemy import select, delete


PYTHON_KPS = [
    {"title": "变量、类型与表达式", "topic": "python", "difficulty": 1, "irt_b_param": -2.0,
     "description": "Python 动态类型系统的核心机制：变量的引用语义、基本数据类型（int/float/str/bool/None）、类型推断与显式转换、运算符优先级与短路求值。理解 Python 中一切皆对象，变量是对象的引用而非容器。CPython 中小整数池(-5~256)和字符串驻留(intern)机制对性能的影响。",
     "learning_objectives": ["理解 Python 引用语义与不可变类型的区别", "掌握类型推断与显式类型转换", "熟练使用运算符与表达式", "理解短路求值在条件表达式中的应用", "了解 CPython 小整数池与字符串驻留机制"],
     "code_examples": ["x = 42          # int, 不可变\ny = 3.14        # float, 不可变\ns = 'hello'     # str, 不可变\nflag = True     # bool, 不可变\n\n# 引用语义演示 — 生产级代码必须理解\na = [1, 2, 3]\nb = a            # b 指向同一对象（浅引用）\nb.append(4)\nprint(a)         # [1, 2, 3, 4] — a 也变了！\n\nc = a.copy()     # 浅拷贝，独立对象\nc.append(5)\nprint(a)         # [1, 2, 3, 4] — a 不受影响\n\n# 小整数池\nprint(id(256) == id(256))   # True — 同一对象\nprint(id(257) == id(257))   # True (同一行) 但跨行可能 False"]},

    {"title": "字符串处理与编码", "topic": "python", "difficulty": 1, "irt_b_param": -1.5,
     "description": "字符串是不可变序列，掌握 Unicode 编码（UCS-2/UCS-4 内部表示）、格式化方法（f-string/format/%）、常用方法（split/join/replace/strip/regex）、原始字符串与转义、多行字符串。生产环境中需关注编码安全（SQL注入防护）、性能（join vs +=）和国际化（locale/gettext）。",
     "learning_objectives": ["理解 Unicode 与 UTF-8/UTF-16 编码关系", "掌握 f-string 与 format 高级用法", "熟练使用正则表达式进行文本处理", "了解字符串性能优化（join vs +）", "掌握编码安全与国际化基础"],
     "code_examples": ["import re\nfrom datetime import datetime\n\n# f-string 高级用法（Python 3.12+ 支持嵌套引号）\nuser = {'name': 'Alice', 'score': 95.678}\nprint(f\"{user['name']:>10} => {user['score']:.2f}\")\n\n# 正则提取 — 日志解析是生产常见场景\nlog = '2024-01-15 ERROR [auth] Login failed for user=admin'\npattern = r'(\\d{4}-\\d{2}-\\d{2})\\s+(\\w+)\\s+\\[(\\w+)\\]\\s+(.+)'\nmatch = re.match(pattern, log)\nif match:\n    date, level, module, msg = match.groups()\n    print(f'{date} | {level} | {module} | {msg}')\n\n# 性能：join vs +（生产代码必须用 join）\nparts = ['hello'] * 10000\nresult = ''.join(parts)  # O(n) 推荐\n# result = '' + ''.join(parts)  # 避免 += 循环拼接 O(n^2)"]},

    {"title": "条件逻辑与布尔代数", "topic": "python", "difficulty": 1, "irt_b_param": -1.2,
     "description": "深入理解 Python 的真值测试（truthiness）、三元表达式、walrus 运算符(:=)、match-case 模式匹配（3.10+）、条件表达式的短路求值。生产级代码需避免深层嵌套，使用卫语句和策略模式。理解 __bool__ 和 __len__ 如何影响真值测试。",
     "learning_objectives": ["掌握 Python 真值测试规则与 __bool__/__len__", "熟练使用三元表达式和 walrus 运算符", "理解 match-case 模式匹配与穷尽检查", "学会卫语句替代深层嵌套"],
     "code_examples": ["# 卫语句（Guard Clauses）— 生产级代码标准模式\ndef process_order(order):\n    if not order:\n        return None\n    if not order.get('items'):\n        return {'status': 'empty'}\n    if order.get('total', 0) <= 0:\n        return {'status': 'invalid'}\n    # 主逻辑 — 扁平化，无嵌套\n    return {'status': 'ok', 'total': order['total']}\n\n# Walrus 运算符 — 减少重复计算\nimport re\nif (match := re.search(r'\\d+', 'abc42def')):\n    print(f'Found number: {match.group()}')\n\n# match-case (Python 3.10+) — 结构化模式匹配\ncommand = {'action': 'move', 'direction': 'up', 'speed': 5}\nmatch command:\n    case {'action': 'move', 'direction': d, 'speed': s}:\n        print(f'Moving {d} at speed {s}')\n    case {'action': 'stop'}:\n        print('Stopping')\n    case _:\n        raise ValueError(f'Unknown command: {command}')"]},

    {"title": "迭代与循环控制", "topic": "python", "difficulty": 1, "irt_b_param": -1.0,
     "description": "for/while 循环的完整语义：迭代协议(__iter__/__next__)、enumerate/zip/itertools、循环中的 else 子句、break/continue/return 控制流。生产级代码优先使用迭代器和生成器替代手动循环，itertools 是高效数据处理的利器。",
     "learning_objectives": ["理解迭代协议与可迭代对象", "掌握 enumerate/zip/itertools 常用函数", "理解循环 else 子句语义", "学会用迭代器替代手动循环"],
     "code_examples": ["from itertools import chain, groupby, islice, product\n\n# enumerate + zip 组合\nnames = ['Alice', 'Bob', 'Charlie']\nscores = [95, 87, 92]\nfor i, (name, score) in enumerate(zip(names, scores), 1):\n    print(f'{i}. {name}: {score}')\n\n# itertools.groupby 分组 — 注意必须先排序\ndata = [('A', 1), ('A', 2), ('B', 3), ('B', 4)]\ndata.sort(key=lambda x: x[0])  # groupby 要求有序\nfor key, group in groupby(data, key=lambda x: x[0]):\n    values = [x[1] for x in group]\n    print(f'{key}: {values}')\n\n# itertools.product — 笛卡尔积\ncolors = ['red', 'blue']\nsizes = ['S', 'M']\nfor color, size in product(colors, sizes):\n    print(f'{color}-{size}')"]},

    {"title": "函数设计与作用域", "topic": "python", "difficulty": 2, "irt_b_param": -0.5,
     "description": "函数是一等公民：参数绑定机制、*args/**kwargs、默认参数陷阱、LEGB 作用域规则、闭包与自由变量、装饰器基础。生产级函数设计遵循单一职责、纯函数优先、显式优于隐式。理解 keyword-only 和 positional-only 参数。",
     "learning_objectives": ["理解参数绑定与默认参数陷阱", "掌握 LEGB 作用域规则", "理解闭包与自由变量机制", "学会使用装饰器增强函数行为", "掌握 keyword-only 和 positional-only 参数"],
     "code_examples": ["from functools import wraps\nimport time\n\n# 默认参数陷阱 — 生产级代码必须避免\ndef append_to(item, lst=None):  # 正确：用 None\n    if lst is None:\n        lst = []\n    lst.append(item)\n    return lst\n\n# keyword-only 参数（Python 3+）\ndef fetch(url: str, *, timeout: int = 30, retries: int = 3) -> dict:\n    pass\n\n# 装饰器：计时与重试\ndef retry(max_attempts=3, delay=1.0):\n    def decorator(func):\n        @wraps(func)\n        def wrapper(*args, **kwargs):\n            for attempt in range(1, max_attempts + 1):\n                try:\n                    return func(*args, **kwargs)\n                except Exception as e:\n                    if attempt == max_attempts:\n                        raise\n                    time.sleep(delay * attempt)\n        return wrapper\n    return decorator\n\n@retry(max_attempts=3, delay=0.5)\ndef fetch_data(url):\n    pass"]},

    {"title": "数据结构：列表、元组与解构", "topic": "python", "difficulty": 2, "irt_b_param": -0.3,
     "description": "列表是动态数组（CPython 实现为 PyObject* 数组，O(1) 尾部追加，O(n) 中间插入），元组是不可变序列。掌握列表推导式、切片赋值、序列解构、namedtuple/dataclass 替代元组。生产环境需关注内存占用（__slots__）和性能特征。",
     "learning_objectives": ["理解列表底层实现与性能特征", "掌握列表推导式与生成器表达式", "熟练使用序列解构与星号表达式", "学会选择 namedtuple/dataclass 替代元组", "理解 __slots__ 对内存的优化"],
     "code_examples": ["from collections import namedtuple\nfrom dataclasses import dataclass, field\n\n# 列表推导式 vs 生成器表达式\nnums = range(1000000)\nsquares_list = [x**2 for x in nums]          # 立即计算，占内存\nsquares_gen = (x**2 for x in nums)            # 惰性计算，省内存\n\n# 序列解构\nfirst, *middle, last = [1, 2, 3, 4, 5]\nprint(first, middle, last)  # 1 [2, 3, 4] 5\n\n# dataclass — 生产级数据类\n@dataclass(frozen=True, slots=True)  # slots=True (3.10+) 节省内存\nclass Vector:\n    x: float\n    y: float\n    def magnitude(self) -> float:\n        return (self.x**2 + self.y**2)**0.5\n\n# namedtuple — 轻量级不可变记录\nPoint = namedtuple('Point', ['x', 'y'])\np = Point(3, 4)\nprint(p.x, p.y)"]},

    {"title": "数据结构：字典、集合与哈希", "topic": "python", "difficulty": 2, "irt_b_param": 0.0,
     "description": "字典是哈希表实现（Python 3.7+ 保证插入顺序，3.6 CPython 实现即有序），集合是无序唯一元素集。掌握 defaultdict/Counter/OrderedDict/ChainMap、字典推导式、哈希性与可哈希对象、集合运算。生产环境需理解哈希冲突、时间复杂度和内存开销。",
     "learning_objectives": ["理解字典底层哈希表实现与有序性保证", "掌握 defaultdict/Counter/ChainMap", "理解哈希性与 __hash__/__eq__ 协议", "学会集合运算与去重策略"],
     "code_examples": ["from collections import defaultdict, Counter, ChainMap\n\n# defaultdict — 消除 KeyError，生产代码常用\ngroups = defaultdict(list)\nfor name, dept in [('Alice', 'eng'), ('Bob', 'eng'), ('Carol', 'hr')]:\n    groups[dept].append(name)\nprint(dict(groups))\n\n# Counter — 频率统计\nwords = 'the cat sat on the mat the cat'.split()\nword_counts = Counter(words)\nprint(word_counts.most_common(2))\n\n# ChainMap — 多字典合并查询（配置层叠）\ndefaults = {'theme': 'dark', 'lang': 'en', 'timeout': 30}\nuser_prefs = {'lang': 'zh'}\nenv_overrides = {'timeout': 60}\nconfig = ChainMap(env_overrides, user_prefs, defaults)\nprint(config['theme'], config['lang'], config['timeout'])  # dark zh 60"]},

    {"title": "面向对象设计", "topic": "python", "difficulty": 3, "irt_b_param": 0.5,
     "description": "Python OOP 的完整体系：类创建与实例化机制(__new__/__init__)、属性描述符协议(__get__/__set__/__delete__)、MRO 与 super()、抽象基类(ABC)、数据模型方法(__str__/__repr__/__eq__/__lt__等)、__slots__ 内存优化、类方法与静态方法。理解 Python 的多继承 MRO C3 线性化算法。",
     "learning_objectives": ["理解 __new__ 与 __init__ 的区别", "掌握描述符协议与 property", "理解 MRO 与 super() 的 C3 线性化", "学会使用 ABC 定义接口契约", "理解 __slots__ 内存优化机制"],
     "code_examples": ["from abc import ABC, abstractmethod\nfrom functools import total_ordering\n\n@total_ordering\nclass Money:\n    __slots__ = ('_amount', '_currency')  # 节省 ~40% 内存\n\n    def __init__(self, amount: float, currency: str = 'CNY'):\n        self._amount = amount\n        self._currency = currency\n\n    @property\n    def amount(self) -> float:\n        return self._amount\n\n    def __eq__(self, other):\n        if not isinstance(other, Money):\n            return NotImplemented\n        return self._amount == other._amount\n\n    def __lt__(self, other):\n        if not isinstance(other, Money):\n            return NotImplemented\n        return self._amount < other._amount\n\n    def __repr__(self):\n        return f'Money({self._amount:.2f}, {self._currency!r})'\n\nclass PaymentProcessor(ABC):\n    @abstractmethod\n    def charge(self, money: Money) -> bool: ...\n    @abstractmethod\n    def refund(self, transaction_id: str) -> bool: ..."]},

    {"title": "生成器与协程", "topic": "python", "difficulty": 3, "irt_b_param": 1.0,
     "description": "生成器是惰性计算的基石：yield 语义、生成器表达式、send()/throw()/close()、yield from 委托、协程与 async/await 的关系。生产级数据处理管道优先使用生成器实现流式处理，避免内存溢出。理解生成器在背压(backpressure)和资源管理中的应用。",
     "learning_objectives": ["理解 yield 的执行语义与状态保存", "掌握 send()/throw() 实现协程通信", "理解 yield from 委托机制", "学会用生成器构建数据处理管道"],
     "code_examples": ["import csv\nfrom pathlib import Path\n\n# 生成器管道：流式处理大文件 — 生产级模式\ndef read_csv(filepath):\n    with open(filepath, encoding='utf-8') as f:\n        reader = csv.DictReader(f)\n        yield from reader  # 委托给 DictReader 的迭代器\n\ndef filter_active(records):\n    for r in records:\n        if r['status'] == 'active':\n            yield r\n\ndef transform(records):\n    for r in records:\n        yield {\n            'name': r['name'].strip().title(),\n            'score': float(r['score']),\n        }\n\n# 惰性管道 — 数据不会一次性加载到内存\npipeline = transform(filter_active(read_csv('data.csv')))\nfor record in pipeline:\n    print(record)\n\n# send() 协程 — 双向通信\ndef accumulator():\n    total = 0\n    while True:\n        value = yield total\n        if value is None:\n            break\n        total += value\n\ngen = accumulator()\nnext(gen)          # 启动协程\ngen.send(10)       # 10\ngen.send(20)       # 30"]},

    {"title": "异步编程 (asyncio)", "topic": "python", "difficulty": 3, "irt_b_param": 1.2,
     "description": "asyncio 事件循环模型：async/await 语法、Task 与 Future、asyncio.gather/wait、信号量与锁、异步上下文管理器、异步迭代器。生产级异步需关注事件循环阻塞（CPU密集任务应用 run_in_executor）、取消语义、异常传播和超时控制。",
     "learning_objectives": ["理解事件循环与协程调度", "掌握 asyncio.gather/wait 并发控制", "理解 asyncio.Lock/Semaphore 同步原语", "学会处理异步异常与取消", "理解 run_in_executor 处理 CPU 密集任务"],
     "code_examples": ["import asyncio\nfrom aiohttp import ClientSession\n\nasync def fetch_json(session: ClientSession, url: str) -> dict:\n    async with session.get(url, timeout=asyncio.ClientTimeout(total=10)) as resp:\n        resp.raise_for_status()\n        return await resp.json()\n\nasync def fetch_all(urls: list[str], max_concurrent: int = 5) -> list[dict]:\n    semaphore = asyncio.Semaphore(max_concurrent)\n\n    async def bounded_fetch(session, url):\n        async with semaphore:\n            return await fetch_json(session, url)\n\n    async with ClientSession() as session:\n        tasks = [bounded_fetch(session, url) for url in urls]\n        results = await asyncio.gather(*tasks, return_exceptions=True)\n\n    return [r for r in results if not isinstance(r, Exception)]\n\n# CPU 密集任务用 run_in_executor\nasync def compute_heavy(data):\n    loop = asyncio.get_running_loop()\n    result = await loop.run_in_executor(None, heavy_computation, data)\n    return result"]},

    {"title": "类型系统与静态分析", "topic": "python", "difficulty": 3, "irt_b_param": 1.0,
     "description": "Python 类型标注体系：Type Hints 语法、Generic/Protocol/TypeVar、TypedDict/NamedTuple、类型窄化(TypeGuard/isinstance)、ParamSpec/Concatenate、mypy/pyright 静态检查。生产级代码必须使用类型标注，配合 CI 中的静态分析。理解 nominal typing vs structural typing(Protocol)。",
     "learning_objectives": ["掌握 Type Hints 完整语法", "理解 Generic/Protocol/TypeVar", "学会 TypedDict 与类型窄化", "配置 mypy/pyright 严格模式", "理解 nominal vs structural typing"],
     "code_examples": ["from typing import Generic, TypeVar, Protocol, TypeGuard\nfrom dataclasses import dataclass\n\nT = TypeVar('T')\n\n@dataclass\nclass Stack(Generic[T]):\n    _items: list[T]\n\n    def __init__(self) -> None:\n        self._items = []\n\n    def push(self, item: T) -> None:\n        self._items.append(item)\n\n    def pop(self) -> T:\n        if not self._items:\n            raise IndexError('pop from empty stack')\n        return self._items.pop()\n\n# Protocol — 结构化类型（鸭子类型的类型安全版）\nclass Sortable(Protocol):\n    def __lt__(self, other: object) -> bool: ...\n\ndef find_min(items: list[Sortable]) -> Sortable:\n    return min(items)\n\n# TypeGuard — 用户定义的类型窄化\ndef is_str_list(val: list[object]) -> TypeGuard[list[str]]:\n    return all(isinstance(x, str) for x in val)"]},

    {"title": "错误处理与防御性编程", "topic": "python", "difficulty": 2, "irt_b_param": 0.3,
     "description": "异常层次体系、自定义异常与异常链(raise from)、上下文管理器(__enter__/__exit__)、contextlib 工具、断言与契约式编程。生产级错误处理遵循：可恢复异常向上传播、不可恢复异常快速失败、资源确保释放。理解异常对性能的影响和 try/except 的最佳放置位置。",
     "learning_objectives": ["掌握异常层次与自定义异常设计", "理解 raise from 异常链与 __cause__", "熟练使用上下文管理器与 contextlib", "学会契约式编程与断言策略"],
     "code_examples": ["from contextlib import contextmanager, suppress\n\nclass AppError(Exception):\n    def __init__(self, message: str, code: str, detail: dict | None = None):\n        super().__init__(message)\n        self.code = code\n        self.detail = detail or {}\n\nclass ValidationError(AppError):\n    def __init__(self, field: str, reason: str):\n        super().__init__(f'Validation failed: {field} - {reason}',\n                         code='VALIDATION_ERROR', detail={'field': field})\n\n@contextmanager\ndef transaction(db_conn):\n    try:\n        yield db_conn\n        db_conn.commit()\n    except Exception:\n        db_conn.rollback()\n        raise\n\n# suppress — 忽略指定异常（比 try/except pass 更清晰）\nwith suppress(FileNotFoundError):\n    import os; os.remove('temp.log')\n\n# 异常链 — 保留原始上下文\ntry:\n    value = int('abc')\nexcept ValueError as e:\n    raise ValidationError('amount', 'Must be numeric') from e"]},

    {"title": "模块系统与包管理", "topic": "python", "difficulty": 2, "irt_b_param": 0.0,
     "description": "import 机制与搜索路径、__init__.py 与命名空间包、相对导入与绝对导入、pyproject.toml 项目配置、虚拟环境管理(venv/conda)、依赖锁定与可复现构建(poetry/pdm/uv)。生产级项目必须使用 pyproject.toml + 锁文件，理解依赖解析与安全审计(pip-audit)。",
     "learning_objectives": ["理解 import 搜索路径与模块缓存", "掌握 pyproject.toml 配置标准", "理解命名空间包与相对导入", "学会依赖管理与可复现构建", "了解依赖安全审计"],
     "code_examples": ["# pyproject.toml (PEP 621 项目配置标准)\n# [project]\n# name = \"myapp\"\n# version = \"1.0.0\"\n# requires-python = \">=3.11\"\n# dependencies = [\n#     \"fastapi>=0.100\",\n#     \"sqlalchemy[asyncio]>=2.0\",\n#     \"pydantic>=2.0\",\n# ]\n# [project.optional-dependencies]\n# dev = [\"pytest>=7.0\", \"mypy>=1.0\", \"ruff>=0.1\"]\n\n# 模块导出控制\n# myapp/__init__.py\nfrom myapp.core import App, Config\nfrom myapp.models import User\n\n__all__ = ['App', 'Config', 'User']\n__version__ = '1.0.0'\n\n# 延迟导入（避免循环依赖 — 生产代码常见模式）\ndef get_db():\n    from myapp.database import SessionLocal\n    return SessionLocal()"]},

    {"title": "数据库与 ORM", "topic": "python", "difficulty": 3, "irt_b_param": 0.8,
     "description": "SQLAlchemy 2.0 异步 ORM：声明式映射(Mapped/DeclarativeBase)、会话管理(async_sessionmaker)、关系映射(relationship/lazy loading/eager loading)、迁移管理(Alembic)、连接池配置、事务隔离级别。生产级数据库操作必须使用连接池、异步会话和迁移管理。",
     "learning_objectives": ["掌握 SQLAlchemy 2.0 声明式映射", "理解异步会话管理与连接池", "掌握关系映射与加载策略", "学会 Alembic 数据库迁移", "理解事务隔离级别与并发控制"],
     "code_examples": ["from sqlalchemy import String, Integer, ForeignKey, select\nfrom sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase\nfrom sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker\n\nclass Base(DeclarativeBase): pass\n\nclass User(Base):\n    __tablename__ = 'users'\n    id: Mapped[int] = mapped_column(primary_key=True)\n    name: Mapped[str] = mapped_column(String(100))\n    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)\n    posts: Mapped[list['Post']] = relationship(back_populates='author', lazy='selectin')\n\nclass Post(Base):\n    __tablename__ = 'posts'\n    id: Mapped[int] = mapped_column(primary_key=True)\n    title: Mapped[str] = mapped_column(String(200))\n    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)\n    author: Mapped['User'] = relationship(back_populates='posts')\n\n# 异步会话\nengine = create_async_engine('postgresql+asyncpg://...', pool_size=20, max_overflow=10)\nAsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)\n\nasync def get_user_with_posts(user_id: int) -> User | None:\n    async with AsyncSessionLocal() as session:\n        stmt = select(User).where(User.id == user_id).options(selectinload(User.posts))\n        result = await session.execute(stmt)\n        return result.scalar_one_or_none()"]},

    {"title": "API 设计与实现", "topic": "python", "difficulty": 3, "irt_b_param": 0.7,
     "description": "FastAPI 生产级 API 设计：路由组织(APIRouter)、依赖注入(Depends)、请求验证(Pydantic V2 model)、响应模型(response_model)、中间件、版本管理、OpenAPI 文档定制。理解 RESTful 设计原则、HATEOAS、API 版本策略和幂等性保证。",
     "learning_objectives": ["掌握 FastAPI 路由组织与依赖注入", "理解 Pydantic V2 模型验证与序列化", "学会 API 版本管理与向后兼容", "掌握中间件与请求生命周期", "理解 RESTful 设计原则与幂等性"],
     "code_examples": ["from fastapi import APIRouter, Depends, HTTPException, status\nfrom pydantic import BaseModel, Field\nfrom typing import Annotated\n\nrouter = APIRouter(prefix='/api/v1/users', tags=['users'])\n\nclass CreateUserRequest(BaseModel):\n    name: str = Field(..., min_length=1, max_length=100)\n    email: str = Field(..., pattern=r'^[\\w.-]+@[\\w.-]+\\.\\w+$')\n\nclass UserResponse(BaseModel):\n    id: int\n    name: str\n    email: str\n    model_config = {'from_attributes': True}\n\nasync def get_db_session():\n    async with AsyncSessionLocal() as session:\n        yield session\n\nDbSession = Annotated[AsyncSession, Depends(get_db_session)]\n\n@router.post('', response_model=UserResponse, status_code=status.HTTP_201_CREATED)\nasync def create_user(data: CreateUserRequest, db: DbSession):\n    existing = await db.execute(select(User).where(User.email == data.email))\n    if existing.scalar_one_or_none():\n        raise HTTPException(status_code=409, detail='Email already registered')\n    user = User(**data.model_dump())\n    db.add(user)\n    await db.commit()\n    await db.refresh(user)\n    return user"]},

    {"title": "安全编程", "topic": "python", "difficulty": 3, "irt_b_param": 1.0,
     "description": "OWASP Top 10 在 Python 中的防护：SQL 注入（参数化查询）、XSS（输出编码）、CSRF（令牌验证）、认证与授权(JWT/OAuth2)、密码哈希(bcrypt/argon2)、输入验证与清洗、安全头配置。生产级应用必须实施纵深防御策略。",
     "learning_objectives": ["理解 OWASP Top 10 安全风险", "掌握 SQL 注入与 XSS 防护", "学会 JWT/OAuth2 认证实现", "掌握密码哈希与安全存储", "理解安全头与 CORS 配置"],
     "code_examples": ["import bcrypt\nimport secrets\nfrom datetime import datetime, timedelta, timezone\nimport jwt\n\n# 密码哈希 — 生产级必须使用 bcrypt/argon2\ndef hash_password(password: str) -> str:\n    salt = bcrypt.gensalt(rounds=12)\n    return bcrypt.hashpw(password.encode(), salt).decode()\n\ndef verify_password(password: str, hashed: str) -> bool:\n    return bcrypt.checkpw(password.encode(), hashed.encode())\n\n# JWT Token 生成与验证\nSECRET_KEY = secrets.token_urlsafe(32)\n\ndef create_access_token(user_id: int, expires_delta: timedelta = timedelta(hours=1)) -> str:\n    payload = {\n        'sub': str(user_id),\n        'exp': datetime.now(timezone.utc) + expires_delta,\n        'iat': datetime.now(timezone.utc),\n        'jti': secrets.token_urlsafe(16),  # JWT ID 防重放\n    }\n    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')\n\n# SQL 注入防护 — 永远不要用 f-string 拼接 SQL\n# 错误: f\"SELECT * FROM users WHERE id = {user_id}\"\n# 正确: 使用参数化查询\nstmt = select(User).where(User.id == user_id)"]},

    {"title": "可观测性：日志、指标与追踪", "topic": "python", "difficulty": 3, "irt_b_param": 1.2,
     "description": "生产级可观测性三支柱：结构化日志(logging + structlog)、指标收集(Prometheus client)、分布式追踪(OpenTelemetry)。理解日志级别策略、关联ID(correlation ID)传播、SLO/SLI 定义。可观测性是生产系统诊断问题的生命线。",
     "learning_objectives": ["掌握结构化日志与 structlog", "理解 Prometheus 指标类型(Counter/Gauge/Histogram/Summary)", "学会 OpenTelemetry 分布式追踪", "理解关联 ID 与上下文传播", "掌握日志级别策略与告警配置"],
     "code_examples": ["import structlog\nfrom opentelemetry import trace\nfrom prometheus_client import Counter, Histogram\n\nlogger = structlog.get_logger()\n\nREQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])\nREQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])\ntracer = trace.get_tracer(__name__)\n\nasync def process_order(order_id: str):\n    with tracer.start_as_current_span('process_order') as span:\n        span.set_attribute('order.id', order_id)\n        logger.info('processing_order', order_id=order_id)\n\n        with REQUEST_LATENCY.labels(method='POST', endpoint='/orders').time():\n            try:\n                result = await do_process(order_id)\n                REQUEST_COUNT.labels(method='POST', endpoint='/orders', status='200').inc()\n                return result\n            except Exception as e:\n                REQUEST_COUNT.labels(method='POST', endpoint='/orders', status='500').inc()\n                span.record_exception(e)\n                logger.error('order_failed', order_id=order_id, error=str(e))\n                raise"]},

    {"title": "并发模式", "topic": "python", "difficulty": 4, "irt_b_param": 1.5,
     "description": "Python 并发三模型：多线程(threading + GIL 限制)、多进程(multiprocessing + 进程间通信)、异步(asyncio + 事件循环)。concurrent.futures 高级接口、进程池与线程池选择策略、GIL 的工作原理与绕过方式。生产级并发需根据任务类型(CPU密集/IO密集)选择合适模型。",
     "learning_objectives": ["理解 GIL 工作原理与限制", "区分多线程/多进程/异步的适用场景", "掌握 concurrent.futures 高级接口", "学会进程池与线程池的选择策略", "理解进程间通信与数据共享"],
     "code_examples": ["from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed\nimport asyncio\n\n# IO 密集 → 线程池或异步\ndef fetch_url(url: str) -> dict:\n    import urllib.request\n    with urllib.request.urlopen(url, timeout=10) as resp:\n        return {'url': url, 'status': resp.status}\n\nurls = ['https://httpbin.org/get'] * 5\n\nwith ThreadPoolExecutor(max_workers=5) as pool:\n    futures = {pool.submit(fetch_url, url): url for url in urls}\n    for future in as_completed(futures):\n        result = future.result()\n        print(result)\n\n# CPU 密集 → 进程池（绕过 GIL）\ndef compute_prime(n: int) -> list[int]:\n    primes = []\n    for num in range(2, n):\n        if all(num % i != 0 for i in range(2, int(num**0.5) + 1)):\n            primes.append(num)\n    return primes\n\nwith ProcessPoolExecutor() as pool:\n    results = pool.map(compute_prime, [10000, 20000, 30000])\n    for result in results:\n        print(f'Found {len(result)} primes')"]},

    {"title": "文件 I/O 与序列化", "topic": "python", "difficulty": 2, "irt_b_param": 0.2,
     "description": "pathlib 路径操作、文件读写模式、上下文管理器确保资源释放、json/pickle/msgpack 序列化、CSV/Excel 处理、流式读写。生产级文件操作需关注编码一致性、大文件流式处理、原子写入和临时文件管理。",
     "learning_objectives": ["掌握 pathlib 路径操作", "理解文件读写模式与编码", "学会 json/pickle 序列化与安全", "掌握流式读写与原子写入", "理解临时文件管理"],
     "code_examples": ["import json\nimport tempfile\nfrom pathlib import Path\n\n# pathlib — 生产级路径操作\nbase = Path('/data')\nconfig_path = base / 'config' / 'app.json'\nconfig_path.parent.mkdir(parents=True, exist_ok=True)\n\n# 原子写入 — 避免写入中断导致数据损坏\ndef atomic_write(path: Path, data: str) -> None:\n    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False, suffix='.tmp') as f:\n        f.write(data)\n        f.flush()\n        temp_path = Path(f.name)\n    temp_path.replace(path)  # 原子操作\n\n# JSON 序列化 — 生产级注意\ndata = {'name': 'Alice', 'scores': [95, 87, 92], 'active': True}\njson_str = json.dumps(data, ensure_ascii=False, indent=2)  # 中文不转义\n\n# 安全警告：永远不要 pickle 不受信任的数据\n# import pickle  # 不安全！可能执行任意代码\n# 使用 json 或 msgpack 替代"]},

    {"title": "测试策略与质量保障", "topic": "python", "difficulty": 3, "irt_b_param": 0.8,
     "description": "pytest 测试框架：参数化测试、fixture 系统(conftest.py)、mock/patch、覆盖率分析(cov)、集成测试与端到端测试。生产级测试遵循测试金字塔（70%单元/20%集成/10%端到端），CI 中强制覆盖率门槛。理解测试隔离、测试数据管理和快照测试。",
     "learning_objectives": ["掌握 pytest fixture 与参数化", "学会 mock/patch 隔离外部依赖", "理解测试金字塔与覆盖率策略", "配置 CI 测试流水线", "掌握 conftest.py 与测试隔离"],
     "code_examples": ["import pytest\nfrom unittest.mock import AsyncMock, patch\n\n# conftest.py — 共享 fixture\n@pytest.fixture\ndef db_session():\n    session = create_test_session()\n    yield session\n    session.close()\n\n# 参数化测试\n@pytest.mark.parametrize('input_val,expected', [\n    (0, 0), (1, 1), (5, 120), (-1, None),\n])\ndef test_factorial(input_val, expected):\n    assert factorial(input_val) == expected\n\n# Mock 外部依赖 — 隔离网络调用\n@pytest.mark.asyncio\nasync def test_fetch_user():\n    with patch('myapp.api.get_user') as mock_get:\n        mock_get.return_value = AsyncMock(return_value={'id': 1, 'name': 'Alice'})\n        result = await fetch_user(1)\n        assert result['name'] == 'Alice'\n        mock_get.assert_called_once_with(1)"]},

    {"title": "设计模式与架构原则", "topic": "python", "difficulty": 4, "irt_b_param": 1.5,
     "description": "SOLID 原则在 Python 中的实践：依赖注入、策略模式、观察者模式、工厂模式、单例模式。Pythonic 实现方式：使用函数/闭包替代类、描述符实现属性代理、元类实现类注册。架构层面关注六边形架构、整洁架构和依赖方向。",
     "learning_objectives": ["理解 SOLID 原则及 Pythonic 实现", "掌握依赖注入与控制反转", "学会策略模式与观察者模式", "理解六边形架构与依赖方向", "掌握 Pythonic 设计模式实现"],
     "code_examples": ["from dataclasses import dataclass\nfrom typing import Protocol\n\n# 依赖注入 + 策略模式 — 生产级解耦\nclass NotificationSender(Protocol):\n    async def send(self, recipient: str, message: str) -> bool: ...\n\nclass EmailSender:\n    async def send(self, recipient: str, message: str) -> bool:\n        print(f'Email to {recipient}: {message}')\n        return True\n\nclass SmsSender:\n    async def send(self, recipient: str, message: str) -> bool:\n        print(f'SMS to {recipient}: {message}')\n        return True\n\n@dataclass\nclass NotificationService:\n    sender: NotificationSender\n\n    async def notify(self, user_id: str, event: str) -> bool:\n        return await self.sender.send(user_id, f'Event: {event}')\n\nemail_service = NotificationService(sender=EmailSender())\nsms_service = NotificationService(sender=SmsSender())"]},

    {"title": "部署与容器化", "topic": "python", "difficulty": 4, "irt_b_param": 1.8,
     "description": "Docker 容器化最佳实践：多阶段构建、最小基础镜像、非 root 用户运行、健康检查。CI/CD 流水线(GitHub Actions/GitLab CI)：自动化测试、镜像构建与推送、蓝绿/金丝雀部署。生产级部署需关注配置管理(环境变量/配置中心)、密钥管理和滚动更新。",
     "learning_objectives": ["掌握 Docker 多阶段构建与最小镜像", "理解 CI/CD 流水线设计", "学会蓝绿部署与金丝雀发布", "掌握配置管理与密钥安全", "理解健康检查与滚动更新"],
     "code_examples": ["# Dockerfile — 多阶段构建\n# FROM python:3.12-slim AS builder\n# WORKDIR /app\n# COPY requirements.txt .\n# RUN pip install --no-cache-dir -r requirements.txt\n#\n# FROM python:3.12-slim\n# RUN useradd -m appuser\n# WORKDIR /app\n# COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages\n# COPY --from=builder /usr/local/bin /usr/local/bin\n# COPY . .\n# USER appuser\n# HEALTHCHECK --interval=30s CMD python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\"\n# EXPOSE 8000\n# CMD [\"uvicorn\", \"app.main:app\", \"--host\", \"0.0.0.0\", \"--workers\", \"4\"]\n\n# GitHub Actions CI\n# name: CI\n# on: [push, pull_request]\n# jobs:\n#   test:\n#     runs-on: ubuntu-latest\n#     steps:\n#       - uses: actions/checkout@v4\n#       - uses: actions/setup-python@v5\n#         with: { python-version: '3.12' }\n#       - run: pip install -r requirements.txt\n#       - run: pytest --cov=app --cov-fail-under=80"]},
]

JAVASCRIPT_KPS = [
    {"title": "变量声明与类型系统", "topic": "javascript", "difficulty": 1, "irt_b_param": -2.0,
     "description": "let/const/var 的本质区别：变量提升(hoisting)、暂时性死区(TDZ)、块级作用域。JavaScript 动态类型与隐式转换陷阱、严格模式、原始类型与引用类型。生产代码必须使用 const 优先、let 次之、禁止 var。理解 V8 引擎对 let/const 的优化。",
     "learning_objectives": ["理解 var/let/const 的作用域与提升差异", "掌握原始类型与引用类型的本质区别", "理解隐式类型转换与严格相等", "学会严格模式与最佳实践"],
     "code_examples": ["// const 优先，let 次之，禁止 var\nconst API_URL = 'https://api.example.com';\nlet currentPage = 1;\n\n// 原始类型 vs 引用类型\nconst a = 'hello';    // 原始类型，不可变\nconst b = [1, 2, 3];  // 引用类型，可变\nconst c = [...b];     // 浅拷贝\n\n// 隐式转换陷阱 — 生产代码必须理解\nconsole.log('5' + 3);    // '53' 字符串拼接\nconsole.log('5' - 3);    // 2  数值减法\nconsole.log(true + 1);   // 2\nconsole.log(null == undefined);  // true\nconsole.log(null === undefined); // false — 始终用 ==="]},

    {"title": "函数与闭包", "topic": "javascript", "difficulty": 2, "irt_b_param": -0.5,
     "description": "函数是一等公民：函数声明/表达式/箭头函数、词法作用域与闭包、this 绑定规则(默认/隐式/显式/new)、call/apply/bind。闭包是 JavaScript 最强大的特性，也是最常见的陷阱来源。理解闭包在模块模式和私有状态中的应用。",
     "learning_objectives": ["理解词法作用域与闭包机制", "掌握 this 的四种绑定规则", "区分箭头函数与普通函数的 this", "学会闭包的实际应用模式"],
     "code_examples": ["// 闭包：私有状态 — 模块模式基础\nfunction createCounter(initial = 0) {\n  let count = initial;\n  return {\n    increment: () => ++count,\n    decrement: () => --count,\n    value: () => count,\n    reset: () => { count = initial; return count; },\n  };\n}\n\nconst counter = createCounter(10);\nconsole.log(counter.increment()); // 11\nconsole.log(counter.value());     // 11\n\n// this 绑定 — 生产级代码必须理解\nconst user = {\n  name: 'Alice',\n  greet() { return `Hello, ${this.name}`; },\n  greetLater() {\n    setTimeout(() => console.log(this.greet()), 1000);\n  },\n};"]},

    {"title": "原型与继承", "topic": "javascript", "difficulty": 3, "irt_b_param": 0.5,
     "description": "原型链是 JavaScript 继承的核心：__proto__ 与 prototype、Object.create、class 语法糖、super 调用链、new 操作符执行过程、私有字段(#field)。理解原型链才能写出高性能、可维护的面向对象代码。",
     "learning_objectives": ["理解原型链查找机制", "掌握 Object.create 与原型继承", "理解 class 语法糖的本质", "学会组合继承与私有字段"],
     "code_examples": ["// class 语法糖 + 私有字段 — 生产级模式\nclass EventEmitter {\n  #listeners = new Map();\n\n  on(event, callback) {\n    if (!this.#listeners.has(event)) this.#listeners.set(event, []);\n    this.#listeners.get(event).push(callback);\n    return () => this.off(event, callback);\n  }\n\n  off(event, callback) {\n    const cbs = this.#listeners.get(event);\n    if (cbs) this.#listeners.set(event, cbs.filter(cb => cb !== callback));\n  }\n\n  emit(event, ...args) {\n    (this.#listeners.get(event) ?? []).forEach(cb => cb(...args));\n  }\n}\n\nconst bus = new EventEmitter();\nconst unsub = bus.on('data', (d) => console.log('Received:', d));\nbus.emit('data', { id: 1 });\nunsub();"]},

    {"title": "Promise 与异步编程", "topic": "javascript", "difficulty": 2, "irt_b_param": 0.0,
     "description": "Promise 链式调用、async/await 语法、错误处理策略、Promise.all/race/allSettled/any、微任务与宏任务队列。生产级异步代码必须处理超时、取消(AbortController)、并发限制和错误边界。",
     "learning_objectives": ["理解 Promise 状态机与链式调用", "掌握 async/await 与错误处理", "理解事件循环与微任务/宏任务", "学会并发控制与超时处理"],
     "code_examples": ["// 并发控制 + 超时 + 错误处理 — 生产级模式\nasync function fetchWithTimeout(url, timeoutMs = 5000) {\n  const controller = new AbortController();\n  const timeout = setTimeout(() => controller.abort(), timeoutMs);\n  try {\n    const resp = await fetch(url, { signal: controller.signal });\n    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);\n    return await resp.json();\n  } finally {\n    clearTimeout(timeout);\n  }\n}\n\nasync function fetchAll(urls, concurrency = 5) {\n  const results = [];\n  for (let i = 0; i < urls.length; i += concurrency) {\n    const batch = urls.slice(i, i + concurrency);\n    const batchResults = await Promise.allSettled(batch.map(url => fetchWithTimeout(url)));\n    results.push(...batchResults);\n  }\n  return results;\n}"]},

    {"title": "ES Modules 与模块系统", "topic": "javascript", "difficulty": 2, "irt_b_param": -0.3,
     "description": "ESM(import/export)与 CommonJS(require/module.exports)的区别、静态分析与动态导入、Tree Shaking 原理、模块解析策略、包管理(npm/pnpm)。生产级项目必须使用 ESM，配合 Tree Shaking 优化包体积。理解 package.json 的 exports 字段。",
     "learning_objectives": ["理解 ESM 与 CJS 的本质区别", "掌握静态导入与动态导入", "理解 Tree Shaking 原理与副作用标记", "学会包管理与依赖策略"],
     "code_examples": ["// ESM — 静态导入（编译时分析，支持 Tree Shaking）\nimport { Router } from 'express';\nimport type { Request, Response } from 'express';\n\nexport function validateInput(schema) {\n  return (req, res, next) => {\n    const { error } = schema.validate(req.body);\n    if (error) return res.status(400).json({ error: error.message });\n    next();\n  };\n}\n\nexport default class App {\n  #router = new Router();\n  use(middleware) { this.#router.use(middleware); return this; }\n}\n\n// 动态导入（运行时加载，代码分割）\nasync function loadPlugin(name) {\n  const { default: plugin } = await import(`./plugins/${name}.js`);\n  return plugin;\n}"]},

    {"title": "高阶函数与函数式编程", "topic": "javascript", "difficulty": 2, "irt_b_param": 0.3,
     "description": "函数组合与柯里化、map/filter/reduce/reduceRight、纯函数与副作用隔离、不可变数据实践(immer/structuredClone)、函子(Functor)与单子(Monad)概念。生产级代码应优先使用函数式风格处理数据转换，减少可变状态。",
     "learning_objectives": ["掌握 map/filter/reduce 高阶组合", "理解纯函数与引用透明性", "学会柯里化与函数组合", "了解不可变数据实践"],
     "code_examples": ["// 函数组合管道 — 生产级数据处理\nconst pipe = (...fns) => (x) => fns.reduce((v, f) => f(v), x);\n\nconst normalize = (s) => s.trim().toLowerCase();\nconst splitWords = (s) => s.split(/\\s+/);\nconst removeStopWords = (words) => words.filter(w => !['the', 'a', 'is'].includes(w));\nconst countFreq = (words) => words.reduce((acc, w) => ({ ...acc, [w]: (acc[w] || 0) + 1 }), {});\n\nconst analyzeText = pipe(normalize, splitWords, removeStopWords, countFreq);\nconst result = analyzeText('The quick brown fox is a quick animal');\n\n// 不可变数据更新（structuredClone — 浏览器原生深拷贝）\nconst state = { users: [{ id: 1, name: 'Alice' }] };\nconst nextState = structuredClone(state);\nnextState.users[0].name = 'Bob';\n// state 不受影响"]},

    {"title": "事件循环与并发模型", "topic": "javascript", "difficulty": 3, "irt_b_param": 1.0,
     "description": "JavaScript 单线程并发模型：调用栈与执行上下文、微任务队列(Promise/MutationObserver)、宏任务队列(setTimeout/I/O)、requestAnimationFrame、requestIdleCallback。理解事件循环是写出高性能异步代码的前提，也是排查异步 Bug 的关键。",
     "learning_objectives": ["理解调用栈与任务队列机制", "区分微任务与宏任务执行顺序", "掌握 requestAnimationFrame 调度", "学会使用 requestIdleCallback"],
     "code_examples": ["// 事件循环执行顺序 — 面试必考，生产必懂\nconsole.log('1: sync');\nsetTimeout(() => console.log('2: macro'), 0);\nPromise.resolve()\n  .then(() => console.log('3: micro 1'))\n  .then(() => console.log('4: micro 2'));\nqueueMicrotask(() => console.log('5: explicit micro'));\nconsole.log('6: sync');\n// 输出顺序: 1, 6, 3, 5, 4, 2\n\n// requestAnimationFrame — 动画帧同步\nlet lastTime = 0;\nfunction animate(timestamp) {\n  const delta = timestamp - lastTime;\n  lastTime = timestamp;\n  requestAnimationFrame(animate);\n}\nrequestAnimationFrame(animate);"]},

    {"title": "TypeScript 类型系统", "topic": "javascript", "difficulty": 3, "irt_b_param": 0.8,
     "description": "TypeScript 是 JavaScript 的超集：接口与类型别名、泛型与条件类型、映射类型与模板字面量类型、类型守卫与窄化、声明文件与模块增强。生产级项目必须使用 TypeScript 严格模式，理解类型编程的高级技巧。",
     "learning_objectives": ["掌握接口、类型别名与泛型", "理解条件类型与映射类型", "学会类型守卫与可辨识联合", "配置 tsconfig 严格模式"],
     "code_examples": ["// 泛型 + 条件类型 — 生产级类型编程\ntype ApiResponse<T> = T extends Array<infer U>\n  ? { data: U[]; total: number }\n  : { data: T };\n\n// 可辨识联合 — 安全的状态机\ntype Result<T> =\n  | { status: 'success'; data: T }\n  | { status: 'error'; error: { code: string; message: string } }\n  | { status: 'loading' };\n\nfunction handleResult<T>(result: Result<T>) {\n  switch (result.status) {\n    case 'success': return result.data;\n    case 'error': throw new Error(result.error.message);\n    case 'loading': return null;\n  }\n}\n\n// 映射类型\ntype Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;\ntype User = { id: number; name: string; email: string };\ntype UserUpdate = Optional<User, 'id'>;"]},

    {"title": "DOM 操作与事件系统", "topic": "javascript", "difficulty": 2, "irt_b_param": -0.2,
     "description": "DOM 树结构与节点操作、事件捕获/冒泡/委托、自定义事件(CustomEvent)、MutationObserver、IntersectionObserver。生产级 DOM 操作必须使用事件委托、批量更新(DocumentFragment)、虚拟滚动等性能优化策略。",
     "learning_objectives": ["理解 DOM 树与节点操作 API", "掌握事件冒泡与委托模式", "学会 CustomEvent 自定义通信", "理解 Observer 模式应用"],
     "code_examples": ["// 事件委托 — 高效处理大量元素\ndocument.querySelector('.list').addEventListener('click', (e) => {\n  const item = e.target.closest('[data-id]');\n  if (!item) return;\n  console.log('Selected:', item.dataset.id);\n});\n\n// IntersectionObserver — 懒加载\nconst observer = new IntersectionObserver((entries) => {\n  entries.forEach(entry => {\n    if (entry.isIntersecting) {\n      entry.target.src = entry.target.dataset.src;\n      observer.unobserve(entry.target);\n    }\n  });\n}, { rootMargin: '200px' });\n\ndocument.querySelectorAll('img[data-src]').forEach(img => observer.observe(img));"]},

    {"title": "Node.js 运行时与模块", "topic": "javascript", "difficulty": 3, "irt_b_param": 0.5,
     "description": "Node.js 运行时架构：V8 引擎 + libuv 事件循环、Buffer 与 Stream 流处理、EventEmitter、process 对象、Cluster 多进程、Worker Threads。生产级 Node.js 需理解事件循环阶段(timers/poll/check)、流式处理和进程管理。",
     "learning_objectives": ["理解 Node.js 事件循环阶段", "掌握 Stream 流式处理", "学会 Cluster 多进程模型", "理解 Worker Threads 并行计算"],
     "code_examples": ["import { Readable, Transform, Writable } from 'stream';\nimport { Cluster } from 'cluster';\n\n// Stream 管道 — 处理大文件不爆内存\nconst upperCase = new Transform({\n  transform(chunk, encoding, callback) {\n    callback(null, chunk.toString().toUpperCase());\n  },\n});\nprocess.stdin.pipe(upperCase).pipe(process.stdout);\n\n// Cluster — 充分利用多核 CPU\nif (Cluster.isPrimary) {\n  const cpuCount = 4;\n  for (let i = 0; i < cpuCount; i++) Cluster.fork();\n  Cluster.on('exit', (worker) => {\n    console.log(`Worker ${worker.process.pid} died, restarting...`);\n    Cluster.fork();\n  });\n} else {\n  // http.createServer(app).listen(3000);\n}"]},

    {"title": "安全编程", "topic": "javascript", "difficulty": 3, "irt_b_param": 1.0,
     "description": "Web 安全核心：XSS 攻击与防护(DOMPurify/CSP)、CSRF 攻击与防护(SameSite Cookie/Token)、CORS 配置策略、内容安全策略(CSP)、输入验证与输出编码、Subresource Integrity(SRI)。生产级前端必须实施纵深安全防御。",
     "learning_objectives": ["理解 XSS 攻击类型与防护策略", "掌握 CSRF 防护与 SameSite Cookie", "学会 CORS 安全配置", "理解 CSP 内容安全策略", "掌握输入验证与输出编码"],
     "code_examples": ["// XSS 防护 — 永远不要直接插入用户内容\n// 错误: element.innerHTML = userInput;\n// 正确: element.textContent = userInput;\n\nimport DOMPurify from 'dompurify';\nconst clean = DOMPurify.sanitize(userInput);\n\n// CSRF Token 模式\nasync function fetchWithCSRF(url, options = {}) {\n  const csrfToken = document.querySelector('meta[name=\"csrf-token\"]')?.content;\n  return fetch(url, {\n    ...options,\n    headers: { ...options.headers, 'X-CSRF-Token': csrfToken },\n    credentials: 'same-origin',\n  });\n}\n\n// SRI — 防止 CDN 篡改\n// <script src=\"https://cdn.example.com/lib.js\"\n//   integrity=\"sha384-abc123...\" crossorigin=\"anonymous\"></script>"]},

    {"title": "构建工具与工程化", "topic": "javascript", "difficulty": 3, "irt_b_param": 0.7,
     "description": "现代前端构建工具链：Vite(开发服务器+Rollup构建)、esbuild(SWC)、Tree Shaking 与 Code Splitting、Source Map、环境变量管理、Monorepo 管理(turborepo/nx)。生产级工程化需理解构建优化、依赖预构建和部署策略。",
     "learning_objectives": ["掌握 Vite 配置与插件开发", "理解 Tree Shaking 与 Code Splitting", "学会环境变量与多环境配置", "理解 Monorepo 管理策略"],
     "code_examples": ["// vite.config.ts — 生产级配置\nimport { defineConfig } from 'vite';\nimport react from '@vitejs/plugin-react';\n\nexport default defineConfig(({ mode }) => ({\n  plugins: [react()],\n  build: {\n    rollupOptions: {\n      output: {\n        manualChunks: {\n          vendor: ['react', 'react-dom'],\n          router: ['react-router-dom'],\n        },\n      },\n    },\n    sourcemap: mode === 'development',\n    minify: 'esbuild',\n    target: 'es2020',\n  },\n  define: {\n    'process.env.API_URL': JSON.stringify(process.env.VITE_API_URL),\n  },\n}));"]},

    {"title": "测试策略", "topic": "javascript", "difficulty": 3, "irt_b_param": 0.9,
     "description": "JavaScript 测试体系：Vitest/Jest 单元测试、React Testing Library 组件测试、Playwright/Cypress 端到端测试、Mock/Stub/Spy 策略、覆盖率与 CI 集成。生产级测试遵循测试金字塔，关注用户行为而非实现细节。",
     "learning_objectives": ["掌握 Vitest/Jest 单元测试", "学会 Mock/Stub/Spy 隔离策略", "理解测试金字塔与覆盖率", "掌握 Playwright E2E 测试"],
     "code_examples": ["// Vitest 单元测试\nimport { describe, it, expect, vi } from 'vitest';\nimport { fetchUser } from './api';\n\ndescribe('fetchUser', () => {\n  it('returns user data on success', async () => {\n    vi.spyOn(global, 'fetch').mockResolvedValue({\n      ok: true,\n      json: () => Promise.resolve({ id: 1, name: 'Alice' }),\n    });\n    const user = await fetchUser(1);\n    expect(user).toEqual({ id: 1, name: 'Alice' });\n  });\n\n  it('throws on network error', async () => {\n    vi.spyOn(global, 'fetch').mockRejectedValue(new Error('Network error'));\n    await expect(fetchUser(1)).rejects.toThrow('Network error');\n  });\n});"]},

    {"title": "性能优化与内存管理", "topic": "javascript", "difficulty": 4, "irt_b_param": 1.5,
     "description": "V8 引擎优化：隐藏类与内联缓存、GC 机制(新生代/老生代)、内存泄漏检测(Chrome DevTools Heap Snapshot)、性能分析(Performance API)、Web Worker 并行计算。生产级应用必须建立性能监控与告警体系。",
     "learning_objectives": ["理解 V8 隐藏类与内联缓存机制", "掌握内存泄漏排查方法", "学会 Performance API 性能分析", "了解 Web Worker 并行计算"],
     "code_examples": ["// Performance API — 自定义性能指标\nconst perf = {\n  start(label) { performance.mark(`${label}-start`); },\n  end(label) {\n    performance.mark(`${label}-end`);\n    performance.measure(label, `${label}-start`, `${label}-end`);\n    const [measure] = performance.getEntriesByName(label);\n    console.log(`${label}: ${measure.duration.toFixed(2)}ms`);\n    return measure.duration;\n  },\n};\n\nperf.start('process');\nperf.end('process');\n\n// Web Worker — 并行计算\nconst worker = new Worker('worker.js');\nworker.postMessage({ type: 'compute', data: largeArray });\nworker.onmessage = (e) => console.log('Result:', e.data);"]},

    {"title": "设计模式与架构", "topic": "javascript", "difficulty": 4, "irt_b_param": 1.8,
     "description": "JavaScript 常用设计模式：发布/订阅、观察者、中介者、代理(Proxy/Reflect)、装饰器、策略模式。架构模式：MVC/MVP/MVVM、Flux/Redux 单向数据流、CQRS、六边形架构。生产级前端架构关注可测试性、可扩展性和关注点分离。",
     "learning_objectives": ["掌握 Proxy/Reflect 元编程", "理解发布/订阅与观察者区别", "学会策略模式与中介者模式", "理解 Flux 单向数据流架构"],
     "code_examples": ["// Proxy — 响应式数据绑定（Vue 3 原理）\nfunction reactive(target, onChange) {\n  return new Proxy(target, {\n    set(obj, prop, value) {\n      const old = obj[prop];\n      obj[prop] = value;\n      if (old !== value) onChange(prop, value, old);\n      return true;\n    },\n  });\n}\n\nconst state = reactive({ count: 0 }, (prop, val, old) => {\n  console.log(`${prop}: ${old} => ${val}`);\n});\nstate.count++;\n\n// 发布/订阅模式 — 事件总线\nclass EventBus {\n  #handlers = new Map();\n  on(event, handler) {\n    this.#handlers.set(event, [...(this.#handlers.get(event) ?? []), handler]);\n  }\n  emit(event, data) {\n    (this.#handlers.get(event) ?? []).forEach(h => h(data));\n  }\n  off(event, handler) {\n    const cbs = this.#handlers.get(event) ?? [];\n    this.#handlers.set(event, cbs.filter(h => h !== handler));\n  }\n}"]},
]

RUST_KPS = [
    {"title": "变量、可变性与基本类型", "topic": "rust", "difficulty": 1, "irt_b_param": -2.0,
     "description": "Rust 的变量默认不可变(let)、mut 关键字、遮蔽(shadowing)、基本类型(i32/u64/f64/bool/char/str)、类型推断与显式标注。理解不可变默认是 Rust 安全保障的基石，与 C/C++ 的可变默认形成鲜明对比。",
     "learning_objectives": ["理解不可变默认的设计哲学", "区分 mut 与 shadowing 的语义", "掌握基本类型与类型推断", "理解栈分配与堆分配的区别"],
     "code_examples": ["fn main() {\n    let x = 5;           // 不可变\n    let mut y = 10;      // 可变\n    y += 1;\n\n    // shadowing — 类型可变\n    let spaces = \"   \";\n    let spaces = spaces.len();  // 从 &str 变为 usize\n\n    // 类型标注\n    let guess: u32 = \"42\".parse().expect(\"Not a number\");\n    let f = 3.14_f64;\n\n    println!(\"x={}, y={}, spaces={}, guess={}\", x, y, spaces, guess);\n}"]},

    {"title": "所有权与移动语义", "topic": "rust", "difficulty": 3, "irt_b_param": 1.0,
     "description": "所有权是 Rust 最核心的概念：每个值有唯一所有者、所有者离开作用域值被丢弃(drop)、赋值/传参发生移动(move)而非拷贝。理解所有权是理解 Rust 全部安全保证的基础，也是 Rust 零成本抽象的根基。",
     "learning_objectives": ["理解所有权三规则", "区分移动(move)与克隆(clone)", "理解 Copy trait 的语义", "掌握所有权的函数传递"],
     "code_examples": ["fn main() {\n    let s1 = String::from(\"hello\");\n    let s2 = s1;          // 移动\n    // println!(\"{}\", s1); // 编译错误：s1 已失效\n    println!(\"{}\", s2);    // OK\n\n    let s3 = s2.clone();  // 深拷贝\n    println!(\"{} {}\", s2, s3);\n\n    let x = 5;\n    let y = x;            // i32 实现了 Copy\n    println!(\"{} {}\", x, y);\n}\n\nfn take_ownership(s: String) {\n    println!(\"Got: {}\", s);\n}  // s 被 drop"]},

    {"title": "引用与借用", "topic": "rust", "difficulty": 3, "irt_b_param": 1.2,
     "description": "借用规则：同一时刻只能有一个可变引用或多个不可变引用、引用必须始终有效(非悬垂)。生命周期标注确保引用安全。理解借用检查器是写出 Rust 代码的关键，也是 Rust 内存安全保证的核心机制。",
     "learning_objectives": ["掌握不可变引用与可变引用规则", "理解借用检查器的工作原理", "学会生命周期标注基础", "理解悬垂引用的预防"],
     "code_examples": ["fn main() {\n    let mut s = String::from(\"hello\");\n    let r1 = &s;\n    let r2 = &s;\n    println!(\"{} {}\", r1, r2);  // 多个不可变引用 OK\n\n    let r3 = &mut s;\n    r3.push_str(\" world\");\n    println!(\"{}\", r3);  // 可变引用独占\n}\n\nfn calculate_length(s: &String) -> usize {\n    s.len()\n}  // 引用，不获取所有权\n\nfn append_world(s: &mut String) {\n    s.push_str(\" world\");\n}"]},

    {"title": "结构体与枚举", "topic": "rust", "difficulty": 2, "irt_b_param": 0.0,
     "description": "结构体(命名字段/元组结构体/单元结构体)、枚举(变体/带数据枚举)、Option 替代 null、Result 替代异常、模式匹配(match/if let/let else)。Rust 的代数数据类型是类型安全的基石，Option/Result 是零成本抽象的典范。",
     "learning_objectives": ["掌握三种结构体定义方式", "理解枚举与代数数据类型", "熟练使用 Option 和 Result", "掌握 match 与 if let 模式匹配"],
     "code_examples": ["#[derive(Debug)]\nstruct User {\n    name: String,\n    age: u32,\n    email: Option<String>,\n}\n\nenum Command {\n    Quit,\n    Move { x: i32, y: i32 },\n    Write(String),\n    ChangeColor(u8, u8, u8),\n}\n\nfn process(cmd: Command) -> Result<String, String> {\n    match cmd {\n        Command::Quit => Ok(\"Bye!\".into()),\n        Command::Move { x, y } => Ok(format!(\"Moving to ({}, {})\", x, y)),\n        Command::Write(text) => Ok(format!(\"Writing: {}\", text)),\n        Command::ChangeColor(..) => Err(\"Color not supported\".into()),\n    }\n}\n\n// let-else (Rust 1.65+)\nfn greet(user: &User) {\n    let Some(email) = &user.email else {\n        println!(\"No email for {}\", user.name);\n        return;\n    };\n    println!(\"Email: {}\", email);\n}"]},

    {"title": "错误处理与 ? 运算符", "topic": "rust", "difficulty": 2, "irt_b_param": 0.5,
     "description": "Rust 没有异常，使用 Result<T, E> 和 Option<T> 处理错误。? 运算符自动传播错误、thiserror/anyhow 错误类型库、自定义错误类型。生产级 Rust 代码必须建立统一的错误类型体系和错误转换链。",
     "learning_objectives": ["掌握 Result 和 Option 的组合", "理解 ? 运算符的传播机制", "学会自定义错误类型", "掌握 thiserror/anyhow 库"],
     "code_examples": ["use std::fs;\nuse std::io;\n\n#[derive(Debug, thiserror::Error)]\nenum AppError {\n    #[error(\"IO error: {0}\")]\n    Io(#[from] io::Error),\n    #[error(\"Parse error: {0}\")]\n    Parse(#[from] std::num::ParseIntError),\n    #[error(\"Not found: {0}\")]\n    NotFound(String),\n}\n\nfn read_config(path: &str) -> Result<Config, AppError> {\n    let content = fs::read_to_string(path)?;\n    let port: u16 = content.trim().parse()?;\n    Ok(Config { port })\n}\n\nstruct Config { port: u16 }"]},

    {"title": "Trait 与泛型", "topic": "rust", "difficulty": 3, "irt_b_param": 1.0,
     "description": "Trait 是 Rust 的接口抽象：trait 定义与实现、默认方法、关联类型、trait bounds、泛型约束、impl Trait 语法、trait 对象动态分发(vtable)。理解 trait 是理解 Rust 类型系统的核心，也是零成本抽象的关键。",
     "learning_objectives": ["掌握 trait 定义与实现规则", "理解 trait bounds 与泛型约束", "区分静态分发与动态分发", "学会关联类型与默认方法"],
     "code_examples": ["trait Summary {\n    fn summarize_author(&self) -> String;\n    fn summarize(&self) -> String {\n        format!(\"(Read more from {}...)\", self.summarize_author())\n    }\n}\n\nstruct Article { title: String, author: String }\n\nimpl Summary for Article {\n    fn summarize_author(&self) -> String { self.author.clone() }\n    fn summarize(&self) -> String { format!(\"{} by {}\", self.title, self.author) }\n}\n\n// 静态分发 — 零开销\nfn notify<T: Summary>(item: &T) {\n    println!(\"Breaking news! {}\", item.summarize());\n}\n\n// 动态分发 — 运行时 vtable\nfn notify_dyn(item: &dyn Summary) {\n    println!(\"{}\", item.summarize());\n}"]},

    {"title": "集合与迭代器", "topic": "rust", "difficulty": 2, "irt_b_param": 0.3,
     "description": "Vec<T> 动态数组、HashMap<K,V> 哈希表、HashSet<T> 集合、迭代器(Iterator trait)与适配器(map/filter/collect/take/skip)、消费者(for_each/fold/count)。Rust 迭代器是零成本抽象，编译后与手写循环性能相同。",
     "learning_objectives": ["掌握 Vec/HashMap/HashSet 常用操作", "理解迭代器协议(Iterator trait)", "掌握迭代器适配器链式调用", "理解迭代器的零成本抽象"],
     "code_examples": ["use std::collections::HashMap;\n\nfn main() {\n    let words = vec![\"hello\", \"world\", \"hello\", \"rust\"];\n\n    let word_count: HashMap<&str, usize> = words\n        .iter()\n        .fold(HashMap::new(), |mut acc, &word| {\n            *acc.entry(word).or_insert(0) += 1;\n            acc\n        });\n\n    let lengths: Vec<usize> = words.iter().map(|w| w.len()).collect();\n    let total: usize = words.iter().map(|w| w.len()).sum();\n}"]},

    {"title": "生命周期", "topic": "rust", "difficulty": 4, "irt_b_param": 1.8,
     "description": "生命周期确保引用始终有效：生命周期标注语法('a)、函数签名中的生命周期、结构体中的生命周期引用、生命周期省略规则、静态生命周期('static)、生命周期子类型与协变/逆变。这是 Rust 最独特也最困难的概念。",
     "learning_objectives": ["理解生命周期的本质与标注语法", "掌握三大省略规则", "学会结构体中的生命周期标注", "理解 'static 与生命周期子类型"],
     "code_examples": ["struct Parser<'a> {\n    input: &'a str,\n    pos: usize,\n}\n\nimpl<'a> Parser<'a> {\n    fn new(input: &'a str) -> Self {\n        Parser { input, pos: 0 }\n    }\n\n    fn peek(&self) -> Option<char> {\n        self.input.chars().nth(self.pos)\n    }\n\n    fn advance(&mut self) -> Option<char> {\n        let ch = self.peek();\n        if ch.is_some() { self.pos += 1; }\n        ch\n    }\n}\n\nfn first_word(s: &str) -> &str {\n    match s.find(' ') {\n        Some(i) => &s[..i],\n        None => s,\n    }\n}"]},

    {"title": "并发与线程安全", "topic": "rust", "difficulty": 4, "irt_b_param": 2.0,
     "description": "Rust 的并发安全由类型系统保证：Send/Sync trait、std::thread、Mutex/RwLock、Arc 原子引用计数、Channel 通道(mpsc)、async/await 异步运行时。Rust 的无畏并发(Fearless Concurrency)是零成本抽象的典范。",
     "learning_objectives": ["理解 Send/Sync 与线程安全", "掌握 Mutex/RwLock + Arc 模式", "学会 Channel 通道通信", "了解 async/await 异步并发"],
     "code_examples": ["use std::sync::{Arc, Mutex};\nuse std::thread;\n\nfn main() {\n    let counter = Arc::new(Mutex::new(0));\n    let mut handles = vec![];\n\n    for _ in 0..10 {\n        let counter = Arc::clone(&counter);\n        let handle = thread::spawn(move || {\n            let mut num = counter.lock().unwrap();\n            *num += 1;\n        });\n        handles.push(handle);\n    }\n\n    for handle in handles { handle.join().unwrap(); }\n    println!(\"Result: {}\", *counter.lock().unwrap());  // 10\n}\n\nuse std::sync::mpsc;\nlet (tx, rx) = mpsc::channel();\nthread::spawn(move || { tx.send(42).unwrap(); });\nprintln!(\"Got: {}\", rx.recv().unwrap());"]},

    {"title": "智能指针与内存管理", "topic": "rust", "difficulty": 3, "irt_b_param": 1.3,
     "description": "Box<T> 堆分配、Rc<T> 引用计数、Arc<T> 原子引用计数、RefCell<T> 内部可变性、Cow<T> 写时克隆、Deref/Drop trait。理解智能指针是理解 Rust 内存管理的关键，也是所有权系统的延伸。",
     "learning_objectives": ["掌握 Box/Rc/Arc 的适用场景", "理解 RefCell 内部可变性", "学会 Deref 强制转换", "理解 Drop trait 与资源释放"],
     "code_examples": ["use std::rc::Rc;\nuse std::cell::RefCell;\n\n#[derive(Debug)]\nstruct Node {\n    value: i32,\n    children: RefCell<Vec<Rc<Node>>>,\n}\n\nfn main() {\n    let leaf = Rc::new(Node { value: 3, children: RefCell::new(vec![]) });\n    let branch = Rc::new(Node {\n        value: 5,\n        children: RefCell::new(vec![Rc::clone(&leaf)]),\n    });\n    println!(\"branch children: {:?}\", branch.children.borrow());\n}"]},

    {"title": "异步运行时 (tokio)", "topic": "rust", "difficulty": 4, "irt_b_param": 2.0,
     "description": "tokio 是 Rust 最主流的异步运行时：#[tokio::main]、任务调度(tokio::spawn)、异步 IO(tcp/udp/fs)、Channel(tokio::sync)、定时器、Select/join。生产级异步 Rust 需理解运行时配置、任务取消和背压控制。",
     "learning_objectives": ["掌握 tokio 基本用法与任务调度", "理解异步 IO 与同步 IO 的区别", "学会 tokio Channel 通信", "掌握 Select/join 并发控制"],
     "code_examples": ["use tokio::sync::mpsc;\nuse tokio::time::{sleep, Duration};\n\n#[tokio::main]\nasync fn main() {\n    let (tx, mut rx) = mpsc::channel(100);\n\n    tokio::spawn(async move {\n        for i in 0..10 {\n            tx.send(i).await.unwrap();\n            sleep(Duration::from_millis(100)).await;\n        }\n    });\n\n    while let Some(value) = rx.recv().await {\n        println!(\"Received: {}\", value);\n    }\n}"]},

    {"title": "测试与基准测试", "topic": "rust", "difficulty": 2, "irt_b_param": 0.6,
     "description": "Rust 内置测试框架：#[test] 属性、#[should_panic] 预期失败、assert!/assert_eq!/assert_ne!、集成测试(tests/)、文档测试(doc tests)、基准测试(criterion)。生产级 Rust 项目必须有完善的测试覆盖和性能回归检测。",
     "learning_objectives": ["掌握单元测试与集成测试", "学会 #[should_panic] 和 Result 测试", "理解文档测试与示例验证", "掌握 criterion 基准测试"],
     "code_examples": ["#[cfg(test)]\nmod tests {\n    use super::*;\n\n    #[test]\n    fn test_add() {\n        assert_eq!(2 + 2, 4);\n    }\n\n    #[test]\n    #[should_panic(expected = \"overflow\")]\n    fn test_overflow() {\n        panic!(\"overflow\");\n    }\n\n    #[test]\n    fn test_result() -> Result<(), Box<dyn std::error::Error>> {\n        let val: i32 = \"42\".parse()?;\n        assert_eq!(val, 42);\n        Ok(())\n    }\n}"]},

    {"title": "Web 开发 (Axum)", "topic": "rust", "difficulty": 4, "irt_b_param": 1.8,
     "description": "Axum 是 Tokio 团队开发的 Web 框架：路由与处理器、提取器(Extractor)、中间件(Tower)、状态共享、错误处理。生产级 Rust Web 服务需理解 Tower Service 中间件栈、优雅关闭和请求追踪。",
     "learning_objectives": ["掌握 Axum 路由与处理器", "理解 Extractor 提取器模式", "学会 Tower 中间件组合", "掌握状态共享与错误处理"],
     "code_examples": ["use axum::{Router, routing::{get, post}, extract::{State, Path}, Json, http::StatusCode};\nuse serde::{Deserialize, Serialize};\n\n#[derive(Serialize)]\nstruct User { id: u64, name: String }\n\n#[derive(Deserialize)]\nstruct CreateUser { name: String }\n\nasync fn create_user(Json(data): Json<CreateUser>) -> (StatusCode, Json<User>) {\n    (StatusCode::CREATED, Json(User { id: 1, name: data.name }))\n}\n\nasync fn get_user(Path(id): Path<u64>) -> Json<User> {\n    Json(User { id, name: \"Alice\".into() })\n}\n\nlet app = Router::new()\n    .route(\"/users\", get(list_users).post(create_user))\n    .route(\"/users/:id\", get(get_user));"]},

    {"title": "宏与元编程", "topic": "rust", "difficulty": 4, "irt_b_param": 2.2,
     "description": "声明宏(macro_rules!)与过程宏(derive/attribute/function-like)、宏卫生性、Token 流处理、quote!/syn/proc-macro2 库。宏是 Rust 元编程的核心，用于消除重复代码和实现编译时检查。理解宏与泛型的选择策略。",
     "learning_objectives": ["掌握 macro_rules! 声明宏", "理解过程宏的三种类型", "学会 syn/quote 解析与生成代码", "理解宏卫生性与递归宏"],
     "code_examples": ["macro_rules! vec_of {\n    ($($x:expr),*) => {{\n        let mut temp_vec = Vec::new();\n        $(temp_vec.push($x);)*\n        temp_vec\n    }};\n}\n\nlet nums = vec_of![1, 2, 3, 4, 5];\n\n// derive 过程宏\n// #[derive(Debug, Clone, Serialize)]\n// struct User { name: String, age: u32 }\n\n// 属性宏\n// #[route(GET, \"/api/users\")]\n// async fn list_users() -> Json<Vec<User>> { ... }"]},
]

REACT_KPS = [
    {"title": "JSX 与元素渲染", "topic": "react", "difficulty": 1, "irt_b_param": -2.0,
     "description": "JSX 是 React.createElement 的语法糖：编译原理、表达式嵌入、条件渲染模式、列表渲染与 key、React 元素的不可变性。理解 JSX 本质是理解 React 渲染模型的基础，也是调试 React 应用的关键。",
     "learning_objectives": ["理解 JSX 编译为 createElement 调用", "掌握条件渲染的三种模式", "理解列表渲染中 key 的作用", "区分 React 元素与组件实例"],
     "code_examples": ["const element = <h1>Hello</h1>;\n// 等价于: React.createElement('h1', null, 'Hello')\n\nfunction Greeting({ isLoggedIn, user }) {\n  return (\n    <div>\n      {isLoggedIn ? <Welcome user={user} /> : <LoginForm />}\n      {user.isAdmin && <AdminPanel />}\n    </div>\n  );\n}\n\nfunction UserList({ users }) {\n  return (\n    <ul>\n      {users.map(user => (\n        <li key={user.id}>{user.name}</li>\n      ))}\n    </ul>\n  );\n}"]},

    {"title": "组件与 Props 设计", "topic": "react", "difficulty": 1, "irt_b_param": -1.5,
     "description": "函数组件是 React 的基本单元：Props 单向数据流、children 与组合模式、Props 解构与默认值、TypeScript 类型约束。生产级组件设计遵循单一职责、受控边界、稳定接口和可组合性。",
     "learning_objectives": ["理解 Props 单向数据流原则", "掌握 children 与组合模式", "学会 TypeScript Props 类型定义", "理解组件设计原则"],
     "code_examples": ["import { ReactNode } from 'react';\n\ntype CardProps = {\n  title: string;\n  subtitle?: string;\n  children: ReactNode;\n  variant?: 'default' | 'outlined';\n  onClick?: () => void;\n};\n\nfunction Card({ title, subtitle, children, variant = 'default', onClick }: CardProps) {\n  const className = variant === 'outlined' ? 'card outlined' : 'card';\n  return (\n    <div className={className} onClick={onClick}>\n      <h3>{title}</h3>\n      {subtitle && <p className=\"subtitle\">{subtitle}</p>}\n      <div className=\"content\">{children}</div>\n    </div>\n  );\n}"]},

    {"title": "useState 与状态管理", "topic": "react", "difficulty": 2, "irt_b_param": -0.5,
     "description": "useState 是最基础的 Hook：状态更新机制(React 18 自动批量更新)、函数式更新、不可变更新模式、状态提升、派生状态 vs 源状态。生产级状态管理需区分 UI 状态与服务端状态，避免状态冗余。",
     "learning_objectives": ["理解 React 批量更新机制", "掌握函数式更新避免闭包陷阱", "学会不可变更新模式", "理解状态提升与派生状态"],
     "code_examples": ["import { useState } from 'react';\n\nfunction TodoApp() {\n  const [todos, setTodos] = useState<{ id: number; text: string; done: boolean }[]>([]);\n  const [input, setInput] = useState('');\n\n  const addTodo = () => {\n    if (!input.trim()) return;\n    setTodos(prev => [...prev, { id: Date.now(), text: input, done: false }]);\n    setInput('');\n  };\n\n  const toggleTodo = (id: number) => {\n    setTodos(prev => prev.map(t => t.id === id ? { ...t, done: !t.done } : t));\n  };\n\n  const remaining = todos.filter(t => !t.done).length;\n  return <div><input value={input} onChange={e => setInput(e.target.value)} /><span>{remaining} items left</span></div>;\n}"]},

    {"title": "useEffect 与副作用", "topic": "react", "difficulty": 2, "irt_b_param": 0.0,
     "description": "useEffect 处理副作用：依赖数组语义、清理函数、竞态条件处理(AbortController)、自定义 Hook 抽取。React 18 Strict Mode 双重调用。生产级 useEffect 必须处理竞态、取消和清理，避免内存泄漏。",
     "learning_objectives": ["理解依赖数组的比较语义", "掌握清理函数与资源释放", "学会处理竞态条件(AbortController)", "理解 Strict Mode 双重调用"],
     "code_examples": ["import { useState, useEffect } from 'react';\n\nfunction UserProfile({ userId }: { userId: number }) {\n  const [user, setUser] = useState<User | null>(null);\n  const [error, setError] = useState<string | null>(null);\n\n  useEffect(() => {\n    const controller = new AbortController();\n    setError(null);\n    async function fetchUser() {\n      try {\n        const resp = await fetch(`/api/users/${userId}`, { signal: controller.signal });\n        if (!resp.ok) throw new Error('Failed');\n        const data = await resp.json();\n        if (!controller.signal.aborted) setUser(data);\n      } catch (e) {\n        if (e instanceof DOMException && e.name === 'AbortError') return;\n        setError(e instanceof Error ? e.message : 'Unknown error');\n      }\n    }\n    fetchUser();\n    return () => controller.abort();\n  }, [userId]);\n\n  if (error) return <div>Error: {error}</div>;\n  if (!user) return <div>Loading...</div>;\n  return <div>{user.name} ({user.email})</div>;\n}"]},

    {"title": "useRef 与 DOM 操作", "topic": "react", "difficulty": 2, "irt_b_param": 0.3,
     "description": "useRef 的两种用途：持久化可变值(不触发重渲染)、访问 DOM 元素。forwardRef 与 useImperativeHandle、ref callback 模式。生产级代码优先使用受控组件，ref 仅用于非受控场景。",
     "learning_objectives": ["区分 useRef 与 useState 的使用场景", "掌握 DOM 引用与命令式操作", "学会 forwardRef 与 useImperativeHandle", "理解 ref callback 模式"],
     "code_examples": ["import { useRef, useEffect, forwardRef, useImperativeHandle } from 'react';\n\nfunction AutoFocusInput() {\n  const inputRef = useRef<HTMLInputElement>(null);\n  useEffect(() => { inputRef.current?.focus(); }, []);\n  return <input ref={inputRef} placeholder=\"Auto focused\" />;\n}\n\ntype TextInputHandle = { focus: () => void; clear: () => void };\nconst TextInput = forwardRef<TextInputHandle, { value: string; onChange: (v: string) => void }>(\n  ({ value, onChange }, ref) => {\n    const inputRef = useRef<HTMLInputElement>(null);\n    useImperativeHandle(ref, () => ({ focus: () => inputRef.current?.focus(), clear: () => onChange('') }));\n    return <input ref={inputRef} value={value} onChange={e => onChange(e.target.value)} />;\n  }\n);"]},

    {"title": "Context 与依赖注入", "topic": "react", "difficulty": 2, "irt_b_param": 0.5,
     "description": "Context API 实现跨组件数据传递：创建与使用 Context、Provider 嵌套与覆盖、useContext Hook、Context 性能优化(split contexts)、自定义 Provider 模式。Context 适用于主题、认证、国际化等全局状态。",
     "learning_objectives": ["理解 Context 的适用场景与限制", "掌握 Provider 嵌套与默认值", "学会拆分 Context 优化性能", "理解自定义 Provider 模式"],
     "code_examples": ["import { createContext, useContext, useState, type ReactNode } from 'react';\n\ntype AuthState = { user: User | null; token: string | null };\ntype AuthActions = { login: (email: string, password: string) => Promise<void>; logout: () => void };\n\nconst AuthStateContext = createContext<AuthState>({ user: null, token: null });\nconst AuthActionsContext = createContext<AuthActions>(null!);\n\nfunction AuthProvider({ children }: { children: ReactNode }) {\n  const [state, setState] = useState<AuthState>({ user: null, token: null });\n  const actions: AuthActions = {\n    login: async (email, password) => { /* fetch API */ },\n    logout: () => setState({ user: null, token: null }),\n  };\n  return (\n    <AuthActionsContext.Provider value={actions}>\n      <AuthStateContext.Provider value={state}>{children}</AuthStateContext.Provider>\n    </AuthActionsContext.Provider>\n  );\n}\n\nconst useAuthState = () => useContext(AuthStateContext);\nconst useAuthActions = () => useContext(AuthActionsContext);"]},

    {"title": "表单处理与验证", "topic": "react", "difficulty": 2, "irt_b_param": 0.4,
     "description": "受控组件与非受控组件、react-hook-form 高性能表单管理、zod/yup Schema 验证、表单状态管理、动态表单与数组字段。生产级表单必须处理验证、错误提示、提交状态和防重复提交。",
     "learning_objectives": ["掌握受控组件与非受控组件", "学会 react-hook-form + zod 验证", "理解表单状态管理策略", "掌握防重复提交与加载状态"],
     "code_examples": ["import { useForm } from 'react-hook-form';\nimport { zodResolver } from '@hookform/resolvers/zod';\nimport { z } from 'zod';\n\nconst schema = z.object({\n  email: z.string().email('Invalid email'),\n  password: z.string().min(8, 'At least 8 characters'),\n  confirmPassword: z.string(),\n}).refine(data => data.password === data.confirmPassword, {\n  message: 'Passwords do not match', path: ['confirmPassword'],\n});\n\ntype FormData = z.infer<typeof schema>;\n\nfunction LoginForm() {\n  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({\n    resolver: zodResolver(schema),\n  });\n  const onSubmit = async (data: FormData) => { /* API call */ };\n  return (\n    <form onSubmit={handleSubmit(onSubmit)}>\n      <input {...register('email')} />\n      {errors.email && <span>{errors.email.message}</span>}\n      <button disabled={isSubmitting}>{isSubmitting ? 'Logging in...' : 'Login'}</button>\n    </form>\n  );\n}"]},

    {"title": "数据获取模式", "topic": "react", "difficulty": 3, "irt_b_param": 0.9,
     "description": "现代 React 数据获取策略：TanStack Query(React Query)/SWR、缓存与失效策略、乐观更新、无限滚动与分页、预加载与后台刷新。生产级数据获取必须处理缓存、竞态、重试和离线状态。",
     "learning_objectives": ["掌握 TanStack Query 核心概念", "理解缓存与失效策略", "学会乐观更新与预加载", "掌握无限滚动与分页"],
     "code_examples": ["import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';\n\nfunction useUser(id: string) {\n  return useQuery({\n    queryKey: ['users', id],\n    queryFn: () => fetch(`/api/users/${id}`).then(r => r.json()),\n    staleTime: 5 * 60 * 1000,\n    retry: 3,\n  });\n}\n\nfunction useUpdateUser() {\n  const queryClient = useQueryClient();\n  return useMutation({\n    mutationFn: (data: UpdateUserDTO) => fetch('/api/users', { method: 'PUT', body: JSON.stringify(data) }),\n    onSuccess: (_, variables) => {\n      queryClient.invalidateQueries({ queryKey: ['users', variables.id] });\n    },\n  });\n}"]},

    {"title": "错误边界与异常处理", "topic": "react", "difficulty": 3, "irt_b_param": 0.7,
     "description": "React 错误边界(ErrorBoundary)捕获渲染错误、组件级降级策略、全局错误处理(window.onerror/unhandledrejection)、错误上报(Sentry)。生产级 React 应用必须有完善的错误边界和降级策略。",
     "learning_objectives": ["掌握 ErrorBoundary 类组件实现", "学会组件级降级策略", "理解全局错误处理与上报", "掌握 Sentry 错误监控集成"],
     "code_examples": ["import { Component, type ReactNode, type ErrorInfo } from 'react';\n\ntype Props = { children: ReactNode; fallback?: ReactNode };\ntype State = { hasError: boolean; error: Error | null };\n\nclass ErrorBoundary extends Component<Props, State> {\n  state: State = { hasError: false, error: null };\n  static getDerivedStateFromError(error: Error): State {\n    return { hasError: true, error };\n  }\n  componentDidCatch(error: Error, info: ErrorInfo) {\n    console.error('ErrorBoundary caught:', error, info.componentStack);\n  }\n  render() {\n    if (this.state.hasError) {\n      return this.props.fallback ?? (\n        <div role=\"alert\">\n          <h2>Something went wrong</h2>\n          <button onClick={() => this.setState({ hasError: false, error: null })}>Try again</button>\n        </div>\n      );\n    }\n    return this.props.children;\n  }\n}"]},

    {"title": "useMemo 与 useCallback", "topic": "react", "difficulty": 3, "irt_b_param": 0.8,
     "description": "性能优化 Hooks：useMemo 缓存计算结果、useCallback 缓存函数引用、React.memo 组件记忆化。过度使用反而降低性能，需遵循测量优先原则。React DevTools Profiler 是性能优化的必备工具。",
     "learning_objectives": ["理解 useMemo/useCallback 的缓存机制", "掌握 React.memo 组件记忆化", "学会识别不必要的重渲染", "遵循测量优先的优化原则"],
     "code_examples": ["import { useMemo, useCallback, memo } from 'react';\n\nfunction SearchResults({ items, query }: { items: Item[]; query: string }) {\n  const filtered = useMemo(\n    () => items.filter(item => item.name.toLowerCase().includes(query.toLowerCase())),\n    [items, query]\n  );\n  return <List items={filtered} />;\n}\n\nconst ExpensiveItem = memo(({ item, onSelect }: { item: Item; onSelect: (id: string) => void }) => (\n  <div onClick={() => onSelect(item.id)}>{item.name}</div>\n));\n\nfunction ItemList({ items }: { items: Item[] }) {\n  const handleSelect = useCallback((id: string) => { console.log('Selected:', id); }, []);\n  return items.map(item => <ExpensiveItem key={item.id} item={item} onSelect={handleSelect} />);\n}"]},

    {"title": "自定义 Hook 设计", "topic": "react", "difficulty": 3, "irt_b_param": 1.0,
     "description": "自定义 Hook 是 React 代码复用的核心机制：命名规范(use前缀)、组合模式、返回值设计、Hook 规则(只在顶层调用)、可测试性。生产级自定义 Hook 应提供清晰的 API 和完善的类型。",
     "learning_objectives": ["掌握自定义 Hook 设计模式", "理解 Hook 规则与 ESLint 插件", "学会返回值设计策略", "理解 Hook 的可测试性"],
     "code_examples": ["import { useState, useEffect, useCallback } from 'react';\n\ntype AsyncState<T> = { data: T | null; error: Error | null; loading: boolean };\n\nfunction useAsync<T>(asyncFn: () => Promise<T>, deps: unknown[] = []) {\n  const [state, setState] = useState<AsyncState<T>>({ data: null, error: null, loading: true });\n  const execute = useCallback(async () => {\n    setState(prev => ({ ...prev, loading: true, error: null }));\n    try {\n      const data = await asyncFn();\n      setState({ data, error: null, loading: false });\n    } catch (error) {\n      setState({ data: null, error: error instanceof Error ? error : new Error(String(error)), loading: false });\n    }\n  }, deps);\n  useEffect(() => { execute(); }, [execute]);\n  return { ...state, refetch: execute };\n}"]},

    {"title": "状态管理进阶", "topic": "react", "difficulty": 3, "irt_b_param": 1.1,
     "description": "React 状态管理方案对比：Zustand(极简全局状态)、Jotai(原子化状态)、Redux Toolkit(大型应用)。选择策略：小型用 Context+useReducer，中型用 Zustand，大型用 Redux Toolkit。理解状态分类(UI状态/服务端状态/URL状态)。",
     "learning_objectives": ["掌握 Zustand 全局状态管理", "理解 Jotai 原子化状态", "学会状态管理方案选择策略", "理解状态分类与管理原则"],
     "code_examples": ["import { create } from 'zustand';\nimport { devtools, persist } from 'zustand/middleware';\n\ntype CartItem = { id: string; name: string; price: number; quantity: number };\ntype CartStore = {\n  items: CartItem[];\n  addItem: (item: Omit<CartItem, 'quantity'>) => void;\n  removeItem: (id: string) => void;\n  total: () => number;\n};\n\nconst useCartStore = create<CartStore>()(\n  devtools(persist((set, get) => ({\n    items: [],\n    addItem: (item) => set((state) => {\n      const existing = state.items.find(i => i.id === item.id);\n      if (existing) return { items: state.items.map(i => i.id === item.id ? { ...i, quantity: i.quantity + 1 } : i) };\n      return { items: [...state.items, { ...item, quantity: 1 }] };\n    }),\n    removeItem: (id) => set((state) => ({ items: state.items.filter(i => i.id !== id) })),\n    total: () => get().items.reduce((sum, i) => sum + i.price * i.quantity, 0),\n  }), { name: 'cart-storage' }))\n);"]},

    {"title": "React 性能优化", "topic": "react", "difficulty": 4, "irt_b_param": 1.5,
     "description": "React 渲染性能优化：虚拟化列表(react-window/tanstack-virtual)、代码分割(React.lazy/Suspense)、并发特性(useTransition/useDeferredValue)、服务端渲染(SSR)与流式渲染。性能优化必须基于 Profiler 测量数据。",
     "learning_objectives": ["掌握虚拟化列表技术", "学会代码分割与懒加载", "理解 useTransition/useDeferredValue", "了解 SSR 与流式渲染"],
     "code_examples": ["import { lazy, Suspense, useTransition, useState } from 'react';\n\nconst HeavyChart = lazy(() => import('./HeavyChart'));\n\nfunction Dashboard() {\n  const [isPending, startTransition] = useTransition();\n  const [tab, setTab] = useState<'overview' | 'analytics'>('overview');\n  return (\n    <div>\n      <nav>\n        <button onClick={() => startTransition(() => setTab('overview'))}>Overview</button>\n        <button onClick={() => startTransition(() => setTab('analytics'))}>Analytics</button>\n      </nav>\n      {isPending && <Spinner />}\n      <Suspense fallback={<Spinner />}>\n        {tab === 'analytics' && <HeavyChart />}\n      </Suspense>\n    </div>\n  );\n}"]},

    {"title": "无障碍访问 (a11y)", "topic": "react", "difficulty": 2, "irt_b_param": 0.6,
     "description": "Web 无障碍访问(WCAG 2.1)：语义化 HTML、ARIA 属性、键盘导航、焦点管理、屏幕阅读器兼容、颜色对比度。生产级 React 应用必须满足 WCAG 2.1 AA 标准，使用 eslint-plugin-jsx-a11y 进行静态检查。",
     "learning_objectives": ["理解 WCAG 2.1 核心原则", "掌握 ARIA 属性与语义化 HTML", "学会键盘导航与焦点管理", "配置 eslint-plugin-jsx-a11y"],
     "code_examples": ["function Modal({ isOpen, onClose, title, children }: ModalProps) {\n  const closeRef = useRef<HTMLButtonElement>(null);\n  useEffect(() => { if (isOpen) closeRef.current?.focus(); }, [isOpen]);\n  useEffect(() => {\n    const handleEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };\n    if (isOpen) document.addEventListener('keydown', handleEsc);\n    return () => document.removeEventListener('keydown', handleEsc);\n  }, [isOpen, onClose]);\n  if (!isOpen) return null;\n  return (\n    <div role=\"dialog\" aria-modal=\"true\" aria-labelledby=\"modal-title\">\n      <h2 id=\"modal-title\">{title}</h2>\n      <button ref={closeRef} onClick={onClose} aria-label=\"Close dialog\">&times;</button>\n      {children}\n    </div>\n  );\n}"]},

    {"title": "测试策略", "topic": "react", "difficulty": 3, "irt_b_param": 1.2,
     "description": "React 测试体系：Jest + React Testing Library、组件测试(渲染/交互/异步)、自定义 Hook 测试(renderHook)、端到端测试(Playwright)、测试覆盖率策略。测试应关注用户行为而非实现细节。",
     "learning_objectives": ["掌握 RTL 组件测试模式", "学会测试异步行为与用户交互", "理解测试用户行为而非实现", "配置 CI 测试流水线"],
     "code_examples": ["import { render, screen, waitFor } from '@testing-library/react';\nimport userEvent from '@testing-library/user-event';\n\ndescribe('LoginForm', () => {\n  it('submits credentials and shows success', async () => {\n    const onSuccess = jest.fn();\n    render(<LoginForm onSuccess={onSuccess} />);\n    const user = userEvent.setup();\n    await user.type(screen.getByLabelText(/email/i), 'alice@example.com');\n    await user.type(screen.getByLabelText(/password/i), 'secret123');\n    await user.click(screen.getByRole('button', { name: /sign in/i }));\n    await waitFor(() => {\n      expect(onSuccess).toHaveBeenCalledWith({ email: 'alice@example.com' });\n    });\n  });\n});"]},
]

VUE_KPS = [
    {"title": "模板语法与指令", "topic": "vue", "difficulty": 1, "irt_b_param": -2.0,
     "description": "Vue 模板语法：插值表达式、v-bind/v-on/v-model/v-if/v-show/v-for/v-slot 指令、修饰符系统、动态参数。理解指令是声明式渲染的核心，也是 Vue 与 React JSX 的根本区别。",
     "learning_objectives": ["掌握插值与指令完整语法", "理解 v-if 与 v-show 的区别", "掌握 v-for 与 key 的使用", "学会修饰符与动态参数"],
     "code_examples": ["const app = createApp({\n  setup() {\n    const message = ref('Hello Vue!');\n    const isShown = ref(true);\n    const items = ref([{ id: 1, text: 'Learn Vue' }, { id: 2, text: 'Build App' }]);\n    return { message, isShown, items };\n  },\n  template: `\n    <div>\n      <h1>{{ message }}</h1>\n      <input v-model=\"message\" placeholder=\"Edit me\" />\n      <button @click=\"isShown = !isShown\">Toggle</button>\n      <p v-show=\"isShown\">Conditional content</p>\n      <ul><li v-for=\"item in items\" :key=\"item.id\">{{ item.text }}</li></ul>\n    </div>\n  `\n}).mount('#app');"]},

    {"title": "响应式系统：ref 与 reactive", "topic": "vue", "difficulty": 2, "irt_b_param": -0.5,
     "description": "Vue 3 响应式系统基于 Proxy：ref 用于基本类型、reactive 用于对象、toRefs/toRef 解构、shallowRef/shallowReactive 浅层响应、computed 计算属性。理解 Proxy 响应式原理是写出高效 Vue 代码的关键。",
     "learning_objectives": ["理解 Proxy 响应式原理", "区分 ref 与 reactive 的使用场景", "掌握 computed 缓存机制", "理解 shallow 响应式的性能优化"],
     "code_examples": ["import { ref, reactive, computed, toRefs } from 'vue';\n\nconst app = createApp({\n  setup() {\n    const count = ref(0);\n    const state = reactive({ firstName: 'Alice', lastName: 'Smith' });\n    const fullName = computed(() => `${state.firstName} ${state.lastName}`);\n    function increment() { count.value++; }\n    return { count, ...toRefs(state), fullName, increment };\n  },\n  template: `<div><p>{{ count }} x 2 = {{ count * 2 }}</p><p>Name: {{ fullName }}</p><button @click=\"increment\">+1</button></div>`\n}).mount('#app');"]},

    {"title": "组合式 API 与 setup", "topic": "vue", "difficulty": 2, "irt_b_param": 0.0,
     "description": "Composition API 是 Vue 3 的核心：setup 函数生命周期、composable 函数抽取、provide/inject 依赖注入、生命周期钩子(onMounted/onUnmounted/onWatch)。组合式 API 解决了 Options API 的逻辑分散问题。",
     "learning_objectives": ["理解 setup 函数与生命周期", "掌握 composable 函数设计", "学会 provide/inject 依赖注入", "理解生命周期钩子的使用"],
     "code_examples": ["import { ref, onMounted, onUnmounted } from 'vue';\n\nfunction useMousePosition() {\n  const x = ref(0);\n  const y = ref(0);\n  function update(event) { x.value = event.clientX; y.value = event.clientY; }\n  onMounted(() => window.addEventListener('mousemove', update));\n  onUnmounted(() => window.removeEventListener('mousemove', update));\n  return { x, y };\n}\n\nconst app = createApp({\n  setup() { const { x, y } = useMousePosition(); return { x, y }; },\n  template: '<p>Mouse: {{ x }}, {{ y }}</p>'\n}).mount('#app');"]},

    {"title": "组件通信模式", "topic": "vue", "difficulty": 2, "irt_b_param": 0.5,
     "description": "Vue 组件通信：Props/emit 单向数据流、v-model 双向绑定、provide/inject 跨层级、事件总线(mitt)、Pinia 状态管理。生产级应用需根据通信距离选择合适的模式。",
     "learning_objectives": ["掌握 Props/emit 单向数据流", "理解 v-model 双向绑定原理", "学会 provide/inject 跨层级通信", "了解 Pinia 状态管理"],
     "code_examples": ["const Child = {\n  props: { modelValue: String },\n  emits: ['update:modelValue'],\n  setup(props, { emit }) {\n    const onInput = (e) => emit('update:modelValue', e.target.value);\n    return { onInput };\n  },\n  template: '<input :value=\"modelValue\" @input=\"onInput\" />'\n};\n\nconst Parent = {\n  setup() { const name = ref('Alice'); return { name }; },\n  template: '<Child v-model=\"name\" /><p>{{ name }}</p>'\n};\n\ncreateApp(Parent).component('Child', Child).mount('#app');"]},

    {"title": "侦听器与副作用", "topic": "vue", "difficulty": 2, "irt_b_param": 0.3,
     "description": "watch/watchEffect 侦听器：watch 精确侦听、watchEffect 自动追踪、深度侦听、立即执行(flush/immediate)、停止侦听、副作用清理(onCleanup)。生产级代码必须处理侦听器的清理和竞态。",
     "learning_objectives": ["区分 watch 与 watchEffect", "掌握深度侦听与立即执行", "学会侦听器清理与竞态处理", "理解 flush 时机(post/pre/sync)"],
     "code_examples": ["import { ref, watch } from 'vue';\n\nfunction useSearch(query) {\n  const results = ref([]);\n  const loading = ref(false);\n  const error = ref(null);\n\n  const stop = watch(query, async (newQuery, oldQuery, onCleanup) => {\n    if (!newQuery.trim()) { results.value = []; return; }\n    const controller = new AbortController();\n    onCleanup(() => controller.abort());\n    loading.value = true;\n    try {\n      const resp = await fetch(`/api/search?q=${encodeURIComponent(newQuery)}`, { signal: controller.signal });\n      results.value = await resp.json();\n    } catch (e) {\n      if (e.name !== 'AbortError') error.value = e.message;\n    } finally { loading.value = false; }\n  }, { immediate: true });\n\n  return { results, loading, error, stop };\n}"]},

    {"title": "Pinia 状态管理", "topic": "vue", "difficulty": 3, "irt_b_param": 1.0,
     "description": "Pinia 是 Vue 官方状态管理库：defineStore(Setup/Option 语法)、StoreToRefs 解构、插件系统(持久化/日志)、SSR 支持、DevTools 集成。生产级状态管理需区分全局状态与局部状态。",
     "learning_objectives": ["掌握 defineStore 两种语法", "理解 StoreToRefs 响应式解构", "学会 Pinia 插件开发", "理解状态管理最佳实践"],
     "code_examples": ["import { defineStore } from 'pinia';\n\nexport const useAuthStore = defineStore('auth', () => {\n  const user = ref(null);\n  const token = ref(null);\n  const isAuthenticated = computed(() => !!token.value);\n  async function login(email: string, password: string) {\n    const resp = await fetch('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });\n    const data = await resp.json();\n    user.value = data.user; token.value = data.token;\n  }\n  function logout() { user.value = null; token.value = null; }\n  return { user, token, isAuthenticated, login, logout };\n});"]},

    {"title": "路由与导航守卫", "topic": "vue", "difficulty": 3, "irt_b_param": 0.8,
     "description": "Vue Router 4：路由配置(动态/嵌套/命名)、导航守卫(beforeEach/beforeResolve/afterEach)、路由懒加载、数据获取策略、滚动行为。生产级路由需处理认证守卫、权限控制和加载状态。",
     "learning_objectives": ["掌握路由配置与动态路由", "理解导航守卫执行顺序", "学会路由懒加载与代码分割", "掌握认证守卫与权限控制"],
     "code_examples": ["import { createRouter, createWebHistory } from 'vue-router';\n\nconst routes = [\n  { path: '/', component: () => import('./views/Home.vue') },\n  { path: '/login', component: () => import('./views/Login.vue'), meta: { guest: true } },\n  { path: '/dashboard', component: () => import('./views/Dashboard.vue'), meta: { requiresAuth: true },\n    children: [\n      { path: 'profile', component: () => import('./views/Profile.vue') },\n      { path: 'settings', component: () => import('./views/Settings.vue') },\n    ],\n  },\n];\n\nconst router = createRouter({ history: createWebHistory(), routes });\nrouter.beforeEach((to) => {\n  const auth = useAuthStore();\n  if (to.meta.requiresAuth && !auth.isAuthenticated) return '/login';\n  if (to.meta.guest && auth.isAuthenticated) return '/dashboard';\n});"]},

    {"title": "组件设计模式", "topic": "vue", "difficulty": 3, "irt_b_param": 1.2,
     "description": "高级组件模式：无渲染组件(Renderless Components)、作用域插槽、动态组件与 keep-alive、Teleport 传送门、Suspense 异步组件。理解这些模式是构建复杂 Vue 应用的关键。",
     "learning_objectives": ["掌握无渲染组件模式", "理解作用域插槽与数据传递", "学会动态组件与 keep-alive", "掌握 Teleport 与 Suspense"],
     "code_examples": ["const MouseTracker = {\n  setup(_, { slots }) {\n    const x = ref(0); const y = ref(0);\n    onMounted(() => {\n      const handler = (e) => { x.value = e.clientX; y.value = e.clientY; };\n      window.addEventListener('mousemove', handler);\n      onUnmounted(() => window.removeEventListener('mousemove', handler));\n    });\n    return () => slots.default?.({ x: x.value, y: y.value });\n  },\n};\n// <MouseTracker v-slot=\"{ x, y }\"><p>Position: {{ x }}, {{ y }}</p></MouseTracker>\n// <Teleport to=\"body\"><div class=\"modal\">Modal content</div></Teleport>"]},

    {"title": "TypeScript 集成", "topic": "vue", "difficulty": 3, "irt_b_param": 1.0,
     "description": "Vue 3 完整 TypeScript 支持：defineComponent/defineProps/defineEmits、类型标注 Props/emit/Ref、泛型组件、类型工具(ExtractPropTypes/ComponentInstance)。生产级 Vue 项目必须使用 TypeScript。",
     "learning_objectives": ["掌握 defineProps/defineEmits 类型标注", "学会泛型组件定义", "理解 Vue 类型工具函数", "配置 Volar 严格类型检查"],
     "code_examples": ["import { defineComponent, type PropType } from 'vue';\n\ntype Status = 'idle' | 'loading' | 'success' | 'error';\n\nexport default defineComponent({\n  props: {\n    items: { type: Array as PropType<string[]>, required: true },\n    status: { type: String as PropType<Status>, default: 'idle' },\n  },\n  emits: { select: (index: number) => typeof index === 'number' },\n  setup(props, { emit }) {\n    const selectedIndex = ref<number | null>(null);\n    function handleSelect(index: number) { selectedIndex.value = index; emit('select', index); }\n    return { selectedIndex, handleSelect };\n  },\n});"]},

    {"title": "表单验证", "topic": "vue", "difficulty": 2, "irt_b_param": 0.4,
     "description": "Vue 表单验证方案：VeeValidate + zod/yup Schema 验证、自定义验证规则、异步验证、表单状态管理。生产级表单验证需处理实时验证、提交验证和服务器端验证的协调。",
     "learning_objectives": ["掌握 VeeValidate + zod 验证", "学会自定义验证规则", "理解实时验证与提交验证策略", "掌握服务器端验证协调"],
     "code_examples": ["import { useForm, Field, ErrorMessage } from 'vee-validate';\nimport { toTypedSchema } from '@vee-validate/zod';\nimport { z } from 'zod';\n\nconst schema = z.object({\n  email: z.string().email('Invalid email'),\n  password: z.string().min(8, 'At least 8 characters'),\n});\n\nconst { handleSubmit, errors, isSubmitting } = useForm({\n  validationSchema: toTypedSchema(schema),\n});\n\nconst onSubmit = handleSubmit(async (values) => {\n  await fetch('/api/auth/login', { method: 'POST', body: JSON.stringify(values) });\n});"]},

    {"title": "国际化 (vue-i18n)", "topic": "vue", "difficulty": 2, "irt_b_param": 0.5,
     "description": "vue-i18n 国际化方案：消息格式化、复数处理、日期/数字本地化、懒加载语言包、运行时切换语言。生产级国际化需考虑翻译工作流、缺失翻译处理和 SEO 多语言策略。",
     "learning_objectives": ["掌握 vue-i18n 基本配置与使用", "理解复数与日期本地化", "学会懒加载语言包", "理解翻译工作流与缺失处理"],
     "code_examples": ["import { createI18n } from 'vue-i18n';\n\nconst messages = {\n  en: { welcome: 'Welcome, {name}!', items: 'No items | One item | {count} items' },\n  zh: { welcome: '欢迎，{name}！', items: '没有项目 | 一个项目 | {count} 个项目' },\n};\n\nconst i18n = createI18n({ legacy: false, locale: 'zh', fallbackLocale: 'en', messages });\n// {{ $t('welcome', { name: 'Alice' }) }}\n// {{ $tc('items', count, { count }) }}"]},

    {"title": "测试策略", "topic": "vue", "difficulty": 3, "irt_b_param": 0.9,
     "description": "Vue 测试体系：Vitest 单元测试、Vue Test Utils 组件挂载与交互、Pinia store 测试、路由测试、E2E 测试(Playwright)。生产级测试需关注组件行为、用户交互和集成测试。",
     "learning_objectives": ["掌握 Vitest + Vue Test Utils", "学会 Pinia store 测试", "理解组件测试最佳实践", "掌握 Playwright E2E 测试"],
     "code_examples": ["import { describe, it, expect } from 'vitest';\nimport { mount } from '@vue/test-utils';\nimport { createPinia, setActivePinia } from 'pinia';\nimport LoginForm from './LoginForm.vue';\n\ndescribe('LoginForm', () => {\n  it('submits form with valid data', async () => {\n    setActivePinia(createPinia());\n    const wrapper = mount(LoginForm);\n    await wrapper.find('input[type=\"email\"]').setValue('alice@example.com');\n    await wrapper.find('form').trigger('submit.prevent');\n    expect(wrapper.emitted('submit')).toHaveLength(1);\n  });\n});"]},

    {"title": "SSR 与 Nuxt.js", "topic": "vue", "difficulty": 4, "irt_b_param": 1.5,
     "description": "服务端渲染(SSR)原理与 Nuxt.js 框架：SSR vs CSR vs SSG vs ISR 渲染模式、Nuxt 3 自动路由、数据获取(useFetch/useAsyncData)、SEO 优化、混合渲染。生产级 SSR 需关注 hydration 和状态序列化。",
     "learning_objectives": ["理解 SSR/CSR/SSG/ISR 渲染模式", "掌握 Nuxt 3 核心概念", "学会 useFetch/useAsyncData 数据获取", "理解 hydration 与状态序列化"],
     "code_examples": ["// Nuxt 3 页面\n// pages/users/[id].vue\n<script setup>\nconst route = useRoute();\nconst { data: user, pending, error } = await useFetch(`/api/users/${route.params.id}`);\nuseHead({ title: () => user.value?.name ?? 'Loading...' });\n</script>\n// <template>\n//   <div v-if=\"pending\">Loading...</div>\n//   <div v-else-if=\"error\">Error: {{ error.message }}</div>\n//   <div v-else><h1>{{ user.name }}</h1><p>{{ user.email }}</p></div>\n// </template>"]},

    {"title": "性能优化与最佳实践", "topic": "vue", "difficulty": 4, "irt_b_param": 1.5,
     "description": "Vue 性能优化：虚拟滚动、v-once/v-memo、异步组件、keep-alive 缓存、响应式数据结构优化(shallowRef/markRaw)、SSR/Nuxt.js。生产级应用必须建立性能监控体系。",
     "learning_objectives": ["掌握 v-memo 与 v-once 优化", "理解 shallowRef/markRaw 使用场景", "学会虚拟滚动与异步组件", "了解 SSR 与 Nuxt.js"],
     "code_examples": ["import { shallowRef, markRaw, triggerRef } from 'vue';\n\nconst bigList = shallowRef<{ id: number; name: string }[]>([]);\nasync function loadList() {\n  const data = await fetch('/api/items').then(r => r.json());\n  bigList.value = data;\n  triggerRef(bigList);\n}\n\nconst chartInstance = markRaw(new Chart(ctx, config));\n\n// v-memo — 条件性跳过更新\n// <div v-for=\"item in list\" :key=\"item.id\" v-memo=\"[item.selected]\">\n//   <!-- 仅当 item.selected 变化时才更新 -->\n// </div>"]},
]

ALL_KPS = PYTHON_KPS + JAVASCRIPT_KPS + RUST_KPS + REACT_KPS + VUE_KPS

PREREQUISITE_CHAINS = {
    "python": list(range(len(PYTHON_KPS))),
    "javascript": list(range(len(JAVASCRIPT_KPS))),
    "rust": [0, 3, 4, 5, 6, 1, 2, 7, 8, 9, 10, 11, 12, 13],
    "react": list(range(len(REACT_KPS))),
    "vue": list(range(len(VUE_KPS))),
}


async def seed():
    async for db in get_db():
        r = await db.execute(select(KnowledgePoint).limit(1))
        if r.scalar_one_or_none():
            print("Clearing existing data...")
            await db.execute(delete(KnowledgeEdge))
            await db.execute(delete(KnowledgePoint))
            await db.flush()

        created_ids: dict[str, list[str]] = {}

        for kp_data in ALL_KPS:
            kp = KnowledgePoint(
                id=str(uuid.uuid4()),
                title=kp_data["title"],
                topic=kp_data["topic"],
                difficulty=kp_data["difficulty"],
                irt_b_param=kp_data["irt_b_param"],
                description=kp_data["description"],
                learning_objectives=kp_data.get("learning_objectives"),
                code_examples=kp_data.get("code_examples"),
                prerequisites=[],
            )
            db.add(kp)
            await db.flush()

            topic = kp_data["topic"]
            if topic not in created_ids:
                created_ids[topic] = []
            created_ids[topic].append(kp.id)
            print(f"  [{topic}] L{kp_data['difficulty']} {kp_data['title']}")

        for topic, chain in PREREQUISITE_CHAINS.items():
            ids = created_ids.get(topic, [])
            for i in range(1, len(chain)):
                if chain[i] < len(ids) and chain[i - 1] < len(ids):
                    edge = KnowledgeEdge(
                        id=str(uuid.uuid4()),
                        from_kp_id=ids[chain[i - 1]],
                        to_kp_id=ids[chain[i]],
                        relation_type="prerequisite",
                    )
                    db.add(edge)

                    kp_r = await db.execute(select(KnowledgePoint).where(KnowledgePoint.id == ids[chain[i]]))
                    kp_obj = kp_r.scalar_one_or_none()
                    if kp_obj:
                        prereqs = kp_obj.prerequisites or []
                        prereqs.append(ids[chain[i - 1]])
                        kp_obj.prerequisites = prereqs

        await db.commit()
        total = sum(len(v) for v in created_ids.values())
        print(f"\nSeeded {total} knowledge points across {len(created_ids)} topics.")
        break


if __name__ == "__main__":
    asyncio.run(seed())
