<template>
  <div class="home">
    <div class="hero">
      <h1 class="logo">AI Brain</h1>
      <p class="slogan">个人智能知识库与 AI 助理平台</p>
      <p class="desc">上传你的资料，让 AI 基于你的知识回答问题、总结文档、管理任务。</p>
      <div class="actions">
        <template v-if="token">
          <el-button type="primary" size="large" @click="$router.push('/chat')">
            开始对话
          </el-button>
          <el-button size="large" @click="$router.push('/knowledge-bases')">
            管理知识库
          </el-button>
          <el-button size="large" @click="$router.push('/tasks')">查看任务</el-button>
        </template>
        <template v-else>
          <el-button type="primary" size="large" @click="$router.push('/register')">
            免费注册
          </el-button>
          <el-button size="large" @click="$router.push('/login')">登录</el-button>
        </template>
      </div>
    </div>

    <div class="features">
      <el-card
        v-for="f in features"
        :key="f.title"
        class="feature-card"
        shadow="hover"
        @click="goFeature(f.path)"
      >
        <h3>{{ f.title }}</h3>
        <p>{{ f.desc }}</p>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const { token } = storeToRefs(useAuthStore())
const router = useRouter()

const features = [
  {
    title: 'AI 流式对话',
    desc: '多对话流式输出，Markdown渲染与代码高亮。',
    path: '/chat',
  },
  {
    title: 'RAG 知识库问答',
    desc: '上传文档，AI 基于你的资料回答问题，标注引用来源。',
    path: '/knowledge-bases',
  },
  {
    title: 'Agent 任务管理',
    desc: '一句话让 AI 帮你创建、查询和修改任务。',
    path: '/tasks',
  },
  {
    title: '用量统计',
    desc: '直观查看 AI 调用次数、Token 消耗与成功率。',
    path: '/stats',
  },
]

/** 点击功能卡片跳转对应模块（未登录时由路由守卫引导登录） */
function goFeature(path: string) {
  router.push(path)
}
</script>

<style scoped>
.home {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px 20px;
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
/* 内容整组垂直居中（hero 与 features 之间保持固定间距） */
.home::before {
  content: '';
  flex-grow: 3.7;
  flex-basis: 0;
  flex-shrink: 0;
}
.home::after {
  content: '';
  flex-grow: 6.3;
  flex-basis: 0;
  flex-shrink: 0;
}
.hero {
  text-align: center;
  padding: 24px 0;
  margin: 0;
}
.features {
  margin-top: 32px;
  margin-bottom: 0;
}
.hero {
  text-align: center;
  padding: 32px 0;
}.logo {
  font-size: 46px;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(135deg, var(--el-color-primary), var(--el-color-primary-light-5));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.slogan {
  font-size: 22px;
  color: var(--el-text-color-primary);
  margin-top: 12px;
}
.desc {
  font-size: 16px;
  color: var(--el-text-color-secondary);
  margin-top: 8px;
}
.actions {
  margin-top: 24px;
  display: flex;
  gap: 12px;
  justify-content: center;
}
.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-top: 32px;
}
.feature-card {
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 12px 8px;
  cursor: pointer;
  transition:
    border-color 0.2s,
    transform 0.2s,
    box-shadow 0.2s;
}
/* 减小卡片内边距，让描述每行容纳更多字（两行排下） */
.feature-card :deep(.el-card__body) {
  padding: 14px 10px;
}
.feature-card:hover {
  border-color: var(--el-color-primary);
  transform: translateY(-3px);
}
.feature-card h3 {
  margin: 0 0 10px;
  font-size: 17px;
}
.feature-card p {
  margin: 0;
  font-size: 14.5px;
  color: var(--el-text-color-secondary);
  line-height: 1.65;
  /* 统一占两行高度：四个卡片描述区高度一致 */
  min-height: 3.3em;
}
</style>
