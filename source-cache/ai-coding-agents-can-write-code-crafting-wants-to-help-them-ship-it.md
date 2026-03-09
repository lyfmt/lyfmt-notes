# AI coding agents can write code, Crafting wants to help them ship it

AI coding agents are getting very good at generating code, but for enterprise engineering teams that is only part of the problem. Teams still have to test, validate, and actually ship that code against real production infrastructure, and that remains a bottleneck that most agent tooling does not address.

Crafting, a San Francisco startup founded by former engineering leaders from Google, Meta, Uber, and Discord, says it wants to solve that problem by giving engineers a platform that provides AI agents with production-like environments containing real dependencies and real data.

CEO Sumeet Vaidya argues that the industry spent the previous six to nine months concentrating on faster code generation, but large engineering organizations eventually run into a different set of issues: orchestration, coordination, efficient resource usage, and the practical constraints of running many agents at scale. The company launched Crafting for Agents alongside a $5.5 million seed round led by Mischief.

## From sandboxes to production-like environments

Crafting already offered cloud-based development environments for human engineers, including Kubernetes interception and hot-swappable services that let developers test against production-like setups. Crafting for Agents extends that same infrastructure to AI agents.

The company’s model is that one coding agent can generate code, while a separate testing agent spins up a production-like environment through Crafting, runs tests there, and iterates based on the result.

Vaidya says agents that live only inside isolated sandboxes cannot do very much. In his framing, the real value is controlled access: if an agent is working on a task that needs access to payments infrastructure in staging, the platform should be able to grant the right credentials for that narrow purpose.

Crafting’s bet is that the hard problem for enterprise customers is not starting a container. The hard part is reproducing the complexity of a company’s real infrastructure, including network topology, credential management, and compliance requirements.

Faire senior engineering manager Cheuk-man Kong says earlier approaches were either point solutions or systems the team had to stitch together on its own. He says Crafting helped Faire scale an agentic stack with secure access to internal systems, MCP servers, and cloud resources.

## Enterprise onboarding

That approach makes onboarding highly hands-on. Crafting says it learns each customer’s network topology, configures Kubernetes clusters that mirror production needs, and manages access to credentials. The company names Brex, Faire, Webflow, Verkada, Persona, and Instabase as early customers.

Vaidya argues that internal staging environments that merely resemble production are often not enough. Instead, the Crafting team works with customers to build environments that directly mimic the parts of production the agent actually needs.

He also says every enterprise is different in infrastructure and expectations, so there will always be some bespoke white-glove work required to get these systems running safely.

According to Vaidya, the strongest interest so far has come from fintech and other heavily regulated industries, where companies have explicit requirements for security and controlled access.

Crafting says teams on its platform are shipping 25 percent more pull requests quarter over quarter, while engineers save about 2.5 hours a week on environment setup. It also says AI-generated code across its customer base has moved from single-digit percentages to as high as 70 percent of total output within twelve months.

## The bigger vision

Vaidya, who previously led engineering teams at Discord, Uber, and Facebook/Meta, says software development is only the initial use case.

His longer-term ambition is to turn Crafting into an operating system for agents: a general infrastructure layer where enterprise agents can obtain the credentials and access they need for engineering, observability, monitoring, or collaboration work.

He argues that enterprises should not wait for the technology to stop changing before investing. Even if the tools improve again in six months, companies that build now can capture six months of additional productivity in the meantime.
