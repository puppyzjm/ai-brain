<template>
  <div class="task-page">
    <div class="task-header">
      <h2>任务</h2>
      <el-button type="primary" @click="openCreate">+ 新建任务</el-button>
    </div>

    <div class="filters">
      <el-select v-model="filterStatus" clearable placeholder="按状态筛选" style="width: 160px">
        <el-option label="待办" value="todo" />
        <el-option label="进行中" value="in_progress" />
        <el-option label="已完成" value="done" />
      </el-select>
      <el-select v-model="filterPriority" clearable placeholder="按优先级筛选" style="width: 160px">
        <el-option label="高" value="high" />
        <el-option label="中" value="medium" />
        <el-option label="低" value="low" />
      </el-select>
    </div>

    <el-card v-for="t in tasks" :key="t.id" class="task-card" shadow="hover">
      <div class="task-row">
        <el-checkbox
          :model-value="t.status === 'done'"
          @change="(val: unknown) => handleToggle(t, Boolean(val))"
        />
        <div class="task-info">
          <div class="task-title" :class="{ done: t.status === 'done' }">{{ t.title }}</div>
          <div class="task-meta">
            <el-tag size="small" :type="priorityType(t.priority)">{{ priorityText(t.priority) }}</el-tag>
            <span v-if="t.due_date" class="task-due">截止 {{ t.due_date }}</span>
            <span class="task-desc">{{ t.description || '' }}</span>
          </div>
        </div>
        <div class="task-actions">
          <el-button
            v-if="t.status !== 'done'"
            size="small"
            @click="handleStatus(t, 'in_progress')"
          >
            开始
          </el-button>
          <el-button size="small" type="danger" @click="handleDelete(t)">删除</el-button>
        </div>
      </div>
    </el-card>

    <el-empty v-if="!tasks.length" description="暂无任务" />

    <el-dialog v-model="dialogVisible" title="新建任务" width="420px">
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="任务标题" />
        </el-form-item>
        <el-form-item label="描述（可选）">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.priority" style="width: 100%">
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createTask,
  deleteTask,
  listTasks,
  updateTask,
  type Task,
  type TaskPriority,
  type TaskStatus,
} from '../api/task'

const tasks = ref<Task[]>([])
const filterStatus = ref<TaskStatus | ''>('')
const filterPriority = ref<TaskPriority | ''>('')
const dialogVisible = ref(false)
const form = reactive({ title: '', description: '', priority: 'medium' as TaskPriority })

onMounted(load)
watch([filterStatus, filterPriority], load)

async function load() {
  try {
    tasks.value = await listTasks({
      status: filterStatus.value || undefined,
      priority: filterPriority.value || undefined,
    })
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

function openCreate() {
  form.title = ''
  form.description = ''
  form.priority = 'medium'
  dialogVisible.value = true
}

async function handleCreate() {
  if (!form.title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  try {
    await createTask({
      title: form.title.trim(),
      description: form.description.trim() || undefined,
      priority: form.priority,
    })
    ElMessage.success('已创建')
    dialogVisible.value = false
    load()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function handleToggle(t: Task, checked: boolean) {
  await handleStatus(t, checked ? 'done' : 'todo')
}

async function handleStatus(t: Task, status: TaskStatus) {
  try {
    await updateTask(t.id, { status })
    load()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function handleDelete(t: Task) {
  try {
    await ElMessageBox.confirm(`确定删除「${t.title}」？`, '删除', { type: 'warning' })
    await deleteTask(t.id)
    ElMessage.success('已删除')
    load()
  } catch {
    /* 用户取消 */
  }
}

function priorityType(p: TaskPriority): 'danger' | 'warning' | 'info' {
  if (p === 'high') return 'danger'
  if (p === 'medium') return 'warning'
  return 'info'
}

function priorityText(p: TaskPriority): string {
  return { high: '高优先级', medium: '中优先级', low: '低优先级' }[p] ?? p
}
</script>

<style scoped>
.task-page {
  max-width: 720px;
  margin: 0 auto;
  padding: 24px 20px;
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
/* 内容整组垂直居中 */
.task-page::before {
  content: '';
  flex-grow: 3.7;
  flex-basis: 0;
  flex-shrink: 0;
}
.task-page::after {
  content: '';
  flex-grow: 6.3;
  flex-basis: 0;
  flex-shrink: 0;
}
.task-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.task-card {
  margin-bottom: 10px;
}
.task-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.task-info {
  flex: 1;
}
.task-title {
  font-size: 14px;
  font-weight: 600;
}
.task-title.done {
  text-decoration: line-through;
  color: var(--el-text-color-secondary);
}
.task-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.task-actions {
  display: flex;
  gap: 6px;
}
</style>
