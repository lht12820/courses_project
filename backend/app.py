from flask import Flask, Response, request
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import re
import csv

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
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'CS_courses.csv')

def load_courses():
    """加载CSV文件中的课程数据（使用csv模块）"""
    try:
        courses = []
        # 使用 utf-8-sig 编码处理可能的 BOM 头
        with open(DATA_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 获取列名（兼容可能的列名变体）
                name = row.get('课程名称', '')
                category = row.get('课程类别', '')
                credits = float(row.get('学分', 0)) if row.get('学分', '') else 0
                semester = int(row.get('开课学期', 0)) if row.get('开课学期', '') else 0
                direction = row.get('专业方向', '通用')
                
                # 跳过空课程名
                if not name:
                    continue
                
                courses.append({
                    '课程名称': name,
                    '课程类别': category,
                    '学分': credits,
                    '开课学期': semester,
                    '专业方向': direction if direction else '通用'
                })
        
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
### 新生项目式课程
{json.dumps(courses_by_type['新生项目式课程'], ensure_ascii=False, indent=2)}

### 面向对象程序设计课程
{json.dumps(courses_by_type['面向对象程序设计课程'], ensure_ascii=False, indent=2)}

### 学科前沿课
{json.dumps(courses_by_type['学科前沿课'], ensure_ascii=False, indent=2)}

### 专业方向选修课
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
        {{"name": "课程名称", "type": "课程类别", "credits": 3}}
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
def build_courses_snapshot(courses):
    """
    构建课程快照（不按学期筛选，包含所有课程）
    """
    snapshot = []
    for c in courses:
        snapshot.append({
            'name': c['课程名称'],
            'type': c['课程类别'],
            'semester': c['开课学期'],
            'credits': c['学分'],
            'direction': c['专业方向']
        })
    # 按固定规则排序，确保字符串完全一致
    snapshot.sort(key=lambda x: (x['semester'], x['name'], x['type']))
    return snapshot

def build_system_prompt(courses_snapshot):
    """
    构建 system prompt（静态部分，包含完整课程库）
    """
    # 按类别整理课程
    courses_by_type = {
        '新生项目式课程': [],
        '面向对象程序设计课程': [],
        '学科前沿课': [],
        '专业方向选修课': []
    }
    
    for c in courses_snapshot:
        category = c['type']
        if category in courses_by_type:
            courses_by_type[category].append(c)
    
    # 对每类课程内的列表排序
    for cat in courses_by_type:
        courses_by_type[cat].sort(key=lambda x: (x['name'], x['semester']))
    
    system_prompt = f"""你是一个计算机专业的课程规划专家。请严格根据以下完整课程库和规划规则，为学生制定剩余的选修课程规划。

## 完整课程库（唯一依据，所有课程都在这里）
### 新生项目式课程（每门课都有开课学期，必须选开课学期>=当前学期的）
{json.dumps(courses_by_type['新生项目式课程'], ensure_ascii=False, indent=2)}

### 面向对象程序设计课程（每门课都有开课学期，必须选开课学期>=当前学期的）
{json.dumps(courses_by_type['面向对象程序设计课程'], ensure_ascii=False, indent=2)}

### 学科前沿课（每门课都有开课学期，必须选开课学期>=当前学期的）
{json.dumps(courses_by_type['学科前沿课'], ensure_ascii=False, indent=2)}

### 专业方向选修课（每门课都有开课学期，必须选开课学期>=当前学期的）
{json.dumps(courses_by_type['专业方向选修课'], ensure_ascii=False, indent=2)}

## 规划规则
1. **强制要求**：新生项目课、面向对象程序设计课、学科前沿课，三类课程各必选且仅选1门
2. **学期限制**：每学期最多从课程库里选2门课程（可以不选）
3. **开课学期**：只能选择开课学期 >= 当前学期的课程（重要！）
4. **方向匹配**：优先选择与学生培养方向匹配的专业方向选修课
5. **学分平衡**：各学期学分分布尽量均衡

## 输出格式
请严格按照以下 JSON 格式输出，不要添加任何额外文字：

{{
  "plan": [
    {{
      "semester": 5,
      "courses": [
        {{"name": "课程名称", "type": "课程类别", "credits": 3}}
      ]
    }}
  ],
  "summary": {{
    "total_courses": 8,
    "total_credits": 24,
    "message": "规划说明"
  }}
}}"""
    
    return system_prompt

def build_user_prompt(user_input, electives_taken):
    """
    构建 user prompt（动态部分，包含学期信息和已修课程）
    """
    user_prompt = f"""## 学生信息
- 专业：{user_input['major']}
- 当前学期：第{user_input['semester']}学期（重要：只能推荐开课学期 >= {user_input['semester']} 的课程）
- 培养方向：{user_input['direction'] if user_input['direction'] else '未指定'}
- 已修课程：{', '.join(electives_taken) if electives_taken else '无'}

请根据系统指令中的完整课程库，为以上学生生成课程规划。注意：只能推荐开课学期 >= {user_input['semester']} 的课程。"""
    
    return user_prompt

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
    """使用 DeepSeek AI 生成课程规划（利用 API 输入缓存）"""
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
        
        # 构建课程快照（用于 system prompt，确保顺序一致）
        # courses_snapshot = build_courses_snapshot(courses, user_input['semester'])
        courses_snapshot = build_courses_snapshot(courses)
        
        # 构建 system prompt（静态部分，可被缓存）
        system_prompt = build_system_prompt(courses_snapshot)
        
        # 构建 user prompt（动态部分）
        user_prompt = build_user_prompt(user_input, electives_taken)
        
        # 计算 system prompt 的 token 数（估算）
        system_prompt_length = len(system_prompt)
        
        print(f"\n{'='*50}")
        print(f"📤 发送请求到 DeepSeek API...")
        print(f"   用户: {user_input['major']}, 第{user_input['semester']}学期, 方向:{user_input['direction'] or '未指定'}")
        print(f"   已修课程: {electives_taken if electives_taken else '无'}")
        print(f"   System Prompt 长度: {system_prompt_length} 字符（静态部分，可被缓存）")
        print(f"   User Prompt 长度: {len(user_prompt)} 字符（动态部分）")
        print(f"{'='*50}")
        
        # 调用 DeepSeek API（利用其自动缓存机制）
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            stream=False
        )
        
        # 获取 token 使用量
        usage = response.usage
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        total_tokens = usage.total_tokens
        
        # 检查是否有缓存命中信息
        prompt_tokens_details = getattr(usage, 'prompt_tokens_details', None)
        cached_tokens = 0
        if prompt_tokens_details:
            # 正确的字段名是 prompt_cache_hit_tokens
            cached_tokens = getattr(prompt_tokens_details, 'prompt_cache_hit_tokens', 0)
        
        # 打印 token 统计
        print(f"\n{'='*50}")
        print(f"📊 Token 使用统计:")
        print(f"   ├─ 输入 token 数: {prompt_tokens}")
        if cached_tokens > 0:
            print(f"   │  └─ 其中缓存命中: {cached_tokens} tokens (节省成本!)")
        print(f"   ├─ 输出 token 数: {completion_tokens}")
        print(f"   └─ 总 token 数: {total_tokens}")
        
        if cached_tokens > 0:
            # 估算节省的费用（按价格页面：缓存命中0.2元/百万，未命中2元/百万）
            saved_cost = (cached_tokens / 1_000_000) * (2 - 0.2)
            print(f"   💰 本次请求节省约: ¥{saved_cost:.6f}")
        print(f"{'='*50}\n")
        
        ai_response = response.choices[0].message.content
        
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
            'cached': cached_tokens > 0,
            'token_usage': {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': total_tokens,
                'cached_tokens': cached_tokens
            }
        })
        
    except Exception as e:
        print(f"\n❌ AI 规划失败: {e}")
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

# ==================== 静态文件托管（用于打包后访问前端） ====================
# 获取前端静态文件目录（支持 PyInstaller 打包后的路径）
def get_frontend_dist_path():
    """获取前端静态文件目录路径（兼容 PyInstaller）"""
    import sys
    if getattr(sys, 'frozen', False):
        # 打包后的环境
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, 'frontend_dist')

FRONTEND_DIST = get_frontend_dist_path()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """托管前端静态文件"""
    if path.startswith('api/'):
        # API 请求交给其他路由处理
        return json_utf8({'error': 'Not Found'}, 404)
    
    file_path = os.path.join(FRONTEND_DIST, path)
    if path and os.path.exists(file_path) and os.path.isfile(file_path):
        # 返回静态资源文件
        from flask import send_file
        return send_file(file_path)
    
    # 返回 index.html（Vue Router 路由）
    index_path = os.path.join(FRONTEND_DIST, 'index.html')
    if os.path.exists(index_path):
        from flask import send_file
        return send_file(index_path)
    
    return json_utf8({'error': 'Not Found'}, 404)

if __name__ == '__main__':
    app.run(debug=True, port=5000)