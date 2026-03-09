import json
from pathlib import Path

root = Path('/home/node/.openclaw/workspace/pi-blog-demo')
path = root / 'articles.json'
data = json.loads(path.read_text(encoding='utf-8'))

pi_detail = {
    'layout': 'lucumr',
    'available': True,
    'translatedFrom': 'https://lucumr.pocoo.org/2026/1/31/pi.md',
    'sourceName': "Armin Ronacher's Thoughts and Writings",
    'sourceDescription': '以下为原文结构对应的中文翻译版，尽量保留原作者行文节奏、段落顺序、图片与嵌入内容。',
    'blocks': [
        {'type': 'paragraph', 'html': '如果你这周不是与世隔绝，大概已经注意到我朋友 Peter 的一个项目在互联网上火了起来。它有过很多名字；最近更常见的名字是 <a href="https://openclaw.ai/" target="_blank" rel="noreferrer noopener">OpenClaw</a>，不过如果你是在不同时间点看到相关消息，也可能见过它被叫作 ClawdBot 或 MoltBot。它本质上是一个接到你所选通信渠道上的 agent，会去<a href="https://lucumr.pocoo.org/2025/7/3/tools/" target="_blank" rel="noreferrer noopener">直接跑代码</a>。'},
        {'type': 'paragraph', 'html': '但你未必知道的是，OpenClaw 底下真正跑着的，是一个叫 <a href="https://github.com/badlogic/pi-mono/" target="_blank" rel="noreferrer noopener">Pi</a> 的小型 coding agent。而在目前这个阶段，Pi 几乎已经成了我唯一在用的 coding agent。过去几周里，我对这个小 agent 越来越像布道者。前阵子我刚做过一次相关分享，后来才意识到：我居然还没在博客里正式写过 Pi。所以这篇文章想补上这个背景——为什么我对它这么着迷，以及它和 OpenClaw 到底是什么关系。'},
        {'type': 'paragraph', 'html': 'Pi 的作者是 <a href="https://mariozechner.at/" target="_blank" rel="noreferrer noopener">Mario Zechner</a>。和 Peter 那种“带一点疯狂感的科幻”路线不同，Mario 非常务实。尽管两人的风格差异很大，OpenClaw 和 Pi 其实遵循的是同一个判断：LLM 特别擅长写代码、跑代码，那就应该顺势而为。从某种意义上说，这也不算偶然，因为正是 Peter 在去年把我和 Mario 一起拉进了这套思路，以及 agent 这件事本身。'},
        {'type': 'heading', 'level': 2, 'text': '什么是 Pi？'},
        {'type': 'paragraph', 'html': 'Pi 是一个 coding agent。而如今的 coding agent 已经很多了。说实话，现在你随便挑一个现成产品，基本都能体验到所谓 agentic programming 是什么感觉。我之前在博客里对 AMP 的评价就挺正面，其中一个原因是：它确实像是由一群既沉迷 agentic programming、又真的试过很多不同路线的人做出来的产品，而不只是给现成能力套了一层花哨 UI。'},
        {'type': 'paragraph', 'html': 'Pi 之所以让我特别感兴趣，主要有两个原因：'},
        {'type': 'list', 'items': [
            '第一，它的核心极小。它的 system prompt 是我见过所有 agent 里最短的之一，而且默认只带四个工具：Read、Write、Edit、Bash。',
            '第二，它用扩展系统来弥补这个极小核心；更重要的是，这个扩展系统允许扩展把状态持久化进 session，这一点威力非常大。'
        ]},
        {'type': 'paragraph', 'html': '另外还有个加分项：Pi 本身是一份写得非常漂亮的软件。它不会闪烁，不怎么吃内存，不会莫名其妙坏掉，非常稳定，而且你能明显感觉到作者对每一项进入软件的东西都很克制。'},
        {'type': 'paragraph', 'html': 'Pi 还不只是一个 CLI，它本身就是一组小组件，你可以在它上面拼出自己的 agent。OpenClaw 就是这么搭出来的；我自己的 Telegram bot 是这么搭的；Mario 的 <a href="https://github.com/badlogic/pi-mono/tree/main/packages/mom" target="_blank" rel="noreferrer noopener">mom</a> 也是这么来的。如果你想做一个能连上某个外部系统的 agent，把 Pi 指向它自己，再配上 mom，它就能帮你把那个 agent 变出来。'},
        {'type': 'heading', 'level': 2, 'text': 'Pi 里刻意没有什么'},
        {'type': 'paragraph', 'html': '想理解 Pi 里有什么，反而更重要的是先理解 Pi 里没有什么、为什么没有、以及更关键的一点：为什么它以后大概率也不会加进去。最明显的缺失就是 MCP 支持。Pi 里没有内建 MCP。你当然可以自己写扩展去接；或者像 OpenClaw 一样，直接用 <a href="https://github.com/steipete/mcporter" target="_blank" rel="noreferrer noopener">mcporter</a> 来做。mcporter 会把 MCP 调用通过 CLI 或 TypeScript 绑定暴露出来，至于 agent 最后能不能把这套能力用好，那就另当别论了。'},
        {'type': 'paragraph', 'html': '而这不是偷懒造成的缺失，而是 Pi 工作哲学的一部分。Pi 的核心想法是：如果 agent 现在还不会做某件事，你不应该第一反应是去下载一个扩展、一个 skill 或类似的东西；你应该让 agent 自己扩展自己。Pi 推崇的是“写代码，再运行代码”这套路径。'},
        {'type': 'paragraph', 'html': '这当然不意味着你不能下载扩展。Pi 明确支持这么做。但它并不天然鼓励你去拿别人现成的能力；相反，你也可以直接指给 agent 看一个已有扩展，然后说：照着这个做，但把这里和这里改成我想要的样子。'},
        {'type': 'heading', 'level': 2, 'text': '为“让 agent 构建 agent”而设计的 agent'},
        {'type': 'paragraph', 'html': '如果你去看 Pi，以及由它延伸出来的 OpenClaw，到底在做什么，你会看到一种像泥巴一样可塑的软件形态。而这种形态，会直接反过来要求底层架构必须满足一些条件；换句话说，它迫使某些约束在系统最核心的设计层就被考虑进去。'},
        {'type': 'paragraph', 'html': '举个例子，Pi 底层的 AI SDK 被设计成：一个 session 里真的可以混杂来自多个不同模型提供商的消息。它承认 session 在不同模型提供商之间并不能完全无损迁移，所以它不会过度押注那些无法跨模型迁移的 provider 专属能力。'},
        {'type': 'paragraph', 'html': '另一个关键点是，除了模型消息本身，Pi 还会在 session 文件中维护自定义消息。这些消息可以被扩展拿来存状态，也可以被系统自己拿来记录一些信息——这些信息要么完全不会发给 AI，要么只会把其中一部分发进去。'},
        {'type': 'paragraph', 'html': '正因为有了这套机制，扩展状态也能落盘持久化，所以它内建了 hot reloading：agent 可以自己写代码、重载、测试，然后不断循环，直到扩展真的可用为止。它还自带文档和示例，而这些文档和示例本身又能被 agent 拿来继续扩展自己。更妙的是：Pi 的 session 不是线性的，而是树状的。你可以在 session 里分支、跳转，这带来很多有意思的工作流——比如开一个旁支去修一个坏掉的 agent 工具，而不必把主 session 的上下文浪费掉。工具修好后，我可以回退到早先的节点，让 Pi 对另一条分支上发生的事做个总结。'},
        {'type': 'paragraph', 'html': '这些设计之所以重要，是因为以 MCP 为例：在大多数模型提供商那里，MCP 工具和其他 LLM 工具一样，需要在 session 启动时就载入到 system context 或对应的 tool 区块里。这样一来，你几乎很难在不中断整个缓存、或者不把模型搞糊涂的前提下，真正热重载某个工具的行为。'},
        {'type': 'heading', 'level': 2, 'text': '上下文之外的工具'},
        {'type': 'paragraph', 'html': 'Pi 里的扩展可以注册工具，让 LLM 直接调用。有时候我确实觉得这很有用。比如尽管我一直在吐槽 Beads 的实现方式，但我仍然认为，让 agent 拥有一个待办列表，是非常有价值的。我自己就让 agent 给我造过一个本地运行的 issue tracker。因为我希望它也能管理 to-do，所以这个场景里我最终给了它一个工具，而不是一个 CLI。对于这个问题范围来说，这样做很合适；而这也是目前我唯一一个额外放进上下文里的工具。'},
        {'type': 'paragraph', 'html': '但在大多数情况下，我给 agent 增加的东西要么是 skills，要么是 TUI 扩展，用来让人和 agent 协作得更顺手。除了 slash commands 之外，Pi 扩展还能直接在终端里渲染自定义 TUI 组件：spinner、progress bar、交互式文件选择器、数据表、预览面板等等。这个 TUI 足够灵活，Mario 甚至证明了它可以<a href="https://x.com/badlogicgames/status/2008702661093454039" target="_blank" rel="noreferrer noopener">在里面跑 Doom</a>。虽然这事并不实用，但如果 Doom 都能跑，那做一个实用的 dashboard 或调试界面当然也没问题。'},
        {'type': 'paragraph', 'html': '我想挑几个自己在用的扩展举例，让你更直观地看到它的可塑性。虽然你可以不加改动地直接拿去用，但这套体系真正鼓励的，还是你把一个现成扩展交给 agent，再让它按你的喜好改出新版本。'},
        {'type': 'heading', 'level': 3, 'text': '/answer'},
        {'type': 'paragraph', 'html': '我<a href="https://lucumr.pocoo.org/2025/12/17/what-is-plan-mode/" target="_blank" rel="noreferrer noopener">不用 plan mode</a>。我更喜欢 agent 主动提问，大家来回沟通；但我不喜欢给它“提问工具”之后那种结构化问卷式对话。我更偏好 agent 用自然语言来表达，中间插一点解释、图示之类的东西。'},
        {'type': 'paragraph', 'html': '问题在于：如果直接在正文里回答这些问题，界面会变得很乱。所以 <code>/answer</code> 会去读取 agent 上一条回复，把里面的所有问题抽出来，再重排进一个更适合输入的对话框里。'},
        {'type': 'image', 'src': 'https://lucumr.pocoo.org/static/pi-answer.png', 'alt': 'The /answer extension showing a question dialog', 'caption': '/answer 扩展把 agent 的问题提炼进一个更适合回答的输入框。'},
        {'type': 'heading', 'level': 3, 'text': '/todos'},
        {'type': 'paragraph', 'html': '虽然我批评过 <a href="https://github.com/steveyegge/beads" target="_blank" rel="noreferrer noopener">Beads</a> 的实现方式，但“给 agent 一个 to-do list”这件事本身真的很有用。<code>/todos</code> 命令会把 <code>.pi/todos</code> 里的所有条目当成 markdown 文件列出来；agent 和我都可以修改它们，session 还可以认领某个任务，把它标成进行中。'},
        {'type': 'embed', 'provider': 'youtube', 'src': 'https://www.youtube.com/embed/ZcKbzxziA5k', 'title': 'Pi /todos extension demo'},
        {'type': 'heading', 'level': 3, 'text': '/review'},
        {'type': 'paragraph', 'html': '随着越来越多代码开始由 agent 写出来，在把半成品直接丢给人类之前，先让另一个 agent 做一轮 review，显然更合理。由于 Pi 的 session 是树状结构，我可以分出一个全新的 review 分支，在那里拿到问题清单，再把修复带回主 session。'},
        {'type': 'image', 'src': 'https://lucumr.pocoo.org/static/pi-review.png', 'alt': 'The /review extension showing review preset options', 'caption': '/review 扩展提供了接近 Codex 风格的 review 入口。'},
        {'type': 'paragraph', 'html': '这个 UI 的设计参考了 Codex：可以很方便地审 commit、diff、未提交改动，或者远端 PR。提示词也会特别关注我在意的东西，所以我能拿到更对味的提醒——比如我会要求它明确指出新增依赖。'},
        {'type': 'heading', 'level': 3, 'text': '/control'},
        {'type': 'paragraph', 'html': '这是一个我还在实验、但并没有日常重度使用的扩展。它允许一个 Pi agent 给另一个 Pi agent 发 prompt。本质上是个非常简单的多 agent 系统，没有复杂编排，适合做实验。'},
        {'type': 'heading', 'level': 3, 'text': '/files'},
        {'type': 'paragraph', 'html': '它会列出当前 session 里被修改过或被引用过的所有文件。你可以在 Finder 里显示它们、在 VS Code 里 diff、快速预览，或者在 prompt 里再次引用。<code>shift+ctrl+r</code> 还能快速预览最近一次提到的文件；当 agent 产出 PDF 的时候，这个功能很顺手。'},
        {'type': 'paragraph', 'html': '其他人也做了不少扩展，比如 <a href="https://github.com/nicobailon/pi-subagents" target="_blank" rel="noreferrer noopener">Nico 的 subagent 扩展</a>，以及 <a href="https://www.npmjs.com/package/pi-interactive-shell" target="_blank" rel="noreferrer noopener">interactive-shell</a>，它能让 Pi 在一个可观察的 TUI 覆层里自主跑交互式 CLI。'},
        {'type': 'heading', 'level': 2, 'text': '软件继续制造软件'},
        {'type': 'paragraph', 'html': '这些都只是“你可以让 agent 做些什么”的例子。真正关键的是：这里面绝大多数东西都不是我亲手写的，而是 agent 按照我的规格帮我做出来的。我只是告诉 Pi：做一个这样的扩展；它就真的做了。这里没有 MCP，没有社区技能商店之类的东西。别误会，我其实用了很多 skills，但它们都是我的 clanker 为我手工打造的，而不是从某个市场下载来的。比如我已经完全不用一堆现成的浏览器自动化 CLI 或 MCP 了，改成了一个只走 <a href="https://github.com/mitsuhiko/agent-stuff/blob/main/skills/web-browser/SKILL.md" target="_blank" rel="noreferrer noopener">CDP 的 skill</a>。这不是因为别的方案不行，而是因为这样做对我来说更自然、更顺手；agent 也能自己维护自己的能力。'},
        {'type': 'paragraph', 'html': '我的 agent 现在有<a href="https://github.com/mitsuhiko/agent-stuff/tree/main/skills" target="_blank" rel="noreferrer noopener">不少 skills</a>，而且关键是：不用了我就会删掉。我曾给它做过一个 skill，让它能读其他工程师共享出来的 Pi session，用在 code review 上；我也有专门帮助 agent 按我喜欢的方式写 commit message、处理提交习惯、更新 changelog 的 skill。这些东西原本是 slash command，现在我正在把它们迁到 skill 体系里，看看效果是否一样好。我还给它做过一个 skill，希望它优先用 <code>uv</code> 而不是 <code>pip</code>；同时我又写了自定义扩展去拦截 <code>pip</code> 和 <code>python</code> 的调用，把它们重定向到 <code>uv</code>。'},
        {'type': 'paragraph', 'html': '和 Pi 这种极简 agent 一起工作的迷人之处之一，就是它会逼着你真正活在“软件继续制造软件”这个想法里。而这条路走到极致，就是把 UI 和输出层拿掉，直接接到聊天里去——这正是 OpenClaw 在做的事。考虑到它最近增长得这么快，我越来越觉得：无论我们喜不喜欢，这大概都会成为未来的一部分。'},
        {'type': 'footnote', 'html': '<a href="https://x.com/steipete/status/2017313990548865292" target="_blank" rel="noreferrer noopener">注 1：原文引用链接</a>'}
    ]
}

