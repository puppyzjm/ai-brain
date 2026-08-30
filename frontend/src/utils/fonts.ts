/**
 * 华为 HarmonyOS Sans SC 字体注入（全量字库，无子集分片缺失问题）。
 * 只引入 Regular(400) 与 Bold(700) 两个字重，其余权重由浏览器就近合成。
 */
import harmonyRegular from '@lobehub/webfont-harmony-sans-sc/fonts/HarmonyOS_Sans_SC_Regular.woff2?url'
import harmonyBold from '@lobehub/webfont-harmony-sans-sc/fonts/HarmonyOS_Sans_SC_Bold.woff2?url'

const style = document.createElement('style')
style.textContent = `
@font-face {
  font-family: 'HarmonyOS Sans SC';
  src: url('${harmonyRegular}') format('woff2');
  font-weight: 100 600;
  font-style: normal;
  font-display: swap;
}
@font-face {
  font-family: 'HarmonyOS Sans SC';
  src: url('${harmonyBold}') format('woff2');
  font-weight: 700 900;
  font-style: normal;
  font-display: swap;
}
`
document.head.appendChild(style)
