const THEME_KEY = "pi-blog-demo-theme";
const DATA_URL = "./articles.json";
const HOME_PAGE_SIZE = 1;

const themeToggle = document.getElementById("theme-toggle");
const body = document.body;
const pageType = body?.dataset?.page || "home";

function getStoredTheme() {
  try {
    const theme = window.localStorage.getItem(THEME_KEY);
    return theme === "dark" || theme === "light" ? theme : null;
  } catch {
    return null;
  }
}

function storeTheme(theme) {
  try {
    window.localStorage.setItem(THEME_KEY, theme);
  } catch {
    // Ignore storage failures.
  }
}

function getPreferredTheme() {
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function applyTheme(theme) {
  const nextTheme = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = nextTheme;

  if (body) {
    body.dataset.theme = nextTheme;
  }

  if (themeToggle) {
    const switchTo = nextTheme === "dark" ? "light" : "dark";
    themeToggle.textContent = switchTo === "dark" ? "Dark mode" : "Light mode";
    themeToggle.setAttribute("aria-label", `Switch to ${switchTo} theme`);
    themeToggle.setAttribute("aria-pressed", String(nextTheme === "dark"));
  }
}

function initThemeToggle() {
  applyTheme(getStoredTheme() || getPreferredTheme());

  if (!themeToggle) {
    return;
  }

  themeToggle.addEventListener("click", () => {
    const currentTheme = document.documentElement.dataset.theme === "dark" ? "dark" : "light";
    const nextTheme = currentTheme === "dark" ? "light" : "dark";
    applyTheme(nextTheme);
    storeTheme(nextTheme);
  });
}

function qs(id) {
  return document.getElementById(id);
}

function clear(node) {
  if (node) {
    node.replaceChildren();
  }
}

function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }
  if (typeof text === "string") {
    element.textContent = text;
  }
  return element;
}

function setText(id, text) {
  const node = qs(id);
  if (node && typeof text === "string") {
    node.textContent = text;
  }
}

function setHref(id, href) {
  const node = qs(id);
  if (node && typeof href === "string") {
    node.href = href;
  }
}

