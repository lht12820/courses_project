from flask import Flask, Response, request
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
import json
import pandas as pd
import os
import re

app = Flask(__name__)
CORS(app)

app.config['JSON_AS_ASCII'] = False

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)
app.config['JSON_AS_ASCII'] = False

# 初始化 DeepSeek 客户端
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
if not DEEPSEEK_API_KEY:
    print("⚠️ 警告：未找到 DEEPSEEK_API_KEY，AI 规划功能将不可用")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
) if DEEPSEEK_API_KEY else None

# 数据文件路径
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'CS_courses.xlsx')

def load_courses():
    """加载Excel中的课程数据"""
    try:
        # 读取Excel文件
        df = pd.read_excel(DATA_FILE)
        
        # 重命名列（根据实际Excel列名）
        df.columns = ['课程名称', '课程类别', '学分', '开课学期', '专业方向']
        
        # 清洗数据：去除空值行
        df = df.dropna(subset=['课程名称'])
        
        # 填充空值
        df['专业方向'] = df['专业方向'].fillna('通用')
        df['开课学期'] = df['开课学期'].fillna(0).astype(int)
        
        # 转换为字典列表
        courses = df.to_dict('records')
        return courses
    except Exception as e:
        print(f"加载课程数据失败: {e}")
        return []

def json_utf8(data, status_code=200):
    response = Response(
        json.dumps(data, ensure_ascii=False),
        mimetype='application/json; charset=utf-8',
        status=status_code
    )
    return response

# ==================== API接口 ====================
def build_ai_prompt(courses, user_input, electives_taken):
    """
    构建发送给 DeepSeek 的 Prompt
    """
    # 按类别和学期整理课程
    courses_by_type = {
        '新生项目式课程': [],
        '面向对象程序设计课程': [],
        '学科前沿课': [],
        '专业方向选修课': []
    }
    
    for c in courses:
        if c['开课学期'] >= user_input['semester']:  # 只考虑当前学期及之后的课程
            category = c['课程类别']
            if category in courses_by_type:
                courses_by_type[category].append({
                    'name': c['课程名称'],
                    'semester': c['开课学期'],
                    'credits': c['学分'],
                    'direction': c['专业方向']
                })
    
    prompt = f"""你是一个计算机专业的课程规划专家。请根据以下信息，为学生制定剩余的选修课程规划。

## 学生信息
- 专业：{user_input['major']}
- 当前学期：第{user_input['semester']}学期（从该学期开始规划）
- 培养方向：{user_input['direction']}
- 已修课程：{', '.join(electives_taken) if electives_taken else '无'}

## 可选课程库
### 新生项目式课程（必选1门，仅选1门）
{json.dumps(courses_by_type['新生项目式课程'], ensure_ascii=False, indent=2)}

### 面向对象程序设计课程（必选1门，仅选1门）
{json.dumps(courses_by_type['面向对象程序设计课程'], ensure_ascii=False, indent=2)}

### 学科前沿课（必选1门，仅选1门）
{json.dumps(courses_by_type['学科前沿课'], ensure_ascii=False, indent=2)}

### 专业方向选修课（根据培养方向选择，每学期最多2门）
{json.dumps(courses_by_type['专业方向选修课'], ensure_ascii=False, indent=2)}

## 规划规则
1. **强制要求**：新生项目课、面向对象程序设计课、学科前沿课，三类课程各必选且仅选1门
2. **学期限制**：每学期最多从课程库里选2门课程（可以不选）
3. **开课学期**：只能选择开课学期 >= 当前学期的课程
4. **方向匹配**：优先选择与学生培养方向匹配的专业方向选修课
5. **学分平衡**：各学期学分分布尽量均衡

## 输出格式
请严格按照以下 JSON 格式输出，不要添加任何额外文字：

{{
  "plan": [
    {{
      "semester": 5,
      "courses": [
        {{"name": "课程名称", "type": "课程类别", "credits": 3, "reason": "选择理由"}}
      ]
    }}
  ],
  "summary": {{
    "total_courses": 8,
    "total_credits": 24,
    "message": "规划说明"
  }}
}}

请开始规划。"""
    
    return prompt

def parse_ai_response(response_text):
    """解析 AI 返回的 JSON 响应"""
    try:
        # 尝试提取 JSON 部分（防止 AI 添加额外文字）
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}")
        print(f"原始响应: {response_text}")
        return None

