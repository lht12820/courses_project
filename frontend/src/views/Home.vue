<template>
  <div class="home">
    <h1>🎓 AI课程规划系统</h1>
    <p class="subtitle">基于课程库的智能选修规划</p>

    <!-- 课程数据统计卡片 -->
    <div class="stats-card" v-if="courseStats">
      <h3>📊 课程库统计</h3>
      <div class="stats-grid">
        <div class="stat-item">
          <span class="stat-value">{{ courseStats.total }}</span>
          <span class="stat-label">总课程数</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ courseStats.categories.length }}</span>
          <span class="stat-label">课程类别</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ courseStats.semesters.length }}</span>
          <span class="stat-label">开课学期</span>
        </div>
      </div>
    </div>

    <!-- 输入表单 -->
    <div class="input-card">
      <h2>📝 规划参数</h2>
      
      <div class="form-group">
        <label>专业</label>
        <input type="text" v-model="form.major" placeholder="例：计算机科学与技术">
      </div>

      <div class="form-group">
      <label>当前学期</label>
      <select v-model="form.semester">
      <option v-for="n in 7" :key="n" :value="n">第{{ n }}学期</option>
      </select>
      <small>从该学期开始规划课程</small>
      </div>

      <div class="form-group">
        <label>已修的选修课（可选）</label>
        <input type="text" v-model="electivesInput" placeholder="例：Java语言程序设计, 数据结构">
        <small>多个课程用逗号分隔</small>
      </div>

     <div class="form-group">
  <label>培养方向</label>
  <div class="direction-input">
    <select v-model="selectedDirection">
      <option value="">请选择或自定义</option>
      <option value="人工智能">🤖 人工智能</option>
      <option value="大数据">📊 大数据</option>
      <option value="网络安全">🔒 网络安全</option>
      <option value="物联网">🌐 物联网</option>
      <option value="嵌入式">📱 嵌入式</option>
    </select>
    <input 
      type="text" 
      v-model="customDirection" 
      placeholder="或直接输入自定义方向"
    >
  </div>
  <small>可选择预设方向，或直接输入你的培养方向</small>
