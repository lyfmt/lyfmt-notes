---
name: rss-summary-detail-pages
description: Use when converting RSS/blog items into a static blog entry with two views (summary + detail), extracted media, translated detail blocks, and GitHub Pages-compatible assets using the existing pi-blog-demo style data model.
---

# RSS Summary + Detail Pages

把 RSS / 博客文章加工成 **静态站点文章数据**，而不是只做一次性简报。

目标是把每篇文章变成两层内容：

- **总结（summary）**：保留提炼后的浓缩版
- **详情（detail）**：尽量按原文结构输出中文翻译版，并带上图片 / 媒体 / 注释

这个 skill 默认面向当前工作区里的静态博客项目（如 `pi-blog-demo`），并且**优先保证 GitHub Pages 可托管**。

---

## 什么时候用

当用户要做下面这些事时，使用这个 skill：

- “把 RSS 里的文章放进博客里”
- “做成总结 + 详情两个 tab / 两个视图”
- “保留提炼内容，再加原文翻译详情页”
- “把订阅来的内容沉淀成静态网页”
- “要兼容 GitHub Pages / 纯静态托管”

如果只是做聊天里的简报，而**不落地到网页**，优先使用：

- `skills/article-digest/SKILL.md`
- `skills/rss-hourly-brief/SKILL.md`

如果要把简报进一步沉淀成博客内容，再切换到本 skill。

---

## 核心目标

每篇文章最终都应该落成一个静态可发布的数据项，至少包含：

1. 基础元信息
   - 标题
   - 作者
   - 日期
   - 来源
   - 原文链接
   - 标签

2. 总结视图
   - `excerpt`
   - `content[]`（提炼后的结构化摘要）

3. 详情视图
   - `detail.available`
   - `detail.blocks[]`
   - 媒体（图片 / embed / 注释）
   - 原文来源说明

4. 静态站点兼容性
   - 页面发布后不依赖服务端
   - 不要求运行时再去抓原文
   - 尽量不依赖根路径 `/...`

---

## GitHub Pages 约束（非常重要）

如果目标是 GitHub Pages，必须按下面规则做：

### 1) 所有核心内容都要在构建/更新时落盘
不要把“详情内容抓取”“正文翻译”“媒体提取”留到浏览器运行时。

GitHub Pages 只是静态托管：

- 没有后端
- 不能运行抓取器
- 不适合运行需要私钥/API 的实时处理

所以：

- **摘要内容**要提前写进 JSON / 静态文件
- **详情内容**也要提前写进 JSON / 静态文件
- **媒体地址**要提前确定

### 2) 优先使用相对路径
GitHub Pages 经常挂在子路径下，例如：

- `https://user.github.io/repo-name/`

所以不要默认写：

- `/assets/...`
- `/post.html?...`

优先写：

- `./assets/...`
- `./post.html?...`

### 3) 图片优先本地化
如果图片对文章表达很重要，优先下载到仓库里，例如：

```text
assets/posts/<slug>/image-01.png
```

然后在详情数据里引用相对路径，而不是长期热链外站。

原因：

- 避免热链失效
- 避免源站防盗链
- 避免未来外链变更
- GitHub Pages 对静态图片托管没问题

### 4) 外部 embed 允许，但要谨慎
像 YouTube iframe 这类稳定 provider 可以保留。

但要注意：

- embed 只是增强，不应成为正文唯一承载方式
- 如果 embed 失效，页面正文仍应可读

### 5) 不依赖运行时跨域抓取
浏览器端直接抓外站正文，常见问题：

- CORS
- 限流
- 防 bot
- 页面结构变化

所以 detail 内容一定要**预处理后写入本地数据**。

---

## 当前默认模板（与现有 pi-blog-demo 对齐）

默认沿用当前站点的数据模型：

```json
{
  "site": {
    "title": "lyfmt's Notes",
    "description": "..."
  },
  "posts": [
    {
      "slug": "post-slug",
      "title": "Article Title",
      "author": "Author Name",
      "publishedAt": "2026-03-09",
      "source": "Source Name",
      "url": "https://example.com/original",
      "tags": ["AI", "Agents"],
      "excerpt": "首页摘要",
      "content": [
        {
          "heading": "文章核心",
          "paragraphs": [
            "总结段落 1",
            "总结段落 2"
          ]
        }
      ],
      "detail": {
        "available": true,
        "layout": "source-style-name",
        "translatedFrom": "https://example.com/original.md",
        "sourceName": "Original Site Name",
        "sourceDescription": "以下为原文结构对应的中文翻译版。",
        "blocks": [
          { "type": "paragraph", "html": "<strong>段落</strong>..." },
          { "type": "heading", "level": 2, "text": "小节标题" },
          { "type": "list", "items": ["点 1", "点 2"] },
          { "type": "image", "src": "./assets/posts/post-slug/figure-01.png", "alt": "...", "caption": "..." },
          { "type": "embed", "provider": "youtube", "src": "https://www.youtube.com/embed/...", "title": "..." },
          { "type": "footnote", "html": "<a href=\"...\">注释</a>" }
        ]
      }
    }
  ]
}
```