function formatDate(value) {
  if (typeof value !== "string" || !value.trim()) {
    return "";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

function getInitials(name) {
  if (typeof name !== "string" || !name.trim()) {
    return "AI";
  }

  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((part) => part[0]?.toUpperCase() || "").join("") || "AI";
}

function createTag(tagText) {
  return createElement("span", "tag", tagText);
}

function createTagRow(tags) {
  if (!Array.isArray(tags) || !tags.length) {
    return null;
  }

  const row = createElement("div", "tag-row");
  tags
    .filter((tag) => typeof tag === "string" && tag.trim())
    .forEach((tag) => row.appendChild(createTag(tag.trim())));

  return row.childNodes.length ? row : null;
}

function buildPostHref(slug) {
  return `./post.html?slug=${encodeURIComponent(slug)}`;
}

function buildIndexHref(page) {
  return page > 1 ? `./index.html?page=${page}` : "./index.html";
}

function createMetaLine(post) {
  return [post.author, formatDate(post.publishedAt), post.source]
    .filter((part) => typeof part === "string" && part.trim())
    .join(" • ");
}

function getPageFromQuery() {
  const params = new URLSearchParams(window.location.search);
  const raw = Number.parseInt(params.get("page") || "1", 10);
  return Number.isFinite(raw) && raw > 0 ? raw : 1;
}

function getSlugFromQuery() {
  const params = new URLSearchParams(window.location.search);
  return params.get("slug") || "";
}

function validatePosts(posts) {
  return Array.isArray(posts)
    ? posts.filter((post) => post && typeof post.slug === "string" && typeof post.title === "string")
    : [];
}

function renderFeatured(site, posts) {
  const siteTitle = typeof site?.title === "string" && site.title.trim()
    ? site.title.trim()
    : "Agent Notes Demo";
  const description = typeof site?.description === "string" && site.description.trim()
    ? site.description.trim()
    : "一个更接近真实博客的首页演示。";

  setText("home-title", siteTitle);
  setText("home-description", description);

  const featured = posts[0] || null;
  if (!featured) {
    setText("featured-title", "暂无精选文章");
    setText("featured-excerpt", "当前还没有文章可展示。请先在 articles.json 中添加内容。");
    setText("featured-meta", "等待内容中");
    setHref("hero-primary-link", "#latest-posts-title");
    return;
  }

  setText("featured-title", featured.title);
  setText("featured-excerpt", featured.excerpt || "这篇文章暂无摘要。" );
  setText("featured-meta", createMetaLine(featured));
  setHref("hero-primary-link", buildPostHref(featured.slug));
}

function renderStats(posts) {
  const authors = new Set();
  const sources = new Set();

  posts.forEach((post) => {
    if (post.author) {
      authors.add(post.author);
    }
    if (post.source) {
      sources.add(post.source);
    }
  });

  setText("stat-post-count", String(posts.length));
  setText("stat-author-count", String(authors.size));
  setText("stat-source-count", String(sources.size));
}

function collectAuthors(posts) {
  const map = new Map();

  posts.forEach((post) => {
    const name = typeof post.author === "string" && post.author.trim() ? post.author.trim() : "Unknown";
    const current = map.get(name) || {
      name,
      count: 0,
      latest: "",
      sources: new Set(),
      tags: new Set()
    };

    current.count += 1;

    if (typeof post.publishedAt === "string" && post.publishedAt > current.latest) {
      current.latest = post.publishedAt;
    }

    if (typeof post.source === "string" && post.source.trim()) {
      current.sources.add(post.source.trim());
    }

    if (Array.isArray(post.tags)) {
      post.tags.forEach((tag) => {
        if (typeof tag === "string" && tag.trim()) {
          current.tags.add(tag.trim());
        }
      });
    }

    map.set(name, current);
  });

  return Array.from(map.values()).sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
}

function renderAuthors(posts) {
  const container = qs("author-list");
  if (!container) {
    return;
  }

  clear(container);
  container.setAttribute("aria-busy", "false");

  const authors = collectAuthors(posts);
  if (!authors.length) {
    const empty = createElement("article", "empty-state empty-state--compact");
    empty.appendChild(createElement("p", "", "当前没有可展示的作者信息。"));
    container.appendChild(empty);
    return;
  }

  authors.forEach((author) => {
    const card = createElement("article", "author-card");
    const header = createElement("div", "author-card__header");
    const avatar = createElement("div", "author-card__avatar", getInitials(author.name));
    const meta = createElement("div", "author-card__meta");
    meta.append(
      createElement("h3", "author-card__name", author.name),
      createElement("p", "author-card__copy", `${author.count} 篇文章 · 最近更新 ${formatDate(author.latest)}`)
    );
    header.append(avatar, meta);

    const sources = createElement("p", "author-card__copy", `来源：${Array.from(author.sources).join("、") || "未知"}`);
    const tags = createTagRow(Array.from(author.tags).slice(0, 4));

    card.appendChild(header);
    card.appendChild(sources);
    if (tags) {
      card.appendChild(tags);
    }

    container.appendChild(card);
  });
}

function renderPagination(totalPages, currentPage) {
  const container = qs("pagination");
  if (!container) {
    return;
  }

  clear(container);

  if (totalPages <= 1) {
    const only = createElement("span", "pagination__link is-current", "1");
    only.setAttribute("aria-current", "page");
    container.appendChild(only);
    return;
  }

  const prev = currentPage > 1
    ? (() => {
        const link = createElement("a", "pagination__link", "← 上一页");
        link.href = buildIndexHref(currentPage - 1);
        return link;
      })()
    : createElement("span", "pagination__link is-disabled", "← 上一页");

  container.appendChild(prev);

  for (let page = 1; page <= totalPages; page += 1) {
    if (page === currentPage) {
      const current = createElement("span", "pagination__link is-current", String(page));
      current.setAttribute("aria-current", "page");
      container.appendChild(current);
    } else {
      const link = createElement("a", "pagination__link", String(page));
      link.href = buildIndexHref(page);
      container.appendChild(link);
    }
  }

  const next = currentPage < totalPages
    ? (() => {
        const link = createElement("a", "pagination__link", "下一页 →");
        link.href = buildIndexHref(currentPage + 1);
        return link;
      })()
    : createElement("span", "pagination__link is-disabled", "下一页 →");

  container.appendChild(next);
}

function renderHome(site, posts) {
  const description = qs("home-description");
  const count = qs("post-count");
  const container = qs("home-posts");

  if (!container) {
    return;
  }

  const siteTitle = typeof site?.title === "string" && site.title.trim() ? site.title.trim() : "Agent Notes Demo";
  const requestedPage = getPageFromQuery();
  const totalPages = Math.max(1, Math.ceil(posts.length / HOME_PAGE_SIZE));
  const currentPage = Math.min(Math.max(1, requestedPage), totalPages);

  document.title = currentPage > 1 ? `${siteTitle} — Page ${currentPage}` : siteTitle;

  if (description && site?.description) {
    description.textContent = site.description;
  }

  renderFeatured(site, posts);
  renderStats(posts);
  renderAuthors(posts);

  if (count) {
    count.textContent = `第 ${currentPage} 页 / 共 ${totalPages} 页 · ${posts.length} 篇文章`;
  }

  clear(container);
  container.setAttribute("aria-busy", "false");

  if (!posts.length) {
    const empty = createElement("article", "empty-state");
    empty.append(
      createElement("h3", "", "暂无文章"),
      createElement("p", "", "articles.json 已加载，但 posts 数组为空。")
    );
    container.appendChild(empty);
    renderPagination(1, 1);
    return;
  }

  const start = (currentPage - 1) * HOME_PAGE_SIZE;
  const pagePosts = posts.slice(start, start + HOME_PAGE_SIZE);

  pagePosts.forEach((post, index) => {
    const card = createElement("article", "post-card");

    const badge = createElement("span", "post-card__index", String(start + index + 1).padStart(2, "0"));
    const meta = createElement("p", "post-card__meta", createMetaLine(post));
    const title = createElement("h3", "post-card__title");
    const titleLink = createElement("a", "post-card__link", post.title);
    titleLink.href = buildPostHref(post.slug);
    title.appendChild(titleLink);

    const excerpt = createElement("p", "post-card__excerpt", post.excerpt || "");
    const footer = createElement("div", "post-card__footer");
    const more = createElement("a", "post-card__more", "阅读详情 →");
    more.href = buildPostHref(post.slug);
    footer.appendChild(more);

    const tagRow = createTagRow(post.tags);
    if (tagRow) {
      footer.prepend(tagRow);
    }

    card.append(badge, meta, title, excerpt, footer);
    container.appendChild(card);
  });

  renderPagination(totalPages, currentPage);
}

function renderPost(post, relatedPosts) {
  const article = qs("post-article");
  const related = qs("related-posts");

  if (!article) {
    return;
  }

  clear(article);
  article.setAttribute("aria-busy", "false");

  if (!post) {
    const empty = createElement("section", "empty-state");
    empty.append(
      createElement("h2", "", "未找到文章"),
      createElement("p", "", "请从首页重新选择文章。")
    );
    article.appendChild(empty);
    document.title = "Post not found — Agent Notes Demo";
    return;
  }

  document.title = `${post.title} — Agent Notes Demo`;

  const header = createElement("header", "article-header");
  const source = createElement("p", "eyebrow", post.source || "Post");
  const title = createElement("h1", "article-title", post.title);
  const meta = createElement("p", "article-meta", createMetaLine(post));
  const excerpt = createElement("p", "article-excerpt", post.excerpt || "");

  header.append(source, title);
  if (meta.textContent) {
    header.appendChild(meta);
  }
  if (excerpt.textContent) {
    header.appendChild(excerpt);
  }

  const headerTags = createTagRow(post.tags);
  if (headerTags) {
    header.appendChild(headerTags);
  }

  const sourceLink = createElement("a", "article-source-link", "查看原文 ↗");
  sourceLink.href = post.url;
  sourceLink.target = "_blank";
  sourceLink.rel = "noreferrer noopener";
  header.appendChild(sourceLink);

  article.appendChild(header);

  const contentWrap = createElement("div", "article-content");
  const sections = Array.isArray(post.content) ? post.content : [];

  sections.forEach((section) => {
    const sectionNode = createElement("section", "article-section");

    if (typeof section === "string") {
      sectionNode.appendChild(createElement("p", "", section));
      contentWrap.appendChild(sectionNode);
      return;
    }

    if (section?.heading) {
      sectionNode.appendChild(createElement("h2", "article-section__title", section.heading));
    }

    if (Array.isArray(section?.paragraphs)) {
      section.paragraphs
        .filter((paragraph) => typeof paragraph === "string" && paragraph.trim())
        .forEach((paragraph) => {
          sectionNode.appendChild(createElement("p", "", paragraph.trim()));
        });
    }

    if (sectionNode.childNodes.length) {
      contentWrap.appendChild(sectionNode);
    }
  });

  if (!contentWrap.childNodes.length) {
    const empty = createElement("section", "empty-state empty-state--compact");
    empty.append(
      createElement("h3", "", "暂无正文"),
      createElement("p", "", "这篇文章还没有可渲染的正文段落。")
    );
    contentWrap.appendChild(empty);
  }

  article.appendChild(contentWrap);

  if (related) {
    const listWrap = related.querySelector(".side-list");
    if (listWrap) {
      clear(listWrap);
      related.setAttribute("aria-busy", "false");

      relatedPosts
        .filter((item) => item.slug !== post.slug)
        .forEach((item) => {
          const card = createElement("article", "side-card");
          const titleNode = createElement("h3", "side-card__title");
          const link = createElement("a", "side-card__link", item.title);
          link.href = buildPostHref(item.slug);
          titleNode.appendChild(link);
          const metaLine = createElement("p", "side-card__meta", createMetaLine(item));
          card.append(titleNode, metaLine);
          listWrap.appendChild(card);
        });

      if (!listWrap.childNodes.length) {
        const empty = createElement("article", "empty-state empty-state--compact");
        empty.appendChild(createElement("p", "", "暂无其他文章。"));
        listWrap.appendChild(empty);
      }
    }
  }
}

function renderError(message) {
  const targetIds = ["home-posts", "author-list", "pagination", "post-article", "related-posts"];

  targetIds.forEach((id) => {
    const node = qs(id);
    if (!node) {
      return;
    }

    if (id === "related-posts") {
      const listWrap = node.querySelector(".side-list");
      if (listWrap) {
        clear(listWrap);
        const box = createElement("article", "empty-state empty-state--compact");
        box.appendChild(createElement("p", "", message));
        listWrap.appendChild(box);
      }
      node.setAttribute("aria-busy", "false");
      return;
    }

    clear(node);
    node.setAttribute("aria-busy", "false");
    const box = createElement("article", "empty-state");
    box.append(
      createElement("h3", "", "加载失败"),
      createElement("p", "", message)
    );
    node.appendChild(box);
  });

  setText("post-count", "加载失败");
}

async function loadBlog() {
  try {
    const response = await fetch(DATA_URL);
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    const data = await response.json();
    const site = data && typeof data.site === "object" ? data.site : {};
    const posts = validatePosts(data?.posts);

    if (pageType === "post") {
      const slug = getSlugFromQuery();
      const current = posts.find((post) => post.slug === slug) || posts[0] || null;
      renderPost(current, posts);
      return;
    }

    renderHome(site, posts);
  } catch (error) {
    const message = error instanceof Error && error.message
      ? error.message
      : "无法加载 articles.json";
    renderError(message);
    console.error(error);
  }
}

initThemeToggle();
void loadBlog();
