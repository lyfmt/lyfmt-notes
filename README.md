# lyfmt's Notes

这是一个 framework-free 的静态多页博客站点。

## 页面结构

- `index.html`：首页卡片流
- `post.html`：文章详情页
- `articles.json`：统一内容源
- `script.js`：运行时渲染首页与详情页
- `styles.css`：共享样式

## 当前内容

当前内置 2 篇示例文章：

- Pi: The Minimal Agent Within OpenClaw
- AI And The Ship of Theseus

## 本地预览

在当前目录启动静态服务器：

```bash
python3 -m http.server 8765
```

然后打开：

- 首页：`http://127.0.0.1:8765/`
- 详情页示例：`http://127.0.0.1:8765/post.html?slug=pi-the-minimal-agent-within-openclaw`

## 说明

- 内容统一来自 `articles.json`
- 支持主题切换
- 详情页通过 `slug` 查询参数选择文章
- 建议通过 HTTP 预览，不要直接双击 HTML 文件