@app.route('/api/ai-plan', methods=['POST'])
def ai_plan():
    """使用 DeepSeek AI 生成课程规划"""
    try:
        data = request.get_json()
        
        if not client:
            return json_utf8({
                'success': False,
                'error': 'AI 服务未配置，请检查 DEEPSEEK_API_KEY'
            }, 500)
        
        # 获取用户输入
        user_input = {
            'major': data.get('major', '计算机科学与技术'),
            'semester': int(data.get('semester', 1)),
            'direction': data.get('direction', '')
        }
        electives_taken = data.get('electives', [])
        
        # 加载课程数据
        courses = load_courses()
        if not courses:
            return json_utf8({
                'success': False,
                'error': '课程数据加载失败'
            }, 500)
        
        # 构建 Prompt
        prompt = build_ai_prompt(courses, user_input, electives_taken)
        
        print(f"📤 发送请求到 DeepSeek API...")
        
        # 调用 DeepSeek API
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的课程规划专家，只输出 JSON 格式的结果，不要添加任何解释文字。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            stream=False
        )
        
        ai_response = response.choices[0].message.content
        print(f"📥 AI 响应: {ai_response[:200]}...")
        
        # 解析 AI 响应
        plan_data = parse_ai_response(ai_response)
        
        if not plan_data:
            return json_utf8({
                'success': False,
                'error': 'AI 返回结果解析失败'
            }, 500)
        
        return json_utf8({
            'success': True,
            'plan': plan_data.get('plan', []),
            'summary': plan_data.get('summary', {}),
            'raw_response': ai_response  # 可选，用于调试
        })
        
    except Exception as e:
        print(f"AI 规划失败: {e}")
        import traceback
        traceback.print_exc()
        return json_utf8({
            'success': False,
            'error': str(e)
        }, 500)


@app.route('/api/health', methods=['GET'])
def health():
    return json_utf8({'status': 'ok', 'message': '服务运行正常'})

@app.route('/api/courses', methods=['GET'])
def get_courses():
    """获取所有课程数据"""
    courses = load_courses()
    # 按开课学期排序
    courses.sort(key=lambda x: x['开课学期'])
    return json_utf8({
        'success': True,
        'count': len(courses),
        'courses': courses
    })

@app.route('/api/courses/filter', methods=['POST'])
def filter_courses():
    """
    根据条件筛选课程
    接收参数：
    - semester: 当前学期（之后未修的课程）
    - direction: 专业方向（可选）
    - category: 课程类别（可选）
    """
    try:
        data = request.get_json()
        current_semester = int(data.get('semester', 1))
        direction = data.get('direction', '')
        category = data.get('category', '')
        
        courses = load_courses()
        
        # 筛选未修的课程（开课学期 > 当前学期）
        filtered = [c for c in courses if c['开课学期'] > current_semester]
        
        # 按专业方向筛选
        if direction and direction != '通用':
            filtered = [c for c in filtered if direction in str(c['专业方向'])]
        
        # 按课程类别筛选
        if category:
            filtered = [c for c in filtered if c['课程类别'] == category]
        
        # 按开课学期分组
        grouped = {}
        for course in filtered:
            semester = course['开课学期']
            if semester not in grouped:
                grouped[semester] = []
            grouped[semester].append(course)
        
        # 统计信息
        category_stats = {}
        for course in filtered:
            cat = course['课程类别']
            category_stats[cat] = category_stats.get(cat, 0) + 1
        
        return json_utf8({
            'success': True,
            'total': len(filtered),
            'grouped': grouped,
            'stats': {
                'by_semester': {k: len(v) for k, v in grouped.items()},
                'by_category': category_stats
            }
        })
        
    except Exception as e:
        print(f"筛选课程失败: {e}")
        import traceback
        traceback.print_exc()
        return json_utf8({'success': False, 'error': str(e)}, 500)

@app.route('/api/plan', methods=['POST'])
def generate_plan():
    """
    生成课程规划（基于实际数据）
    接收参数：
    - major: 专业
    - semester: 当前学期（从该学期开始规划）
    - electives: 已修选修课列表
    - direction: 培养方向（支持自由输入）
    """
    try:
        data = request.get_json()
        current_semester = int(data.get('semester', 1))  # 从该学期开始规划
        direction = data.get('direction', '')
        
        courses = load_courses()
        
        # 筛选未修课程（开课学期 >= 当前学期）
        remaining = [c for c in courses if c['开课学期'] >= current_semester]
        
        # 根据方向筛选推荐课程（临时规则，后续接入AI agent）
        recommended = []
        if direction and direction != '通用':
            for course in remaining:
                course_direction = str(course['专业方向'])
                if direction in course_direction or course_direction == '通用':
                    recommended.append(course)
        else:
            recommended = remaining
        
        # 按学期分组
        plan_by_semester = {}
        for course in recommended:
            sem = f"第{course['开课学期']}学期"
            if sem not in plan_by_semester:
                plan_by_semester[sem] = []
            plan_by_semester[sem].append({
                'name': course['课程名称'],
                'type': course['课程类别'],
                'credits': course['学分'],
                'direction': course['专业方向']
            })
        
        # 统计信息
        total_credits = sum(c['学分'] for c in recommended)
        
        return json_utf8({
            'success': True,
            'plan': plan_by_semester,
            'summary': {
                'current_semester': current_semester,
                'direction': direction if direction else '通用',
                'total_courses': len(recommended),
                'total_credits': total_credits,
                'remaining_semesters': sorted(set(c['开课学期'] for c in recommended))
            }
        })
        
    except Exception as e:
        print(f"生成规划失败: {e}")
        import traceback
        traceback.print_exc()
        return json_utf8({'success': False, 'error': str(e)}, 500)

if __name__ == '__main__':
    app.run(debug=True, port=5000)