const THEME_KEY = "pi-blog-demo-theme";
const DATA_URL = "./articles.json?v=20260311-2";
const HOME_PAGE_SIZE = 4;

const themeToggle = document.getElementById("theme-toggle");
const body = document.body;
const pageType = body?.dataset?.page || "home";

let cachedSite = null;
let cachedPosts = [];
let hasLoadedBlog = false;

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

function initMobileHeaderBehavior() {
  const header = document.querySelector(".site-header");
  if (!header) {
    return;
  }

  const mediaQuery = window.matchMedia("(max-width: 760px)");
  let lastY = window.scrollY;
  let ticking = false;

  function syncHeaderState() {
    const currentY = window.scrollY;
    const delta = currentY - lastY;

    if (!mediaQuery.matches) {
      header.classList.remove("is-mobile-hidden");
      lastY = currentY;
      ticking = false;
      return;
    }

    if (currentY <= 8) {
      header.classList.remove("is-mobile-hidden");
    } else if (delta > 10) {
      header.classList.add("is-mobile-hidden");
    } else if (delta < -10) {
      header.classList.remove("is-mobile-hidden");
    }

    lastY = currentY;
    ticking = false;
  }

  function onScroll() {
    if (ticking) {
      return;
    }

    ticking = true;
    window.requestAnimationFrame(syncHeaderState);
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  mediaQuery.addEventListener("change", syncHeaderState);
  syncHeaderState();
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

function renderMarkdownNodes(markdown, options = {}) {
  const nodes = [];
  if (typeof markdown !== "string" || !markdown.trim()) {
    return nodes;
  }

  const { skipH1 = false } = options;
  const lines = markdown.split(/\r?\n/);
  let buffer = [];

  function flushParagraph() {
    if (!buffer.length) {
      return;
    }
    const text = buffer.join(" ").trim();
    if (text) {
      nodes.push(createElement("p", "", text));
    }
    buffer = [];
  }

  lines.forEach((raw) => {
    const line = raw.trim();
    if (!line) {
      flushParagraph();
      return;
    }
    if (line.startsWith("### ")) {
      flushParagraph();
      nodes.push(createElement("h3", "", line.slice(4).trim()));
      return;
    }
    if (line.startsWith("## ")) {
      flushParagraph();
      nodes.push(createElement("h2", "", line.slice(3).trim()));
      return;
    }
    if (line.startsWith("# ")) {
      flushParagraph();
      if (!skipH1) {
        nodes.push(createElement("h1", "", line.slice(2).trim()));
      }
      return;
    }
    buffer.push(line);
  });

  flushParagraph();
  return nodes;
}


function extractMarkdownTitle(markdown) {
  if (typeof markdown !== "string") {
    return "";
  }
  const lines = markdown.split(/\r?\n/);
  for (const raw of lines) {
    const line = raw.trim();
    if (line.startsWith("# ")) {
      return line.slice(2).trim();
    }
  }
  return "";
}


function applyExcerptTitleToPosts(posts) {
  if (!Array.isArray(posts)) {
    return posts;
  }
  posts.forEach((post) => {
    const excerptTitle = extractMarkdownTitle(post?.excerpt || "");
    if (excerptTitle) {
      post.title = excerptTitle;
    }
  });
  return posts;
}

function renderMarkdownInto(target, markdown, options) {
  if (!target) {
    return;
  }
  const nodes = renderMarkdownNodes(markdown, options || {});
  if (!nodes.length) {
    return;
  }
  nodes.forEach((node) => target.appendChild(node));
}

function setMarkdown(id, markdown, options) {
  const node = qs(id);
  if (!node) {
    return;
  }
  clear(node);
  renderMarkdownInto(node, markdown, options || {});
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
  const link = createElement("a", "tag", tagText);
  link.href = buildTagHref(tagText);
  link.title = `查看标签「${tagText}」归档`;
  return link;
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

function renderTags(id, tags) {
  const container = qs(id);
  if (!container) {
    return;
  }

  clear(container);
  const row = createTagRow(tags);
  if (row) {
    container.appendChild(row);
  }
}

function normalizeTag(tag) {
  return typeof tag === "string" ? tag.trim().toLowerCase() : "";
}

function collectTags(posts) {
  const map = new Map();

  posts.forEach((post) => {
    if (!Array.isArray(post.tags)) {
      return;
    }

    post.tags.forEach((tag) => {
      if (typeof tag !== "string" || !tag.trim()) {
        return;
      }

      const value = tag.trim();
      const key = normalizeTag(value);
      const current = map.get(key) || { name: value, count: 0 };
      current.count += 1;
      map.set(key, current);
    });
  });

  return Array.from(map.values()).sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
}

function filterPostsByTag(posts, activeTag) {
  const normalizedTag = normalizeTag(activeTag);
  if (!normalizedTag) {
    return posts;
  }

  return posts.filter((post) =>
    Array.isArray(post.tags)
    && post.tags.some((tag) => normalizeTag(tag) === normalizedTag)
  );
}

function createTagFilterChip(tag, href, isActive) {
  const chip = createElement("a", "tag", tag);
  chip.href = href;
  if (tag !== "全部") {
    chip.title = `在首页按「${tag}」筛选`;
  }

  if (isActive) {
    chip.setAttribute("aria-current", "true");
    chip.style.background = "var(--accent)";
    chip.style.color = "#fff";
  }

  return chip;
}

function renderTagFilters(tags, activeTag, sort) {
  const container = qs("tag-filter-list");
  if (!container) {
    return;
  }

  clear(container);

  const row = createElement("div", "tag-row");
  row.appendChild(createTagFilterChip("全部", buildIndexHref(1, "", sort), !normalizeTag(activeTag)));

  tags.forEach((tag) => {
    const isActive = normalizeTag(tag.name) === normalizeTag(activeTag);
    row.appendChild(createTagFilterChip(`${tag.name} (${tag.count})`, buildIndexHref(1, tag.name, sort), isActive));
  });

  container.appendChild(row);
}

function buildPostHref(slug, view) {
  const params = new URLSearchParams();
  const resolvedView = view === "detail" ? "detail" : "summary";
  params.set("slug", slug);
  if (resolvedView === "detail") {
    params.set("view", "detail");
  }
  return `./post.html?${params.toString()}`;
}

function buildAuthorHref(author) {
  const params = new URLSearchParams({ author: author.trim() });
  return `./author.html?${params.toString()}`;
}

function buildTagHref(tag) {
  const params = new URLSearchParams({ tag: tag.trim() });
  return `./tag.html?${params.toString()}`;
}

function buildIndexHref(page, tag, sort) {
  const params = new URLSearchParams();
  const trimmedTag = typeof tag === "string" ? tag.trim() : "";
  const resolvedSort = sort === "added-asc" ? "added-asc" : "added-desc";

  if (page > 1) {
    params.set("page", String(page));
  }

  if (trimmedTag) {
    params.set("tag", trimmedTag);
  }

  if (resolvedSort !== "added-desc") {
    params.set("sort", resolvedSort);
  }

  const query = params.toString();
  return query ? `./index.html?${query}` : "./index.html";
}

function createMetaLine(post) {
  return [post.author, formatDate(post.publishedAt), post.source]
    .filter((part) => typeof part === "string" && part.trim())
    .join(" • ");
}

function sortPostsByAdded(posts, sort) {
  const list = Array.isArray(posts) ? [...posts] : [];
  return sort === "added-asc" ? [...list].reverse() : list;
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

function getAuthorFromQuery() {
  const author = new URLSearchParams(window.location.search).get("author");
  return author ? author.trim() : "";
}

function getTagFromQuery() {
  return new URLSearchParams(window.location.search).get("tag")?.trim() || "";
}

function getSortFromQuery() {
  const raw = new URLSearchParams(window.location.search).get("sort")?.trim();
  return raw === "added-asc" ? "added-asc" : "added-desc";
}

function getPostViewFromQuery() {
  const raw = new URLSearchParams(window.location.search).get("view")?.trim();
  return raw === "detail" ? "detail" : "summary";
}

function validatePosts(posts) {
  return Array.isArray(posts)
    ? posts.filter((post) => post && typeof post.slug === "string" && typeof post.title === "string")
    : [];
}

function isModifiedNavigation(event) {
  return event.defaultPrevented
    || event.button !== 0
    || event.metaKey
    || event.ctrlKey
    || event.shiftKey
    || event.altKey;
}

function isHomePathname(pathname) {
  return pathname === "/" || pathname.endsWith("/index.html");
}

async function renderCurrentHomePage(preferFresh = false) {
  if (pageType !== "home") {
    return;
  }

  if (preferFresh || !hasLoadedBlog) {
    await loadBlog();
    return;
  }

  renderHome(cachedSite || {}, Array.isArray(cachedPosts) ? cachedPosts : []);
}

function initHomeNavigation() {
  if (pageType !== "home") {
    return;
  }

  document.addEventListener("click", (event) => {
    const link = event.target.closest("#pagination a, #tag-filter-list a, #sort-filter-list a");
    if (!link || isModifiedNavigation(event)) {
      return;
    }

    if (link.target && link.target !== "_self") {
      return;
    }

    const url = new URL(link.href, window.location.href);
    if (url.origin !== window.location.origin || !isHomePathname(url.pathname) || !hasLoadedBlog) {
      return;
    }

    const nextUrl = `${url.pathname}${url.search}${url.hash}`;
    const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;

    event.preventDefault();
    if (nextUrl === currentUrl) {
      return;
    }

    window.history.pushState({ page: "home" }, "", nextUrl);
    void renderCurrentHomePage(true);
  });

  window.addEventListener("popstate", () => {
    if (!hasLoadedBlog || !isHomePathname(window.location.pathname)) {
      return;
    }

    void renderCurrentHomePage(true);
  });

  window.addEventListener("focus", () => {
    if (!hasLoadedBlog || !isHomePathname(window.location.pathname)) {
      return;
    }

    void renderCurrentHomePage(true);
  });
}

function renderFeatured(site, posts, activeTag) {
  const siteTitle = typeof site?.title === "string" && site.title.trim()
    ? site.title.trim()
    : "lyfmt's Notes";
  const description = typeof site?.description === "string" && site.description.trim()
    ? site.description.trim()
    : "一个更接近真实博客的首页演示。";
  const tagLabel = typeof activeTag === "string" ? activeTag.trim() : "";

  setText("home-title", siteTitle);
  setText("home-description", description);
  setText(
    "featured-supporting-copy",
    tagLabel
      ? `当前正在按「${tagLabel}」标签浏览，可先查看这一主题的精选内容，再继续阅读作者与最新文章。`
      : "在这里快速查看精选内容、作者信息与最新文章动态。"
  );

  const featured = Array.isArray(posts) ? posts[0] || null : null;

  if (!featured) {
    setText("featured-title", "暂无精选文章");
    setText("featured-excerpt", "当前还没有文章可展示。请先在 articles.json 中添加内容。");
    setText("featured-meta", "等待内容中");
    setHref("hero-primary-link", "#latest-posts-title");
    renderTags("featured-tags", []);
    return;
  }

  setText("featured-title", featured.title);
  const featuredExcerpt = featured.excerpt || "这篇文章暂无摘要。";
  const excerptIsMarkdown = typeof featuredExcerpt === "string" && featuredExcerpt.trim().startsWith("# ");
  setMarkdown("featured-excerpt", featuredExcerpt, { skipH1: excerptIsMarkdown });
  setText("featured-meta", createMetaLine(featured));
  setHref("hero-primary-link", buildPostHref(featured.slug));
  renderTags("featured-tags", featured.tags);
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
    const nameHeading = createElement("h3", "author-card__name");
    const nameLink = createElement("a", "author-card__link", author.name);
    nameLink.href = buildAuthorHref(author.name);
    nameHeading.appendChild(nameLink);
    meta.append(
      nameHeading,
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

function renderSortFilters(activeSort, activeTag) {
  const container = qs("sort-filter-list");
  if (!container) {
    return;
  }

  clear(container);

  const row = createElement("div", "segmented-control");
  row.setAttribute("role", "tablist");
  row.setAttribute("aria-label", "按加入时间排序");

  const options = [
    ["added-desc", "最新加入"],
    ["added-asc", "最早加入"]
  ];

  options.forEach(([value, label]) => {
    const isActive = activeSort === value;
    const link = createElement("a", `segmented-control__item${isActive ? " is-active" : ""}`, label);
    link.href = buildIndexHref(1, activeTag, value);
    link.setAttribute("role", "tab");
    link.setAttribute("aria-selected", String(isActive));
    if (isActive) {
      link.setAttribute("aria-current", "true");
    }
    row.appendChild(link);
  });

  container.appendChild(row);
}

function renderPagination(totalPages, currentPage, activeTag, activeSort) {
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
        link.href = buildIndexHref(currentPage - 1, activeTag, activeSort);
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
      link.href = buildIndexHref(page, activeTag, activeSort);
      container.appendChild(link);
    }
  }

  const next = currentPage < totalPages
    ? (() => {
        const link = createElement("a", "pagination__link", "下一页 →");
        link.href = buildIndexHref(currentPage + 1, activeTag, activeSort);
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

  const siteTitle = typeof site?.title === "string" && site.title.trim() ? site.title.trim() : "lyfmt's Notes";
  const activeTag = getTagFromQuery();
  const activeSort = getSortFromQuery();
  const allTags = collectTags(posts);
  const filteredPosts = filterPostsByTag(posts, activeTag);
  const sortedPosts = sortPostsByAdded(filteredPosts, activeSort);
  const featuredPosts = sortedPosts.length ? sortedPosts : sortPostsByAdded(posts, activeSort);
  const requestedPage = getPageFromQuery();
  const totalPages = Math.max(1, Math.ceil(sortedPosts.length / HOME_PAGE_SIZE));
  const currentPage = Math.min(Math.max(1, requestedPage), totalPages);

  document.title = activeTag
    ? `${siteTitle} — ${activeTag}`
    : currentPage > 1 ? `${siteTitle} — 第 ${currentPage} 页` : siteTitle;

  if (description && site?.description) {
    description.textContent = site.description;
  }

  renderTagFilters(allTags, activeTag, activeSort);
  renderSortFilters(activeSort, activeTag);
  renderFeatured(site, featuredPosts, activeTag);
  renderStats(posts);
  renderAuthors(posts);

  if (count) {
    const sortLabel = activeSort === "added-asc" ? "最早加入" : "最新加入";
    count.textContent = activeTag
      ? `标签「${activeTag}」下共 ${sortedPosts.length} 篇文章 · 按${sortLabel}`
      : `第 ${currentPage} 页，共 ${totalPages} 页 · 当前共 ${sortedPosts.length} 篇文章 · 按${sortLabel}`;
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
    renderPagination(1, 1, activeTag, activeSort);
    return;
  }

  if (!sortedPosts.length) {
    const empty = createElement("article", "empty-state");
    empty.append(
      createElement("h3", "", "当前标签暂无文章"),
      createElement("p", "", `标签「${activeTag}」下还没有文章，稍后再来看看。`)
    );
    container.appendChild(empty);
    renderPagination(1, 1, activeTag, activeSort);
    return;
  }

  const start = (currentPage - 1) * HOME_PAGE_SIZE;
  const pagePosts = sortedPosts.slice(start, start + HOME_PAGE_SIZE);

  pagePosts.forEach((post, index) => {
    const card = createElement("article", "post-card");

    const badge = createElement("span", "post-card__index", String(start + index + 1).padStart(2, "0"));
    const meta = createElement("p", "post-card__meta", createMetaLine(post));
    const title = createElement("h3", "post-card__title");
    const titleLink = createElement("a", "post-card__link", post.title);
    titleLink.href = buildPostHref(post.slug);
    title.appendChild(titleLink);

    const excerpt = createElement("div", "post-card__excerpt");
    renderMarkdownInto(excerpt, post.excerpt || "", { skipH1: true });
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

  renderPagination(totalPages, currentPage, activeTag, activeSort);
}

function renderArchivePostCards(container, posts) {
  clear(container);
  container.setAttribute("aria-busy", "false");

  posts.forEach((post, index) => {
    const card = createElement("article", "post-card");
    const badge = createElement("span", "post-card__index", String(index + 1).padStart(2, "0"));
    const meta = createElement("p", "post-card__meta", createMetaLine(post));
    const title = createElement("h3", "post-card__title");
    const titleLink = createElement("a", "post-card__link", post.title);
    titleLink.href = buildPostHref(post.slug);
    title.appendChild(titleLink);

    const excerpt = createElement("div", "post-card__excerpt");
    renderMarkdownInto(excerpt, post.excerpt || "", { skipH1: true });
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
}

function renderAuthorPage(posts) {
  const author = getAuthorFromQuery();
  const matchedPosts = posts.filter((post) => (post.author || "").trim() === author);
  const titleNode = qs("author-page-title");
  const descNode = qs("author-page-description");
  const statsNode = qs("author-page-stats");
  const countNode = qs("author-page-post-count");
  const postsNode = qs("author-page-posts");

  if (!postsNode) {
    return;
  }

  if (!author) {
    document.title = "作者归档 — lyfmt's Notes";
    setText("author-page-title", "未指定作者");
    setText("author-page-description", "请从首页作者区进入具体作者页面。" );
    clear(postsNode);
    postsNode.setAttribute("aria-busy", "false");
    const empty = createElement("article", "empty-state");
    empty.append(
      createElement("h3", "", "暂无作者信息"),
      createElement("p", "", "当前页面缺少 author 参数。")
    );
    postsNode.appendChild(empty);
    if (countNode) {
      countNode.textContent = "0 篇文章";
    }
    return;
  }

  document.title = `${author} — lyfmt's Notes`;
  if (titleNode) {
    titleNode.textContent = author;
  }
  if (descNode) {
    descNode.textContent = matchedPosts.length
      ? `这里聚合了 ${author} 的文章与更新时间。`
      : `暂时还没有找到作者「${author}」的文章。`;
  }

  if (statsNode) {
    clear(statsNode);
    statsNode.setAttribute("aria-busy", "false");
    const sources = new Set(matchedPosts.map((post) => post.source).filter(Boolean));
    const latest = matchedPosts[0]?.publishedAt || "";
    [
      [String(matchedPosts.length), "Posts"],
      [String(sources.size), "Sources"],
      [latest ? formatDate(latest) : "—", "Updated"]
    ].forEach(([value, label]) => {
      const card = createElement("article", "stat-card");
      card.append(
        createElement("span", "stat-card__value", value),
        createElement("span", "stat-card__label", label)
      );
      statsNode.appendChild(card);
    });
  }

  if (countNode) {
    countNode.textContent = `${matchedPosts.length} 篇文章`;
  }

  if (!matchedPosts.length) {
    clear(postsNode);
    postsNode.setAttribute("aria-busy", "false");
    const empty = createElement("article", "empty-state");
    empty.append(
      createElement("h3", "", "还没有文章"),
      createElement("p", "", `作者「${author}」当前没有可展示的文章。`)
    );
    postsNode.appendChild(empty);
    return;
  }

  renderArchivePostCards(postsNode, matchedPosts);
}

function renderTagPage(posts) {
  const tag = getTagFromQuery();
  const matchedPosts = filterPostsByTag(posts, tag);
  const titleNode = qs("tag-page-title");
  const descNode = qs("tag-page-description");
  const countNode = qs("tag-page-post-count");
  const postsNode = qs("tag-page-posts");

  if (!postsNode) {
    return;
  }

  if (!tag) {
    document.title = "标签归档 — lyfmt's Notes";
    setText("tag-page-title", "未指定标签");
    setText("tag-page-description", "请从首页标签区进入具体标签页面。" );
    clear(postsNode);
    postsNode.setAttribute("aria-busy", "false");
    const empty = createElement("article", "empty-state");
    empty.append(
      createElement("h3", "", "暂无标签信息"),
      createElement("p", "", "当前页面缺少 tag 参数。")
    );
    postsNode.appendChild(empty);
    if (countNode) {
      countNode.textContent = "0 篇文章";
    }
    return;
  }

  document.title = `${tag} — lyfmt's Notes`;
  if (titleNode) {
    titleNode.textContent = `标签：${tag}`;
  }
  if (descNode) {
    descNode.textContent = matchedPosts.length
      ? `这里展示标签「${tag}」下的全部文章。`
      : `标签「${tag}」当前还没有文章。`;
  }
  if (countNode) {
    countNode.textContent = `${matchedPosts.length} 篇文章`;
  }

  if (!matchedPosts.length) {
    clear(postsNode);
    postsNode.setAttribute("aria-busy", "false");
    const empty = createElement("article", "empty-state");
    empty.append(
      createElement("h3", "", "当前标签暂无文章"),
      createElement("p", "", `标签「${tag}」下还没有文章，稍后再来看看。`)
    );
    postsNode.appendChild(empty);
    return;
  }

  renderArchivePostCards(postsNode, matchedPosts);
}

function renderPostPager(post, posts, activeView) {
  if (!post || !Array.isArray(posts)) {
    return null;
  }

  const currentIndex = posts.findIndex((item) => item && item.slug === post.slug);
  if (currentIndex === -1) {
    return null;
  }

  const previousPost = currentIndex > 0 ? posts[currentIndex - 1] : null;
  const nextPost = currentIndex < posts.length - 1 ? posts[currentIndex + 1] : null;

  if (!previousPost && !nextPost) {
    return null;
  }

  const wrapper = createElement("section", "post-pager");
  const nav = createElement("nav", "post-pager__nav");
  nav.setAttribute("aria-label", "文章翻页");

  function createPagerLink(label, targetPost, modifierClass) {
    const link = createElement("a", `post-pager__link ${modifierClass}`);
    link.href = buildPostHref(targetPost.slug, activeView);
    link.setAttribute("aria-label", `${label}：${targetPost.title}`);

    const labelNode = createElement("span", "post-pager__label", label);
    const titleNode = createElement("span", "post-pager__title", targetPost.title);

    link.appendChild(labelNode);
    link.appendChild(titleNode);
    return link;
  }

  if (previousPost) {
    nav.appendChild(createPagerLink("上一篇", previousPost, "post-pager__link--prev"));
  }

  if (nextPost) {
    nav.appendChild(createPagerLink("下一篇", nextPost, "post-pager__link--next"));
  }

  wrapper.appendChild(nav);
  return wrapper;
}

function appendPostPager(article, post, posts, activeView) {
  if (!article || typeof article.appendChild !== "function") {
    return null;
  }

  const pager = renderPostPager(post, posts, activeView);
  if (!pager) {
    return null;
  }

  article.appendChild(pager);
  return pager;
}

function createPostViewHref(post, view) {
  return buildPostHref(post?.slug || "", view);
}

function renderPostViewSwitcher(post) {
  const container = qs("post-view-switcher");
  if (!container) {
    return;
  }

  clear(container);
  if (!post) {
    return;
  }

  const requestedView = getPostViewFromQuery();
  const detailAvailable = Boolean(post?.detail?.available);
  const activeView = requestedView === "detail" && detailAvailable ? "detail" : "summary";
  const row = createElement("div", "segmented-control");
  row.setAttribute("role", "tablist");
  row.setAttribute("aria-label", "文章视图切换");

  const summaryLink = createElement("a", `segmented-control__item${activeView === "summary" ? " is-active" : ""}`, "总结");
  summaryLink.href = createPostViewHref(post, "summary");
  summaryLink.setAttribute("role", "tab");
  summaryLink.setAttribute("aria-selected", String(activeView === "summary"));
  row.appendChild(summaryLink);

  const detailLink = createElement("a", `segmented-control__item${activeView === "detail" ? " is-active" : ""}${detailAvailable ? "" : " is-disabled"}`, detailAvailable ? "详情" : "详情（待补充）");
  detailLink.href = detailAvailable ? createPostViewHref(post, "detail") : "#";
  detailLink.setAttribute("role", "tab");
  detailLink.setAttribute("aria-selected", String(activeView === "detail"));
  if (!detailAvailable) {
    detailLink.setAttribute("aria-disabled", "true");
    detailLink.tabIndex = -1;
  }
  row.appendChild(detailLink);

  container.appendChild(row);
}

function renderSummaryContent(post) {
  const contentWrap = createElement("div", "article-content");
  const sections = Array.isArray(post.content) ? post.content : [];

  sections.forEach((section) => {
    const sectionNode = createElement("section", "article-section");

    if (typeof section === "string") {
      renderMarkdownInto(sectionNode, section, { skipH1: true });
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
          renderMarkdownInto(sectionNode, paragraph.trim(), { skipH1: true });
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

  return contentWrap;
}

function renderDetailBlocks(detail) {
  const contentWrap = createElement("div", "article-content");

  if (detail?.sourceDescription) {
    contentWrap.appendChild(createElement("p", "article-mode-note", detail.sourceDescription));
  }

  const blocks = Array.isArray(detail?.blocks) ? detail.blocks : [];

  blocks.forEach((block) => {
    if (!block || typeof block !== "object") {
      return;
    }

    if (block.type === "paragraph") {
      const section = createElement("section", "article-section");
      const p = createElement("p");
      p.innerHTML = block.html || "";
      section.appendChild(p);
      contentWrap.appendChild(section);
      return;
    }

    if (block.type === "heading") {
      const section = createElement("section", "article-section");
      const level = Number.isFinite(block.level) ? block.level : 2;
      const tag = level >= 3 ? "h3" : "h2";
      section.appendChild(createElement(tag, "article-section__title", block.text || ""));
      contentWrap.appendChild(section);
      return;
    }

    if (block.type === "list") {
      const section = createElement("section", "article-section");
      const list = createElement("ul");
      (Array.isArray(block.items) ? block.items : []).forEach((item) => {
        const li = createElement("li");
        li.innerHTML = typeof item === "string" ? item : "";
        list.appendChild(li);
      });
      if (list.childNodes.length) {
        section.appendChild(list);
        contentWrap.appendChild(section);
      }
      return;
    }

    if (block.type === "image") {
      const section = createElement("section", "article-section");
      const figure = createElement("figure", "article-figure");
      const img = document.createElement("img");
      img.src = block.src || "";
      img.alt = block.alt || "";
      img.loading = "lazy";
      figure.appendChild(img);
      if (block.caption) {
        figure.appendChild(createElement("figcaption", "", block.caption));
      }
      section.appendChild(figure);
      contentWrap.appendChild(section);
      return;
    }

    if (block.type === "embed") {
      const section = createElement("section", "article-section");
      const iframe = document.createElement("iframe");
      iframe.className = "article-embed";
      iframe.src = block.src || "";
      iframe.title = block.title || "Embedded media";
      iframe.loading = "lazy";
      iframe.allowFullscreen = true;
      section.appendChild(iframe);
      contentWrap.appendChild(section);
      return;
    }

    if (block.type === "footnote") {
      const section = createElement("section", "article-section article-footnote");
      const p = createElement("p");
      p.innerHTML = block.html || "";
      section.appendChild(p);
      contentWrap.appendChild(section);
    }
  });

  if (!contentWrap.childNodes.length) {
    const empty = createElement("section", "empty-state empty-state--compact");
    empty.append(
      createElement("h3", "", "详情内容待补充"),
      createElement("p", "", "当前文章还没有可渲染的原文翻译详情。")
    );
    contentWrap.appendChild(empty);
  }

  return contentWrap;
}

function renderPost(post, relatedPosts) {
  const article = qs("post-article");

  if (!article) {
    return;
  }

  const excerptTitle = extractMarkdownTitle(post?.excerpt || "");
  if (excerptTitle) {
    post.title = excerptTitle;
  }

  renderPostViewSwitcher(post);
  clear(article);
  article.setAttribute("aria-busy", "false");

  if (!post) {
    const empty = createElement("section", "empty-state");
    empty.append(
      createElement("h2", "", "未找到文章"),
      createElement("p", "", "请从首页重新选择文章。")
    );
    article.appendChild(empty);
    document.title = "文章未找到 — lyfmt's Notes";
    return;
  }

  const activeView = getPostViewFromQuery();
  const effectiveView = activeView === "detail" && post?.detail?.available ? "detail" : "summary";
  article.dataset.viewMode = effectiveView;
  article.dataset.detailLayout = effectiveView === "detail" ? (post?.detail?.layout || "default") : "summary";
  document.title = `${post.title} — ${effectiveView === "detail" ? "详情" : "总结"} — lyfmt's Notes`;

  const header = createElement("header", "article-header");
  const source = createElement("p", "eyebrow", effectiveView === "detail" ? `${post.source || "Post"} · 原文译文` : post.source || "Post");
  const title = createElement("h1", "article-title", post.title);
  const meta = createElement("p", "article-meta", createMetaLine(post));
  const excerpt = createElement("div", "article-excerpt");
  renderMarkdownInto(excerpt, post.excerpt || "", { skipH1: true });

  header.append(source, title);
  if (meta.textContent) {
    header.appendChild(meta);
  }

  const excerptIsMarkdown = typeof post.excerpt === "string" && post.excerpt.trim().startsWith("# ");
  if (!(effectiveView === "summary" && excerptIsMarkdown) && excerpt.textContent) {
    header.appendChild(excerpt);
  }

  const headerTags = createTagRow(post.tags);
  if (headerTags) {
    header.appendChild(headerTags);
  }

  if (effectiveView === "detail" && post?.detail?.translatedFrom) {
    const sourceNote = createElement("p", "article-meta", `详情视图基于原文逐段翻译与原结构重排：${post.detail.sourceName || post.source || "原站"}`);
    header.appendChild(sourceNote);
  }

  const sourceLink = createElement("a", "article-source-link", effectiveView === "detail" ? "查看原始英文文章 ↗" : "查看原文 ↗");
  sourceLink.href = post.url;
  sourceLink.target = "_blank";
  sourceLink.rel = "noreferrer noopener";
  header.appendChild(sourceLink);

  article.appendChild(header);

  const contentWrap = effectiveView === "detail"
    ? renderDetailBlocks(post.detail)
    : renderSummaryContent(post);

  article.appendChild(contentWrap);
  appendPostPager(article, post, relatedPosts, effectiveView);
}

function renderError(message) {
  const targetIds = ["home-posts", "author-list", "pagination", "post-article"];

  targetIds.forEach((id) => {
    const node = qs(id);
    if (!node) {
      return;
    }

    // related-posts removed

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
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    const data = await response.json();
    const site = data && typeof data.site === "object" ? data.site : {};
    const posts = applyExcerptTitleToPosts(validatePosts(data?.posts));

    cachedSite = site;
    cachedPosts = posts;
    hasLoadedBlog = true;

    if (pageType === "author") {
      renderAuthorPage(posts);
      return;
    }

    if (pageType === "tag") {
      renderTagPage(posts);
      return;
    }

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
initMobileHeaderBehavior();
initHomeNavigation();
void loadBlog();
