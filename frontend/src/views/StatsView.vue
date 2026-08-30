<template>
  <div class="stats-page">
    <h2 class="page-title">AI 使用统计</h2>

    <el-row :gutter="16" class="summary-row">
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="metric-label">总请求次数</div>
          <div class="metric-value">{{ stats?.summary.total_requests ?? '-' }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="metric-label">成功率</div>
          <div class="metric-value">{{ stats?.summary.success_rate ?? '-' }}%</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="metric-label">Token 消耗</div>
          <div class="metric-value">{{ stats?.summary.total_tokens ?? '-' }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="chart-card">
      <template #header>近 7 天趋势（请求次数 / Token）</template>
      <div ref="chartRef" class="chart"></div>
      <el-empty
        v-if="!stats?.daily.length"
        description="暂无数据，去对话页体验 AI 功能吧"
        :image-size="70"
      />
    </el-card>

    <el-card>
      <template #header>按用途类型统计</template>
      <el-table :data="stats?.by_type ?? []" style="width: 100%">
        <el-table-column label="类型" width="200">
          <template #default="{ row }">{{ typeText(row.type) }}</template>
        </el-table-column>
        <el-table-column prop="count" label="调用次数" width="160" />
        <el-table-column prop="total_tokens" label="Token 消耗" />
      </el-table>
      <el-empty
        v-if="!stats?.by_type.length"
        description="暂无数据"
        :image-size="70"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { fetchUsageStats, type UsageStats } from '../api/stats'

echarts.use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const stats = ref<UsageStats | null>(null)
const chartRef = ref<HTMLElement | null>(null)

onMounted(async () => {
  try {
    stats.value = await fetchUsageStats()
    renderChart()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
})

function renderChart() {
  if (!chartRef.value || !stats.value?.daily.length) return
  const chart = echarts.init(chartRef.value)
  const daily = stats.value.daily
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['请求次数', 'Token 消耗'] },
    grid: { left: 50, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: daily.map((d) => d.date.slice(5)) },
    yAxis: [{ type: 'value', name: '次数' }, { type: 'value', name: 'Token' }],
    series: [
      {
        name: '请求次数',
        type: 'line',
        data: daily.map((d) => d.count),
        smooth: true,
      },
      {
        name: 'Token 消耗',
        type: 'line',
        yAxisIndex: 1,
        data: daily.map((d) => d.total_tokens),
        smooth: true,
      },
    ],
  })
  window.addEventListener('resize', () => chart.resize())
}

function typeText(type: string): string {
  const map: Record<string, string> = {
    chat: '普通对话',
    rag: 'RAG 问答',
    agent: 'Agent 对话',
    summary: '文档总结',
  }
  return map[type] ?? type
}
</script>

<style scoped>
.stats-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 20px;
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
/* 内容整组垂直居中 */
.stats-page::before {
  content: '';
  flex-grow: 3.7;
  flex-basis: 0;
  flex-shrink: 0;
}
.stats-page::after {
  content: '';
  flex-grow: 6.3;
  flex-basis: 0;
  flex-shrink: 0;
}
.summary-row {
  margin-bottom: 16px;
}
.page-title {
  text-align: center;
  margin: 0 0 20px;
}
/* 四个指标卡：统一高度 + 框内文字水平垂直居中 */
.summary-row :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 118px;
  padding: 16px 8px;
}
.metric-label {
  font-size: 14.5px;
  color: var(--el-text-color-secondary);
  text-align: center;
}
.metric-value {
  font-size: 27px;
  font-weight: 600;
  text-align: center;
}
.chart-card {
  margin-bottom: 16px;
}
.chart {
  height: 260px;
}
</style>
