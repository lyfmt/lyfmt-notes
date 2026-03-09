# Perhaps not Boring Technology after all

A recurring concern about LLMs for programming is that they might push developers toward the tools that are best represented in training data, making it harder for newer or less common technologies to break through.

Simon Willison says that this concern certainly looked valid a couple of years ago, when models appeared to give much better answers for Python or JavaScript than for less widely used languages and tools.

His view is that the newest models, when used inside good coding-agent harnesses, seem to weaken that effect.

He says he is seeing excellent results with brand new tools such as showboat, rodney, and chartroom. His approach is to tell the agent to start by reading the tools’ own help output, and the longer context windows of newer models mean they can absorb a substantial amount of documentation before beginning the task.

He also says that if you drop a coding agent into an existing codebase that uses libraries or tools that are too private or too new to be well represented in training data, the agent can still perform well. In his experience, the agent studies existing examples, infers the local patterns, and then iterates and tests until it fills in the gaps.

The surprising result for him is that coding agents do not currently seem to force his own technology choices toward the “Choose Boring Technology” approach nearly as much as he expected.

## Update

Willison adds that there is still a separate question about what technology stacks LLM-powered tools recommend by default.

He points to the study “What Claude Code Actually Chooses,” which found that Claude Code showed a strong build-over-buy bias and repeated preferences for certain tools, with GitHub Actions, Stripe, and shadcn/ui approaching a near monopoly in their categories.

For this post, though, he cares more about what happens after a human has already chosen a different stack and handed that choice to the agent.

He also highlights the growing importance of Skills. More and more coding-agent ecosystems now support skills that explicitly teach an agent how to use a specific framework or product.

He lists Remotion, Supabase, Vercel, and Prisma as examples of projects that now publish official skills to help agents work with their tools.
