import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

# 模拟课程数据
test_courses = [
    {"name": "Web软件工程项目实践", "type": "新生项目式课程", "semester": 2, "credits": 1},
    {"name": "C++语言程序设计", "type": "面向对象程序设计课程", "semester": 3, "credits": 3},
    {"name": "小波与引力波基础及前沿进展", "type": "学科前沿课", "semester": 7, "credits": 1},
]

test_prompt = """请为计算机专业学生规划课程。
学生当前在第4学期，培养方向为人工智能。

规则：
1. 必须从以下三类中各选1门：
   - 新生项目式课程：Web软件工程项目实践(第2学期，1学分)
   - 面向对象程序设计课程：C++语言程序设计(第3学期，3学分)
   - 学科前沿课：小波与引力波基础及前沿进展(第7学期，1学分)
2. 每学期最多选2门

请输出JSON格式。"""

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "输出JSON格式，不要添加解释"},
        {"role": "user", "content": test_prompt}
    ],
    temperature=0.7,
    max_tokens=1000
)

print("AI 响应:")
print(response.choices[0].message.content)