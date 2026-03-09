const THEME_KEY = "pi-blog-demo-theme";
const DATA_URL = "./articles.json";
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
  const seen = new Set();
  const tags = [];

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
      if (seen.has(key)) {
        return;
      }

      seen.add(key);
      tags.push(value);
    });
  });

  return tags;
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

function renderTagFilters(tags, activeTag) {
  const container = qs("tag-filter-list");
  if (!container) {
    return;
  }

  clear(container);

  const row = createElement("div", "tag-row");
  row.appendChild(createTagFilterChip("全部", buildIndexHref(1), !normalizeTag(activeTag)));

  tags.forEach((tag) => {
    const isActive = normalizeTag(tag) === normalizeTag(activeTag);
    row.appendChild(createTagFilterChip(tag, buildIndexHref(1, tag), isActive));
  });

  container.appendChild(row);
}

function buildPostHref(slug) {
  return `./post.html?slug=${encodeURIComponent(slug)}`;
}

function buildAuthorHref(author) {
  const params = new URLSearchParams({ author: author.trim() });
  return `./author.html?${params.toString()}`;
}

function buildTagHref(tag) {
  const params = new URLSearchParams({ tag: tag.trim() });
  return `./tag.html?${params.toString()}`;
}

function buildIndexHref(page, tag) {
  const params = new URLSearchParams();
  const trimmedTag = typeof tag === "string" ? tag.trim() : "";

  if (page > 1) {
    params.set("page", String(page));
  }

  if (trimmedTag) {
    params.set("tag", trimmedTag);
  }

  const query = params.toString();
  return query ? `./index.html?${query}` : "./index.html";
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

function getAuthorFromQuery() {
  const author = new URLSearchParams(window.location.search).get("author");
  return author ? author.trim() : "";
}

function getTagFromQuery() {
  return new URLSearchParams(window.location.search).get("tag")?.trim() || "";
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

function renderCurrentHomePage() {
  if (pageType !== "home" || !hasLoadedBlog) {
    return;
  }

  renderHome(cachedSite || {}, Array.isArray(cachedPosts) ? cachedPosts : []);
}

function initHomeNavigation() {
  if (pageType !== "home") {
    return;
  }

  document.addEventListener("click", (event) => {
    const link = event.target.closest("#pagination a, #tag-filter-list a");
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
    renderCurrentHomePage();
  });

  window.addEventListener("popstate", () => {
    if (!hasLoadedBlog || !isHomePathname(window.location.pathname)) {
      return;
    }

    renderCurrentHomePage();
  });
}

function renderFeatured(site, posts, activeTag) {
  const siteTitle = typeof site?.title === "string" && site.title.trim()
    ? site.title.trim()
    : "Agent Notes Demo";
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
  setText("featured-excerpt", featured.excerpt || "这篇文章暂无摘要。");
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

function renderPagination(totalPages, currentPage, activeTag) {
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
        link.href = buildIndexHref(currentPage - 1, activeTag);
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
      link.href = buildIndexHref(page, activeTag);
      container.appendChild(link);
    }
  }

  const next = currentPage < totalPages
    ? (() => {
        const link = createElement("a", "pagination__link", "下一页 →");
        link.href = buildIndexHref(currentPage + 1, activeTag);
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
  const activeTag = getTagFromQuery();
  const allTags = collectTags(posts);
  const filteredPosts = filterPostsByTag(posts, activeTag);
  const featuredPosts = filteredPosts.length ? filteredPosts : posts;
  const requestedPage = getPageFromQuery();
  const totalPages = Math.max(1, Math.ceil(filteredPosts.length / HOME_PAGE_SIZE));
  const currentPage = Math.min(Math.max(1, requestedPage), totalPages);

  document.title = activeTag
    ? `${siteTitle} — ${activeTag}`
    : currentPage > 1 ? `${siteTitle} — Page ${currentPage}` : siteTitle;

  if (description && site?.description) {
    description.textContent = site.description;
  }

  renderTagFilters(allTags, activeTag);
  renderFeatured(site, featuredPosts, activeTag);
  renderStats(posts);
  renderAuthors(posts);

  if (count) {
    count.textContent = activeTag
      ? `标签「${activeTag}」下共 ${filteredPosts.length} 篇文章`
      : `第 ${currentPage} 页，共 ${totalPages} 页 · 当前共 ${filteredPosts.length} 篇文章`;
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
    renderPagination(1, 1, activeTag);
    return;
  }

  if (!filteredPosts.length) {
    const empty = createElement("article", "empty-state");
    empty.append(
      createElement("h3", "", "当前标签暂无文章"),
      createElement("p", "", `标签「${activeTag}」下还没有文章，稍后再来看看。`)
    );
    container.appendChild(empty);
    renderPagination(1, 1, activeTag);
    return;
  }

  const start = (currentPage - 1) * HOME_PAGE_SIZE;
  const pagePosts = filteredPosts.slice(start, start + HOME_PAGE_SIZE);

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

  renderPagination(totalPages, currentPage, activeTag);
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
    document.title = "Author — Agent Notes Demo";
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

  document.title = `${author} — Agent Notes Demo`;
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
    document.title = "Tag — Agent Notes Demo";
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

  document.title = `${tag} — Agent Notes Demo`;
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

function renderPostPager(post, posts) {
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
    link.href = buildPostHref(targetPost.slug);
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

function appendPostPager(article, post, posts) {
  if (!article || typeof article.appendChild !== "function") {
    return null;
  }

  const pager = renderPostPager(post, posts);
  if (!pager) {
    return null;
  }

  article.appendChild(pager);
  return pager;
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
  appendPostPager(article, post, relatedPosts);

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
initHomeNavigation();
void loadBlog();
