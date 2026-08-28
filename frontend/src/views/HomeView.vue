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
      <el-card v-for="f in features" :key="f.title" class="feature-card" shadow="hover">
        <div class="feature-icon">{{ f.icon }}</div>
        <h3>{{ f.title }}</h3>
        <p>{{ f.desc }}</p>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'

const { token } = storeToRefs(useAuthStore())

const features = [
  {
    icon: '📚',
    title: 'RAG 知识库问答',
    desc: '上传 PDF / TXT / Markdown，AI 基于你的资料回答并标注引用来源。',
  },
  {
    icon: '💬',
    title: 'AI 流式对话',
    desc: '多轮对话、SSE 流式输出、Markdown 渲染与代码高亮。',
  },
  {
    icon: '🤖',
    title: 'Agent 任务管理',
    desc: '一句话让 AI 创建、查询、修改你的任务，自动调用工具完成。',
  },
  {
    icon: '📊',
    title: '用量统计',
    desc: '直观查看 AI 调用次数、Token 消耗与成功率趋势。',
  },
]
</script>

<style scoped>
.home {
  max-width: 960px;
  margin: 0 auto;
  padding-top: 48px;
}
.hero {
  text-align: center;
  padding: 32px 0;
}
.logo {
  font-size: 42px;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(135deg, #409eff, #67c23a);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.slogan {
  font-size: 20px;
  color: #333;
  margin-top: 12px;
}
.desc {
  font-size: 14px;
  color: #999;
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
}
.feature-icon {
  font-size: 32px;
}
.feature-card h3 {
  margin: 8px 0;
}
.feature-card p {
  font-size: 13px;
  color: #666;
  line-height: 1.6;
}
</style>
