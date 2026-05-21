from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgePoint, KnowledgeEdge
from loguru import logger


PYTHON_KNOWLEDGE_GRAPH = [
    {
        "title": "变量与数据类型",
        "description": "学习Python中的变量声明、基本数据类型（int, float, str, bool）以及类型转换",
        "topic": "python-basics",
        "difficulty": 1,
        "irt_b_param": -1.5,
        "prerequisites": [],
        "learning_objectives": ["理解变量的概念", "掌握4种基本数据类型", "能够进行类型转换"],
    },
    {
        "title": "运算符与表达式",
        "description": "算术运算符、比较运算符、逻辑运算符、赋值运算符的使用",
        "topic": "python-basics",
        "difficulty": 1,
        "irt_b_param": -1.2,
        "prerequisites": ["变量与数据类型"],
        "learning_objectives": ["掌握算术运算符", "理解比较和逻辑运算", "能写出复合表达式"],
    },
    {
        "title": "字符串操作",
        "description": "字符串的创建、索引、切片、格式化以及常用方法",
        "topic": "python-basics",
        "difficulty": 1,
        "irt_b_param": -0.8,
        "prerequisites": ["变量与数据类型"],
        "learning_objectives": ["掌握字符串索引和切片", "学会字符串格式化", "了解常用字符串方法"],
    },
    {
        "title": "条件判断 if-elif-else",
        "description": "条件语句的语法、嵌套条件、三元表达式",
        "topic": "python-basics",
        "difficulty": 2,
        "irt_b_param": -0.5,
        "prerequisites": ["运算符与表达式"],
        "learning_objectives": ["掌握if-elif-else语法", "理解条件嵌套", "学会三元表达式"],
    },
    {
        "title": "while循环",
        "description": "while循环语法、循环条件、break和continue、无限循环",
        "topic": "python-basics",
        "difficulty": 2,
        "irt_b_param": -0.2,
        "prerequisites": ["条件判断 if-elif-else"],
        "learning_objectives": ["掌握while循环语法", "理解break和continue", "能避免无限循环"],
    },
    {
        "title": "for循环与range",
        "description": "for循环遍历、range函数、嵌套循环、列表推导式入门",
        "topic": "python-basics",
        "difficulty": 2,
        "irt_b_param": 0.0,
        "prerequisites": ["while循环"],
        "learning_objectives": ["掌握for循环语法", "理解range函数", "能使用嵌套循环"],
    },
    {
        "title": "列表 List",
        "description": "列表的创建、索引、切片、增删改查、列表方法",
        "topic": "python-data-structures",
        "difficulty": 2,
        "irt_b_param": 0.2,
        "prerequisites": ["for循环与range"],
        "learning_objectives": ["掌握列表基本操作", "学会列表方法", "理解列表可变性"],
    },
    {
        "title": "字典 Dict",
        "description": "字典的创建、键值对操作、字典方法、嵌套字典",
        "topic": "python-data-structures",
        "difficulty": 3,
        "irt_b_param": 0.5,
        "prerequisites": ["列表 List"],
        "learning_objectives": ["掌握字典基本操作", "理解键值对概念", "能使用嵌套字典"],
    },
    {
        "title": "元组与集合",
        "description": "元组的不可变性、集合的去重和集合运算",
        "topic": "python-data-structures",
        "difficulty": 3,
        "irt_b_param": 0.6,
        "prerequisites": ["字典 Dict"],
        "learning_objectives": ["理解元组不可变性", "掌握集合操作", "区分可变与不可变类型"],
    },
    {
        "title": "函数基础",
        "description": "函数定义、参数传递、返回值、作用域、递归入门",
        "topic": "python-functions",
        "difficulty": 3,
        "irt_b_param": 0.8,
        "prerequisites": ["元组与集合"],
        "learning_objectives": ["掌握函数定义和调用", "理解参数和返回值", "了解作用域规则"],
    },
    {
        "title": "高阶函数与Lambda",
        "description": "map、filter、reduce、lambda表达式、闭包",
        "topic": "python-functions",
        "difficulty": 4,
        "irt_b_param": 1.2,
        "prerequisites": ["函数基础"],
        "learning_objectives": ["掌握lambda表达式", "学会map/filter/reduce", "理解闭包概念"],
    },
    {
        "title": "面向对象编程",
        "description": "类与对象、继承、多态、封装、魔术方法",
        "topic": "python-oop",
        "difficulty": 4,
        "irt_b_param": 1.5,
        "prerequisites": ["高阶函数与Lambda"],
        "learning_objectives": ["掌握类和对象", "理解继承和多态", "学会封装和魔术方法"],
    },
    {
        "title": "文件操作与异常处理",
        "description": "文件读写、with语句、try-except-finally、自定义异常",
        "topic": "python-advanced",
        "difficulty": 4,
        "irt_b_param": 1.8,
        "prerequisites": ["面向对象编程"],
        "learning_objectives": ["掌握文件读写", "理解异常处理机制", "能编写健壮的代码"],
    },
    {
        "title": "模块与包",
        "description": "import机制、包结构、__init__.py、pip使用",
        "topic": "python-advanced",
        "difficulty": 4,
        "irt_b_param": 1.6,
        "prerequisites": ["文件操作与异常处理"],
        "learning_objectives": ["理解模块化编程", "掌握import机制", "学会创建和使用包"],
    },
    {
        "title": "算法与数据结构基础",
        "description": "排序算法、搜索算法、栈、队列、链表",
        "topic": "python-algorithms",
        "difficulty": 5,
        "irt_b_param": 2.2,
        "prerequisites": ["模块与包"],
        "learning_objectives": ["掌握基本排序算法", "理解栈和队列", "能分析时间复杂度"],
    },
]


async def seed_knowledge_graph(db: AsyncSession) -> dict:
    existing = await db.execute(select(KnowledgePoint))
    if existing.scalars().first():
        logger.info("Knowledge graph already seeded, skipping")
        return {"status": "skipped", "reason": "already seeded"}

    kp_map: dict[str, uuid.UUID] = {}

    for kp_data in PYTHON_KNOWLEDGE_GRAPH:
        kp = KnowledgePoint(
            title=kp_data["title"],
            description=kp_data["description"],
            topic=kp_data["topic"],
            difficulty=kp_data["difficulty"],
            irt_b_param=kp_data["irt_b_param"],
            prerequisites=kp_data["prerequisites"],
            learning_objectives=kp_data["learning_objectives"],
        )
        db.add(kp)
        await db.flush()
        kp_map[kp_data["title"]] = kp.id

    await db.commit()

    edge_count = 0
    for kp_data in PYTHON_KNOWLEDGE_GRAPH:
        for prereq_title in kp_data["prerequisites"]:
            if prereq_title in kp_map:
                edge = KnowledgeEdge(
                    from_kp_id=kp_map[prereq_title],
                    to_kp_id=kp_map[kp_data["title"]],
                    relation_type="prerequisite",
                )
                db.add(edge)
                edge_count += 1

    await db.commit()

    logger.info(f"Seeded {len(kp_map)} knowledge points and {edge_count} edges")
    return {"status": "seeded", "knowledge_points": len(kp_map), "edges": edge_count}
