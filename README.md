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

## RSS / Blog 导入脚本

当前目录提供了两层导入工具，用来把 RSS / blog 文章按“总结 + 详情”数据模型写入站点。

### 1) 从 spec 直接写入站点

```bash
python3 tools/upsert_post_from_spec.py --spec tools/examples.rss-post-spec.json --articles articles.json
```

如果 spec 中的 `detail.blocks[]` 包含远程图片，并且你希望为 GitHub Pages 本地化资源：

```bash
python3 tools/upsert_post_from_spec.py --spec tools/my-post.json --articles articles.json --localize-media
```

### 2) 从 RSS bundle 生成 spec，再写入站点

```bash
python3 /home/node/.openclaw/workspace/scripts/rss_hourly_brief_bundle.py > /tmp/rss-bundle.json
python3 tools/build_post_spec_from_bundle.py --bundle /tmp/rss-bundle.json --id 2624 --cache-metadata --upsert
```

### 3) 从 source-cache 生成 detail 草稿

```bash
python3 tools/build_detail_from_cache.py --spec tools/generated-specs/how-context-rot-drags-down-ai-and-llm-results-for-enterprises-and-how-to-fix-it.json --cache-html --write-spec
```

说明：
- Markdown 缓存会提取段落、标题、列表、图片、iframe、脚注
- HTML 缓存会优先尝试抽取正文容器，并用 JSON-LD 主图兜底
- 默认生成的是 detail 草稿，不会自动完成中文润色翻译

这个导入流程与 `skills/rss-summary-detail-pages/SKILL.md` 配套。
