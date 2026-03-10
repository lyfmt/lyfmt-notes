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
python3 /home/node/.openclaw/workspace/scripts/rss_hourly_brief_bundle.py --state-limit 0 > /tmp/rss-bundle.json
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
- 如果缓存内容本身是 Cloudflare / challenge 页面，现在会显式写成 blocked draft，而不会误生成可发布 detail

### 4) 把英文 detail 草稿改写成中文细读版

```bash
python3 tools/refine_detail_to_chinese.py --spec tools/generated-specs/how-context-rot-drags-down-ai-and-llm-results-for-enterprises-and-how-to-fix-it.json --write-spec --enable-detail
```

说明：
- 输入是已有的 `detail.blocks[]` 草稿
- 输出是中文“细读/改写”版 detail，而不是逐字镜像翻译
- 默认保留原有结构、图片、embed 与链接
- 建议先小范围试跑：`--limit 3`
- 在当前环境下，更稳的方式是分段跑，并开启 `--continue-on-error`

示例：
```bash
python3 tools/refine_detail_to_chinese.py \
  --spec tools/generated-specs/how-context-rot-drags-down-ai-and-llm-results-for-enterprises-and-how-to-fix-it.json \
  --resume-untranslated \
  --limit 3 \
  --continue-on-error
```

## 新的稳态 orchestrator 入口

现在推荐把 cron / 定时任务改成调用单一入口，而不是手工串联多段命令：

```bash
./run-rss-autopublish.sh
```

它会调用：

- `scripts/rss_hourly_brief_bundle.py` 作为 scan/new/probe 的单一真相来源
- `tools/build_post_spec_from_bundle.py`
- `tools/build_detail_from_cache.py`
- `tools/refine_detail_to_chinese.py`
- `tools/upsert_post_from_spec.py`
- `tools/validate_articles.py`
- `scripts/rss_hourly_digest_state.py commit`

### Orchestrator 当前保证

- 单批次、顺序处理；不引入每篇并发/subagent
- 把每轮执行写入 `.openclaw/runtime/rss-autopublish/`
  - `runs/<run_id>.json`
  - `items/<article_id>.json`
  - `current-run.json`
  - `latest-run.json`
- 每篇条目有明确 terminal outcome：
  - `published`
  - `draft_only`
  - `blocked`
  - `skipped_existing`
  - `failed`
- 只有当整批 item 都达到 terminal outcome，且 `articles.json` 静态校验通过后，才提交 RSS checkpoint
- 如果某篇只是留下 draft / blocked detail，不会静默吞 checkpoint 语义；状态会落进 item journal / run ledger
- 对 Cloudflare / challenge 页面做显式降级，避免 `Just a moment...` 这类标题污染 slug
- upsert 会优先保留更丰富的已存在 detail，避免后续部分 rerun 把更完整的 detail 覆盖回半成品

### 常用参数

```bash
python3 tools/rss_autopublish_orchestrator.py --max-items 2 --pi-limit 1 --pi-timeout 60 --dry-run
```

```bash
python3 tools/rss_autopublish_orchestrator.py --bundle-file /path/to/saved-bundle.json --dry-run
```

说明：
- `--dry-run`：跑完整编排和 journaling，但不做 validation/checkpoint/git 收尾
- `--bundle-file`：用保存下来的 bundle 做回放/调试
- `--max-items`：限制本轮处理多少条
- `--pi-limit`：每次只翻译多少个 detail block，降低本地 `pi` 挂住风险

## Replay / 测试 / 校验

### Replay 旧 bundle

```bash
python3 tools/replay_bundle_to_specs.py --bundle /tmp/rss-bundle.json --ids 2629 2630
```

### 校验站点数据

```bash
python3 tools/validate_articles.py --articles articles.json --pretty
```

当前会检查：
- 必填字段缺失
- 重复 slug
- 可疑标题
- `just-a-moment` 这类污染 slug
- `detail.blocks` 结构错误

### 跑最小本地测试

这个环境未必有 `pytest`，所以附带了一个无依赖 runner：

```bash
python3 tests/run_tests.py
```

## 当前已知限制

- 本地 `pi` 仍可能在长块翻译时挂住；当前策略是小批量 + checkpoint + `continue-on-error`
- orchestrator 目前把 `failed` 也视为 terminal outcome，以便 run ledger 可收敛；但只有整批都 terminal 且静态校验通过时才会推进 checkpoint
- `--dry-run` 仍会执行中间生成步骤，因此更适合“本地烟测/回放”，不是纯只读模式
- 远端 `git push` 仍默认关闭，避免把未审阅内容直接推出去

这个导入流程与 `skills/rss-summary-detail-pages/SKILL.md` 配套。