</div>


      <button @click="generatePlan" :disabled="isLoading" class="generate-btn">
        {{ isLoading ? '规划中...' : '🚀 生成课程规划' }}
      </button>
    </div>

    <!-- 规划结果 -->
    <div v-if="planResult" class="output-card">
      <div class="output-header">
        <h2>📋 课程规划结果</h2>
        <button @click="clearResult" class="clear-btn">清除</button>
      </div>
      
      <div class="summary">
        <div class="summary-grid">
          <div><strong>当前学期：</strong>第{{ planResult.summary.current_semester }}学期结束后</div>
          <div><strong>培养方向：</strong>{{ planResult.summary.direction }}</div>
          <div><strong>规划课程：</strong>{{ planResult.summary.total_courses }}门</div>
          <div><strong>总学分：</strong>{{ planResult.summary.total_credits }}学分</div>
          <div><strong>剩余学期：</strong>{{ planResult.summary.remaining_semesters.join('、') }}学期</div>
        </div>
      </div>

      <div class="plan-detail">
        <div v-for="(courses, semester) in planResult.plan" :key="semester" class="semester-block">
          <h3>{{ semester }}</h3>
          <table class="course-table">
            <thead>
              <tr><th>课程名称</th><th>课程类别</th><th>学分</th><th>专业方向</th></tr>
            </thead>
            <tbody>
              <tr v-for="course in courses" :key="course.name">
                <td class="course-name">{{ course.name }}</td>
                <td><span :class="['type-badge', getTypeClass(course.type)]">{{ course.type }}</span></td>
                <td>{{ course.credits }}</td>
                <td>{{ course.direction }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="note" v-if="planResult.summary.total_courses === 0">
        <p>⚠️ 当前学期后没有找到符合条件的课程，请尝试调整当前学期或培养方向。</p>
      </div>
    </div>

    <!-- 全部课程浏览 -->
    <div class="courses-card">
      <div class="courses-header">
        <h2>📚 全部课程库</h2>
        <button @click="toggleCourses" class="toggle-btn">
          {{ showAllCourses ? '收起' : '展开' }}
        </button>
      </div>
      
      <div v-if="showAllCourses" class="courses-list">
        <div v-if="allCourses.length === 0" class="loading">加载中...</div>
        <div v-else>
          <div class="course-filters">
            <input type="text" v-model="courseSearch" placeholder="搜索课程..." class="search-input">
            <select v-model="semesterFilter" class="semester-filter">
              <option value="">全部学期</option>
              <option v-for="n in 8" :key="n" :value="n">第{{ n }}学期</option>
            </select>
          </div>
          
          <table class="course-table full-table">
            <thead>
              <tr><th>课程名称</th><th>课程类别</th><th>学分</th><th>开课学期</th><th>专业方向</th></tr>
            </thead>
            <tbody>
              <tr v-for="course in filteredCourses" :key="course['课程名称']">
                <td class="course-name">{{ course['课程名称'] }}</td>
                <td><span :class="['type-badge', getTypeClass(course['课程类别'])]">{{ course['课程类别'] }}</span></td>
                <td>{{ course['学分'] }}</td>
                <td>第{{ course['开课学期'] }}学期</td>
                <td>{{ course['专业方向'] }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="errorMsg" class="error-card">
      <span>❌ {{ errorMsg }}</span>
      <button @click="errorMsg = ''">关闭</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted,watch } from 'vue'
import axios from 'axios'

// 表单数据
const form = ref({
  major: '计算机科学与技术',
  semester: 1,
  direction: '',
  
})

const selectedDirection = ref('')
const customDirection = ref('')
const electivesInput = ref('')
const isLoading = ref(false)
const planResult = ref(null)
const errorMsg = ref('')
const allCourses = ref([])
const showAllCourses = ref(false)
const courseSearch = ref('')
const semesterFilter = ref('')
const courseStats = ref(null)

// 监听预设方向变化
watch(selectedDirection, (newVal) => {
  if (newVal) {
    customDirection.value = ''  // 选择预设时清空自定义
    form.value.direction = newVal
  } else if (!customDirection.value) {
    form.value.direction = ''
  }
})

// 监听自定义方向变化
watch(customDirection, (newVal) => {
  if (newVal) {
    selectedDirection.value = ''  // 输入自定义时清空预设选择
    form.value.direction = newVal
  } else if (!selectedDirection.value) {
    form.value.direction = ''
  }
})

// 筛选后的课程
const filteredCourses = computed(() => {
  let result = allCourses.value
  
  if (courseSearch.value) {
    result = result.filter(c => 
      c['课程名称'].toLowerCase().includes(courseSearch.value.toLowerCase())
    )
  }
  
  if (semesterFilter.value) {
    result = result.filter(c => c['开课学期'] === parseInt(semesterFilter.value))
  }
  
  return result
})

// 加载课程统计
const loadCourseStats = async () => {
  try {
    const response = await axios.get('/api/courses')
    if (response.data.success) {
      allCourses.value = response.data.courses
      
      // 统计信息
      const categories = [...new Set(allCourses.value.map(c => c['课程类别']))]
      const semesters = [...new Set(allCourses.value.map(c => c['开课学期']))]
      
      courseStats.value = {
        total: allCourses.value.length,
        categories: categories,
        semesters: semesters.sort((a,b) => a-b)
      }
    }
  } catch (err) {
    console.error('加载课程失败:', err)
  }
}

// 生成规划
const generatePlan = async () => {
  isLoading.value = true
  planResult.value = null
  errorMsg.value = ''

  const electives = electivesInput.value
    .split(',')
    .map(s => s.trim())
    .filter(s => s)

  const requestData = {
    major: form.value.major,
    semester: form.value.semester,
    electives: electives,
    direction: form.value.direction  // 直接使用，已被 watch 更新
  }


  try {
    const response = await axios.post('/api/plan', requestData, {
      timeout: 30000
    })

    if (response.data.success) {
      planResult.value = response.data
    } else {
      errorMsg.value = response.data.error || '生成失败'
    }
  } catch (err) {
    console.error('请求失败:', err)
    if (err.response) {
      errorMsg.value = err.response.data.error || '服务器错误'
    } else if (err.code === 'ECONNABORTED') {
      errorMsg.value = '请求超时，请重试'
    } else {
      errorMsg.value = '连接后端失败，请确认 Flask 是否在运行'
    }
  } finally {
    isLoading.value = false
  }
}

const clearResult = () => {
  planResult.value = null
}

const toggleCourses = () => {
  showAllCourses.value = !showAllCourses.value
  if (showAllCourses.value && allCourses.value.length === 0) {
    loadCourseStats()
  }
}

const getTypeClass = (type) => {
  if (type.includes('新生项目')) return 'project'
  if (type.includes('前沿')) return 'frontier'
  if (type.includes('面向对象')) return 'oop'
  if (type.includes('专业方向')) return 'elective'
  return 'other'
}

// 页面加载时加载课程统计
onMounted(() => {
  loadCourseStats()
})
</script>

<style scoped>
.home {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 40px 20px;
}

h1 {
  color: white;
  text-align: center;
  font-size: 2.5rem;
  margin-bottom: 10px;
}

.subtitle {
  color: rgba(255,255,255,0.9);
  text-align: center;
  font-size: 1.2rem;
  margin-bottom: 40px;
}

/* 统计卡片 */
.stats-card {
  background: white;
  border-radius: 16px;
  padding: 20px 30px;
  max-width: 900px;
  margin: 0 auto 30px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.2);
}

