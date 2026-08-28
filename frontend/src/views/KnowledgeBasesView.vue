<template>
  <div class="kb-page">
    <div class="kb-header">
      <h2>知识库</h2>
      <el-button type="primary" @click="openCreate">+ 新建知识库</el-button>
    </div>

    <el-card v-for="kb in kbs" :key="kb.id" class="kb-card" shadow="hover">
      <div class="kb-row">
        <div class="kb-info" @click="$router.push(`/knowledge-bases/${kb.id}`)">
          <div class="kb-name">{{ kb.name }}</div>
          <div class="kb-desc">{{ kb.description || '暂无描述' }}</div>
        </div>
        <div class="kb-actions">
          <el-button size="small" @click="$router.push(`/knowledge-bases/${kb.id}`)">
            管理文档
          </el-button>
          <el-button size="small" @click="openEdit(kb)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(kb)">删除</el-button>
        </div>
      </div>
    </el-card>

    <el-empty v-if="!kbs.length" description="暂无知识库，点击右上角新建" />

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑知识库' : '新建知识库'" width="420px">
      <el-form label-position="top">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="知识库名称" />
        </el-form-item>
        <el-form-item label="描述（可选）">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  listKnowledgeBases,
  updateKnowledgeBase,
  type KnowledgeBase,
} from '../api/knowledgeBase'

const kbs = ref<KnowledgeBase[]>([])
const dialogVisible = ref(false)
const editing = ref<KnowledgeBase | null>(null)
const form = reactive({ name: '', description: '' })

onMounted(load)

async function load() {
  try {
    kbs.value = await listKnowledgeBases()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

function openCreate() {
  editing.value = null
  form.name = ''
  form.description = ''
  dialogVisible.value = true
}

function openEdit(kb: KnowledgeBase) {
  editing.value = kb
  form.name = kb.name
  form.description = kb.description ?? ''
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  try {
    if (editing.value) {
      await updateKnowledgeBase(editing.value.id, form.name.trim(), form.description.trim())
      ElMessage.success('已保存')
    } else {
      await createKnowledgeBase(form.name.trim(), form.description.trim())
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    load()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function handleDelete(kb: KnowledgeBase) {
  try {
    await ElMessageBox.confirm(`确定删除知识库「${kb.name}」？其中的文档与向量将一并删除。`, '删除', {
      type: 'warning',
    })
    await deleteKnowledgeBase(kb.id)
    ElMessage.success('已删除')
    load()
  } catch {
    /* 用户取消 */
  }
}
</script>

<style scoped>
.kb-page {
  max-width: 860px;
  margin: 0 auto;
}
.kb-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.kb-card {
  margin-bottom: 12px;
  cursor: default;
}
.kb-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.kb-info {
  flex: 1;
  cursor: pointer;
}
.kb-name {
  font-size: 15px;
  font-weight: 600;
}
.kb-desc {
  font-size: 13px;
  color: #999;
  margin-top: 4px;
}
</style>