### 关键约定

- `excerpt`：首页卡片摘要
- `content[]`：总结视图正文
- `detail`：详情视图正文
- `detail.available = false`：表示当前文章只有总结，没有详情

如果未来站点改成一文一 JSON，也可以继续沿用这套字段，只是拆文件而已。

---

## 推荐目录结构

以当前工作区为例，推荐：

```text
pi-blog-demo/
  index.html
  post.html
  script.js
  styles.css
  articles.json
  assets/
    posts/
      <slug>/
        image-01.png
        image-02.jpg
        cover.png
  source-cache/
    <slug>.html
    <slug>.md
  tools/
    update_*.py
```

### 目录含义

- `articles.json`：站点主数据
- `assets/posts/<slug>/`：本地化媒体资源
- `source-cache/`：原始抓取缓存，便于复查和重生成
- `tools/`：一次性或可重复执行的更新脚本

---

## 工作流

### 第 1 步：确定输入文章
输入来源通常有两类：

1. RSS 简报筛出来的重点文章
2. 用户点名要落地的原文链接

先确定：

- 标题
- 原文链接
- 来源
- 日期
- 作者（如果能取到）
- 标签（可人工归类）

### 第 2 步：抓取最适合加工的原文版本
优先级如下：

1. 站点官方 markdown 版本（如果有）
2. RSS feed 中的完整/半完整 HTML 内容
3. 原始 HTML 页面正文
4. 退化为标题 + 摘要 + 链接

优先选择**最稳定、最干净**的输入，而不是最复杂的输入。

#### 建议
- 有 `.md` 就优先抓 `.md`
- 有 feed 正文就优先用 feed 正文
- HTML 只在必要时解析

### 第 3 步：生成总结视图
总结视图不是翻译稿，而是提炼稿。

要求：

- 中文
- 信息密度高
- 2-4 个信息块即可
- 可直接用于首页/卡片点击后的“总结”模式

推荐结构：

```json
"content": [
  {
    "heading": "文章核心",
    "paragraphs": [
      "...",
      "..."
    ]
  },
  {
    "heading": "值得关注的点",
    "paragraphs": [
      "...",
      "..."
    ]
  }
]
```

### 第 4 步：生成详情视图
详情视图目标：

- 尽量保留原文结构
- 不是一句话摘要
- 也不是胡乱拼接整篇原文
- 是**更接近原 blog 阅读体验**的中文版本

#### detail.blocks 推荐块类型

##### `paragraph`
用于普通段落。

```json
{ "type": "paragraph", "html": "这里可以包含安全的链接、code、strong、em。" }
```

##### `heading`
用于章节标题。

```json
{ "type": "heading", "level": 2, "text": "What is Pi?" }
```

##### `list`
用于原文 bullet points。

```json
{ "type": "list", "items": ["点 1", "点 2"] }
```

##### `image`
用于正文图片。

```json
{ "type": "image", "src": "./assets/posts/pi/figure-01.png", "alt": "...", "caption": "..." }
```

##### `embed`
用于稳定外部媒体（如 YouTube）。

```json
{ "type": "embed", "provider": "youtube", "src": "https://www.youtube.com/embed/...", "title": "..." }
```

##### `footnote`
用于脚注/尾注。

```json
{ "type": "footnote", "html": "<a href=\"...\">注 1</a>" }
```

### 第 5 步：处理图片和媒体
#### 图片处理优先级

1. **优先下载到本地**并改成相对路径
2. 实在不方便再保留绝对 URL

#### 图片命名建议

```text
assets/posts/<slug>/figure-01.png
assets/posts/<slug>/figure-02.jpg
assets/posts/<slug>/cover.png
```

#### 媒体处理规则

- 正文表达需要的图片：尽量保留
- 装饰性图片：可省略
- 视频：优先保留 embed
- 社交分享图：只有在确实有展示价值时才保留

### 第 6 步：写回站点数据
更新时：

