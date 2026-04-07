from flask import Flask, Response, request
from flask_cors import CORS
import json
import pandas as pd
import os

app = Flask(__name__)
CORS(app)

app.config['JSON_AS_ASCII'] = False

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