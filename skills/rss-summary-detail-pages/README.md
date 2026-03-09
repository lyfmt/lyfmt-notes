# RSS Summary + Detail Pages

这个 skill 用来把 RSS / 博客文章沉淀成静态博客内容，而不是只做聊天简报。

## 产出目标

每篇文章有两个视图：

- Summary：提炼后的总结版
- Detail：更接近原文结构的中文详情版

并且适配：

- 静态 JSON 数据源
- 相对路径链接
- 本地化图片资源
- GitHub Pages 托管

## 适用项目

当前默认面向：

- `pi-blog-demo`
- 其他同类静态博客项目

## 核心原则

1. 详情内容必须预处理，不依赖浏览器运行时抓取
2. 图片优先本地化到仓库
3. 链接优先使用相对路径
4. 总结与详情共享同一篇文章数据
5. detail 不完整时宁可关闭，不伪造内容

## 推荐字段

见 `SKILL.md` 里的完整 JSON 模型说明。

## 最小工作流

1. 选定 RSS 文章
2. 抓取 markdown / feed / html 正文
3. 生成 summary
4. 生成 detail
5. 本地化媒体
6. 写回 `articles.json`
7. 本地预览验证
8. git commit
