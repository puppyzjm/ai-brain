import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import DOMPurify from 'dompurify'
import 'highlight.js/styles/github.css'

const md = new MarkdownIt({
  breaks: true,
  linkify: true,
  highlight(code: string, lang: string): string {
    const highlighted =
      lang && hljs.getLanguage(lang)
        ? hljs.highlight(code, { language: lang }).value
        : hljs.highlightAuto(code).value
    // 代码块右上角复制按钮（点击事件由外层容器事件委托处理）
    return (
      `<div class="code-block"><button type="button" class="copy-btn" title="复制代码">复制</button>` +
      `<pre class="hljs"><code>${highlighted}</code></pre></div>`
    )
  },
})

/** Markdown 渲染 + XSS 白名单过滤（PRD 安全要求）。 */
export function renderMarkdown(text: string): string {
  return DOMPurify.sanitize(md.render(text))
}
