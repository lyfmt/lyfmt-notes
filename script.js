const THEME_KEY = "pi-blog-demo-theme";
const DATA_URL = "./articles.json";

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

function createTag(tagText) {
  const item = createElement("span", "tag", tagText);
  return item;
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

function createMetaLine(post) {
  return [post.author, formatDate(post.publishedAt), post.source]
    .filter((part) => typeof part === "string" && part.trim())
    .join(" • ");
}

function renderHome(site, posts) {
  const description = qs("home-description");
  const count = qs("post-count");
  const container = qs("home-posts");

  if (!container) {
    return;
  }

  if (description && site?.description) {
    description.textContent = site.description;
  }

  if (count) {
    count.textContent = `${posts.length} 篇文章`;
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
    return;
  }

  posts.forEach((post, index) => {
    const card = createElement("article", "post-card");

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

    const indexBadge = createElement("span", "post-card__index", String(index + 1).padStart(2, "0"));

    card.append(indexBadge, meta, title, excerpt, footer);
    container.appendChild(card);
  });
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
  const targetIds = ["home-posts", "post-article", "related-posts"];

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