theseus_detail = {
    'layout': 'lucumr',
    'available': True,
    'translatedFrom': 'https://lucumr.pocoo.org/2026/3/5/theseus.md',
    'sourceName': "Armin Ronacher's Thoughts and Writings",
    'sourceDescription': '以下为原文结构对应的中文翻译版，尽量保持原文段落顺序与论证节奏。',
    'blocks': [
        {'type': 'paragraph', 'html': '随着写代码的成本越来越低，这件事自然也包括“重新实现”。我前阵子提到过，我让 AI 把我一个库移植到另一门语言里，结果它最终选了一套不同的实现设计。从很多方面看，功能还是那个功能，但到达目标的路径已经变了。那个移植工作的核心做法，就是绕过原实现，直接依赖测试集。'},
        {'type': 'paragraph', 'html': '还有一件相关、但又不完全相同的事发生在 <a href="https://github.com/chardet/chardet/issues/327#issuecomment-4005195078" target="_blank" rel="noreferrer noopener">chardet</a> 上。现在的维护者只把 API 和测试集提供给 agent，让它从零重做了一份实现。这样做的动机，是把许可证从 LGPL 改成 MIT。顺带一提，我自己在这件事里也有立场，因为很多年以来我也一直希望 chardet 能换到一个非 GPL 的许可证。所以你完全可以把我看成一个带偏见的人。'},
        {'type': 'paragraph', 'html': '这份新实现果不其然引发了争议。尤其是原作者 Mark Pilgrim 明确反对，认为它仍然属于派生作品。而那位已经维护这个项目 12 年的新维护者，则认为这是一个全新的作品，并且就是让自己的 coding agent 去按这个方向做。据他说，拿 JPlag 去验证之后，新实现和旧实现是明显不同的。你如果真的去看它的工作方式，这也不算奇怪：它比原版快得多，支持多核，而且采用了从根子上不同的设计。'},
        {'type': 'paragraph', 'html': '但对我来说，更有意思的其实不是这场争论本身，而是它所揭示的后果。像 GPL 这样的 copyleft 代码，在很大程度上依赖版权体系以及执行成本带来的摩擦力。可一旦代码天然公开，不管有没有测试，现在你都能很轻松地把它重写一遍。这几年我自己也一直想对一些 GPL 库这么做，readline 的一个重写我之前就已经开了头，理由也类似——就是它的 GPL 许可证。这里当然有道德问题，但那并不是我此刻最关心的点。因为不仅 GPL 软件可能以 MIT 形式重新出现，那些被放弃的专有软件，也可能出现同样的命运。'},
        {'type': 'paragraph', 'html': '对我个人来说，更有意思的一点在于：这些“新作品”甚至可能根本无法被版权保护。法院完全有可能裁定，AI 生成代码由于缺乏足够的人类输入，所以应当直接落入公有领域。当然，这种结果未必最可能发生，但它绝不是不可能。'},
        {'type': 'paragraph', 'html': '但无论如何，这些变化都在逼出一些我们还没准备好的新局面。比如 Vercel 可以很开心地用 Clankers <a href="https://just-bash.dev/" target="_blank" rel="noreferrer noopener">重做 bash</a>，可当有人用同样方法重做 Next.js 时，它又会表现得<a href="https://x.com/cramforce/status/2027155457597669785" target="_blank" rel="noreferrer noopener">非常不高兴</a>。'},
        {'type': 'paragraph', 'html': '这里面的后果非常大。如果生成代码的成本真的降到这么低，而且我们只靠测试集就能把一套软件重新实现出来，那这会如何改变软件的未来？我们会不会看到大量软件以更宽松的许可证重新出现？会不会看到大量专有软件重新作为开源出现？又或者，是否也会有很多软件重新以专有形式出现？'},
        {'type': 'paragraph', 'html': '这是一个全新的世界，而我们几乎还不知道该怎么在其中导航。短期内，我们大概会先看到一轮关于版权的争吵；但我总觉得，真正把这些争端送进法院的情况可能不会很多，因为所有相关方其实都会害怕：一旦判例被立下来，后果可能远超当下这次冲突本身。'},
        {'type': 'paragraph', 'html': '如果只看 GPL 这个方向，我觉得这会重新点燃一些已经沉寂很久的老争论：copyleft 和 permissive license 到底谁更合理。自己的作品被一个 Clanker 重写，署名感被抹掉，这当然不会让人好受。但和“忒修斯之船”不同的是，这里的边界对我来说反而更清楚：如果你把所有旧代码都扔掉，从零开始重写，即便最后行为一致，那它也已经是一艘新船了。它只是还顶着旧名字而已。反过来看，这或许也说明：作者也许更应该抓住的是商标，而不是单纯依赖许可证和合同法。'},
        {'type': 'paragraph', 'html': '就我个人而言，我觉得这一切很令人兴奋。我一直支持尽可能少用许可证约束地把东西公开出去；我相信当大家愿意共享时，社会整体会变得更好，而 GPL 在我看来恰恰与这种精神相悖，因为它限制了别人能拿这些东西做什么。眼下的变化正好印证了我的世界观。当然，我也完全理解并不是每个人都这么看，所以我预计围绕 slopforks 还会有更多争执。毕竟，它把两个本来就极易引发争论的话题——许可证和 AI——以一种最糟糕的方式绑在了一起。'}
    ]
}

for post in data.get('posts', []):
    if post.get('slug') == 'pi-the-minimal-agent-within-openclaw':
        post['detail'] = pi_detail
    elif post.get('slug') == 'ai-and-the-ship-of-theseus':
        post['detail'] = theseus_detail
    else:
        post.setdefault('detail', {'available': False})

path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('updated', path)