- **追加新文章**，不要破坏已有结构
- 尽量保持字段顺序稳定
- 不要让已有 slug 失效

如果是已有文章补 detail：

- 保留原 `excerpt` / `content`
- 只补 `detail`

当前工作区已经提供了两层脚本：

#### A. 单篇 spec 写回站点

```bash
cd /home/node/.openclaw/workspace/pi-blog-demo
python3 tools/upsert_post_from_spec.py \
  --spec tools/examples.rss-post-spec.json \
  --articles articles.json
```

如果 detail 里有远程图片，并且你希望为 GitHub Pages 本地化媒体：

```bash
python3 tools/upsert_post_from_spec.py \
  --spec tools/my-post.json \
  --articles articles.json \
  --localize-media
```

#### B. 从 RSS bundle 直接生成 spec

先跑 bundle：

```bash
python3 /home/node/.openclaw/workspace/scripts/rss_hourly_brief_bundle.py > /tmp/rss-bundle.json
```

再把某一条变成站点 spec：

```bash
cd /home/node/.openclaw/workspace/pi-blog-demo
python3 tools/build_post_spec_from_bundle.py \
  --bundle /tmp/rss-bundle.json \
  --id 2624 \
  --cache-metadata
```

如果要一口气生成并写进站点：

```bash
python3 tools/build_post_spec_from_bundle.py \
  --bundle /tmp/rss-bundle.json \
  --id 2624 \
  --cache-metadata \
  --upsert
```

约定：

- 输入 spec 是一个 JSON 对象，描述单篇文章
- `upsert_post_from_spec.py` 会按 `slug` 更新已存在文章，否则插入新文章
- `--localize-media` 目前会处理 `detail.blocks[]` 里的 `image` 块
- 资源默认落到 `assets/posts/<slug>/`
- `build_post_spec_from_bundle.py` 默认从 bundle 的 `focus_items` 生成 spec
- `--cache-metadata` 会把条目元数据和 probe 信息写到 `source-cache/<slug>.metadata.json`
- `--cache-html` 会尝试缓存原始 HTML 到 `source-cache/<slug>.html`

#### C. 从 source-cache 生成 detail 草稿

如果已经有 `source-cache/<slug>.md` 或 `.html`，可以直接生成 `detail.blocks[]` 草稿：

```bash
cd /home/node/.openclaw/workspace/pi-blog-demo
python3 tools/build_detail_from_cache.py \
  --spec tools/generated-specs/how-context-rot-drags-down-ai-and-llm-results-for-enterprises-and-how-to-fix-it.json \
  --cache-html
```

如果希望把 detail 草稿直接写回 spec：

```bash
python3 tools/build_detail_from_cache.py \
  --spec tools/generated-specs/how-context-rot-drags-down-ai-and-llm-results-for-enterprises-and-how-to-fix-it.json \
  --cache-html \
  --write-spec
```

如果希望直接开放详情模式：

```bash
python3 tools/build_detail_from_cache.py \
  --spec tools/generated-specs/how-context-rot-drags-down-ai-and-llm-results-for-enterprises-and-how-to-fix-it.json \
  --cache-html \
  --write-spec \
  --enable-detail
```

约定补充：

- `build_detail_from_cache.py` 目前支持 `.md`、`.html`
- 能提取：标题层级、段落、列表、图片、iframe、脚注
- HTML 路径会优先尝试正文容器抽取，并用 JSON-LD 主图做兜底
- 这是 **详情草稿生成器**，默认不会自动翻译润色整篇中文
- `refine_detail_to_chinese.py` 可把英文 `detail.blocks[]` 改写成中文“细读版”详情结构
- 在当前环境下，`pi` 更适合按小批量 block 分段跑；推荐结合 `--resume-untranslated` / `--limit` / `--continue-on-error`
- 推荐流程：先生成草稿，再生成中文 detail；只有确认可发布时再 `--enable-detail`

### 第 7 步：本地验证
至少做这些检查：

```bash
node --check script.js
python3 -m json.tool articles.json >/dev/null
python3 tools/validate_articles.py --articles articles.json --pretty
python3 tests/run_tests.py
python3 -m http.server 8766
curl 'http://127.0.0.1:8766/post.html?slug=<slug>'
curl 'http://127.0.0.1:8766/post.html?slug=<slug>&view=detail'
```

如果项目是多页静态站，还要确认：

- 首页卡片正常
- 总结/详情切换正常
- 相关文章链接正常
- 上一篇/下一篇正常
- 相对路径在子目录托管下也正常

