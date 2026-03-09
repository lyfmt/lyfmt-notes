# Pi Blog Demo

这是一个 framework-free 的静态多文章博客首页 demo。

## 内容来源

- 运行时内容来自 `articles.json`
- 当前内置 2 篇示例文章
- 页面通过 `script.js` 动态渲染文章列表与文章详情

## 本地预览

在当前目录启动本地静态服务器：

```bash
python3 -m http.server 8765
```

然后打开：

```
http://127.0.0.1:8765/
```

## 说明

- 建议通过 HTTP 预览，不要直接双击 `index.html`
- 支持主题切换
- 支持通过 URL hash 选择文章，例如 `#pi-the-minimal-agent-within-openclaw`
