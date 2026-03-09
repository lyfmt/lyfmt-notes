---
name: rss-hourly-brief
description: Use when running the hourly RSS watcher workflow: scan blogwatcher feeds, detect only new articles since the last checkpoint, fetch representative article bodies, and send a concise Chinese digest.
---

# RSS Hourly Brief

这个 skill 负责“每小时 RSS 巡检 + 增量日报发送”的完整流程。

## 依赖

- BlogWatcher 数据库：`~/.blogwatcher/blogwatcher.db`
- 增量状态脚本：`/home/node/.openclaw/workspace/scripts/rss_hourly_digest_state.py`
- 排版 skill：`/home/node/.openclaw/workspace/skills/article-digest/SKILL.md`

## 工作流

### 1. 先扫描 RSS
使用 blogwatcher 触发一次扫描：

```bash
HOME=/home/node /home/node/.local/bin/blogwatcher scan
```

### 2. 读取本轮新增文章
用状态脚本读取自上次检查以来的新增文章：

```bash
python3 /home/node/.openclaw/workspace/scripts/rss_hourly_digest_state.py new --limit 12
```

### 3. 如果没有新增
直接回复：

```text
NO_REPLY
```

不要发送任何额外说明。

### 4. 如果有新增
按下面规则处理：

- 如果新增 `<= 5` 篇：全部纳入简报
- 如果新增 `> 5` 篇：
  - 精选前 5 篇作为重点
  - 其余作为“其他更新”列标题目
- 选取最多 **3 篇** 去抓正文
- 优先抓：
  - AI / 模型 / agent / infra 方向
  - 来源多样化
  - 标题信息量高的文章

### 5. 抓正文
对选中的文章使用 `web_fetch`，提炼核心结论。
如果正文抓取失败，就只基于标题 + 来源 + 链接做快报，不要编造内容。

### 6. 使用 article-digest 的写法输出
输出目标：

- 中文
- Markdown 分级标题
- 开头先给出总览
- 保留原始链接
- 信息密度高
- 不逐段翻译原文

建议格式：

```markdown
# RSS 小时简报｜{{总标题}}

## 检测结果
- 本轮新增：{{N}} 篇
- 时间：{{当前 UTC 时间}}

## 今日核心
用 2-4 句话总结这批更新最值得看的方向。

## 重点文章 1｜{{标题}}
### 来源
{{来源}}｜{{日期}}

### 核心
1-3 句话

### 要点
- 点 1
- 点 2
- 点 3

### 原始链接
<{{链接}}>

## 重点文章 2｜...

## 其他更新
- {{标题}} — {{来源}}
- {{标题}} — {{来源}}

## 一句话点评
一句话收束。
```

### 7. 成功产出后再推进状态
只有在你已经准备好最终对用户发送的 digest 后，才运行：

```bash
python3 /home/node/.openclaw/workspace/scripts/rss_hourly_digest_state.py commit --through-id <max_new_id>
```

## 严格约束

- **不要**在发送前提前 commit
- **不要**因为没新增而输出解释文字；没新增就是 `NO_REPLY`
- **不要**把旧 backlog 重复发出
- **不要**为所有文章都抓全文，最多抓 3 篇
- **不要**编造未抓到正文的细节
- 如果新增很多，做“精选 + 其他更新”，不要输出超长墙文