### 第 8 步：提交变更
完成后应提交 git：

- 站点数据
- 样式/模板改动
- 新增资产
- 生成脚本（如果值得保留）

---

## 写作与翻译规则

### 总结视图
- 不逐段翻译
- 先提炼，再组织
- 保留关键事实和判断
- 用中文表达，但不要擅自扩写

**总结写法固定格式（必须遵守）：**
1. 标题：中文对文章内容的一句话总结
2. 内容分类：内容的相关领域
3. 内容总结：总结文章内容

**禁止出现“rss”字样**（任何大小写形式都不允许出现在总结里）

### 详情视图
- **必须一比一逐段翻译**，保持原文句序与信息密度
- **禁止改写/意译/扩写/删改**，不得加入原文没有的信息
- 链接、代码名、产品名、项目名保持原文（不要随意译名）

### 不确定时
- 抓不到完整正文：`detail.available = false`
- 图片拿不到：宁可缺图，也不要编造图注
- 某段含义不明：宁可保守翻译，不要脑补

---

## 严格约束

- **不要**把 detail 生成依赖到浏览器运行时
- **不要**假设 GitHub Pages 能跑后端逻辑
- **不要**使用根路径 `/...` 作为默认链接策略
- **不要**编造原文没有的段落、图片、作者观点
- **不要**在没有正文的情况下伪造“逐段翻译详情”
- **不要**为了“像原站”而把原站 CSS 整份硬拷进来
- **不要**牺牲站点可维护性去追求像素级复刻

---

## GitHub Pages 结论

**可以做，而且很适合做。**

前提是：

- 把 RSS 到 summary/detail 的加工放在**发布前**完成
- 页面只消费静态 JSON / 静态资源
- 图片尽量本地化
- 链接全部用相对路径思维处理

换句话说：

- **GitHub Pages 不适合“实时抓文章再渲染”**
- **GitHub Pages 很适合“预先加工好内容，再静态发布”**

本 skill 就是按这个前提设计的。

---

## 推荐默认行为

当用户说：

- “把这篇 RSS 放进博客”
- “给它做 summary/detail 双视图”
- “详情按原文翻译、图片一起带上”
- “兼容 GitHub Pages”

默认执行策略：

1. 先做 `excerpt + content[]`
2. 再判断能否做 `detail`
3. 能做则补 `detail.blocks[]`
4. 能本地化媒体则本地化
5. 更新静态数据
6. 本地验证
7. git commit

如果 detail 不足够完整，就保留：

```json
"detail": { "available": false }
```

而不是凑假内容。

### RSS autopublish 强制规则（新增）

- **strict publish 模式下，只允许提交/推送 `published` 结果**。
- 若本轮无 `published`，则必须跳过 git commit/push（避免 draft-only 被推送）。
- `draft_only/blocked` 允许落地到本地工作区供后续补全，但不得推送到远端。

---

## 针对当前工作区的补充约定（RSS autopublish）

当前这个工作区里，RSS autopublish 已经在往“单一稳态脚本入口”收敛，推荐优先调用：

```bash
cd /home/node/.openclaw/workspace/pi-blog-demo
./run-rss-autopublish.sh
```

### 现在的本地稳态入口特性

- 保持 **单批次、顺序处理**；不要引入每篇并发/subagent
- 继续把 `scripts/rss_hourly_brief_bundle.py` 作为 scan/new/probe 的单一真相来源
- 每轮 run 会把 ledger 写到：
  - `/home/node/.openclaw/workspace/.openclaw/runtime/rss-autopublish/runs/`
  - `/home/node/.openclaw/workspace/.openclaw/runtime/rss-autopublish/items/`
- 只有当整批 item 都达到 terminal outcomes 且 `articles.json` 校验通过时，才推进 RSS checkpoint
- 对 challenge / Cloudflare 页面会显式降级成 blocked draft，避免 `Just a moment...` 污染 slug/title
- upsert 会优先保留更丰富的 detail，降低 rerun 把成品覆盖回半成品的风险

### 推荐排查顺序

1. 先看 `runs/<run_id>.json` 的 batch 结果
2. 再看 `items/<article_id>.json` 的 stage history / attempts
3. 如果要重放，用：

```bash
python3 tools/replay_bundle_to_specs.py --bundle /path/to/saved-bundle.json
```

4. 如果要做发布前短路，先跑：

```bash
python3 tools/validate_articles.py --articles articles.json --pretty
```

这样做的目标是：即使留下半成品，也要留下明确 journal，而不是静默吞 checkpoint。