.stats-card h3 {
  margin-bottom: 15px;
  color: #333;
}

.stats-grid {
  display: flex;
  justify-content: space-around;
  gap: 20px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 2rem;
  font-weight: bold;
  color: #667eea;
}

.stat-label {
  font-size: 0.85rem;
  color: #666;
}

/* 输入卡片 */
.input-card, .output-card, .courses-card, .error-card {
  background: white;
  border-radius: 16px;
  padding: 30px;
  max-width: 1200px;
  margin: 0 auto 30px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.2);
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-weight: bold;
  margin-bottom: 8px;
  color: #333;
}

.form-group input, .form-group select {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 0.3s;
}

.form-group input:focus, .form-group select:focus {
  outline: none;
  border-color: #667eea;
}

.form-group small {
  display: block;
  color: #666;
  font-size: 12px;
  margin-top: 5px;
}

.generate-btn {
  width: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 14px;
  border-radius: 8px;
  font-size: 18px;
  font-weight: bold;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.generate-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(0,0,0,0.3);
}

.generate-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.output-header, .courses-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 2px solid #eee;
  padding-bottom: 15px;
}

.output-header h2, .courses-header h2 {
  margin: 0;
  color: #333;
}

.clear-btn, .toggle-btn {
  background: #ff9800;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
}

.clear-btn:hover, .toggle-btn:hover {
  background: #e68900;
}

.summary {
  background: #f0f4ff;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 25px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
}

.semester-block {
  margin-bottom: 30px;
}

.semester-block h3 {
  color: #667eea;
  border-left: 4px solid #667eea;
  padding-left: 12px;
  margin-bottom: 15px;
}

.course-table {
  width: 100%;
  border-collapse: collapse;
}

.course-table th, .course-table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.course-table th {
  background: #f5f5f5;
  font-weight: bold;
}

.course-name {
  font-weight: 500;
}

.type-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
}

.type-badge.project { background: #e8f5e9; color: #2e7d32; }
.type-badge.frontier { background: #e3f2fd; color: #1565c0; }
.type-badge.oop { background: #fff3e0; color: #e65100; }
.type-badge.elective { background: #f3e5f5; color: #7b1fa2; }
.type-badge.other { background: #f5f5f5; color: #666; }

.note {
  margin-top: 20px;
  padding: 12px;
  background: #fff3e0;
  border-radius: 8px;
  font-size: 13px;
  color: #e65100;
}

.course-filters {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.search-input, .semester-filter {
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  flex: 1;
  min-width: 200px;
}

.full-table {
  max-height: 500px;
  overflow-y: auto;
  display: block;
}

.full-table thead {
  position: sticky;
  top: 0;
  background: white;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #666;
}

.error-card {
  background: #ffebee;
  border: 1px solid #ffcdd2;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.error-card button {
  background: #c62828;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
}
.direction-input {
  display: flex;
  gap: 10px;
}

.direction-input select,
.direction-input input {
  flex: 1;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 16px;
}

.direction-input select:focus,
.direction-input input:focus {
  outline: none;
  border-color: #667eea;
}
</style>