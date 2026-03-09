const THEME_KEY = "pi-blog-demo-theme";

const themeToggle = document.getElementById("theme-toggle");
const postList = document.getElementById("post-list");
const postDetail = document.getElementById("post-detail");

const state = {
  site: {},
  posts: [],
  selectedSlug: ""
};

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

  if (document.body) {
    document.body.dataset.theme = nextTheme;
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

function setBusy(isBusy) {
  const value = String(Boolean(isBusy));

  if (postList) {
    postList.setAttribute("aria-busy", value);
  }

  if (postDetail) {
    postDetail.setAttribute("aria-busy", value);
  }
}

function applyStyles(element, styles) {
  Object.assign(element.style, styles);
  return element;
}

function clearNode(node) {
  if (node) {
    node.replaceChildren();
  }
}

function createTextElement(tagName, text, styles) {
  const element = document.createElement(tagName);
  element.textContent = text;

  if (styles) {
    applyStyles(element, styles);
  }

  return element;
}

function createMessageCard(title, message, detail, isError) {
  const card = document.createElement("section");

  if (isError) {
    card.setAttribute("role", "alert");
  }

  applyStyles(card, {
    display: "grid",
    gap: "0.75rem",
    padding: "1rem",
    borderRadius: "1rem",
    border: isError
      ? "1px solid rgba(220, 38, 38, 0.35)"
      : "1px solid var(--border, rgba(15, 23, 42, 0.1))",
    background: isError
      ? "rgba(220, 38, 38, 0.08)"
      : "var(--surface-soft, rgba(255, 255, 255, 0.7))"
  });

  card.appendChild(
    createTextElement("h2", title, {
      margin: "0",
      fontSize: "1.1rem",
      lineHeight: "1.3",
      color: "var(--heading, #0f172a)"
    })
  );

  card.appendChild(
    createTextElement("p", message, {
      margin: "0",
      color: "var(--text, #162033)",
      lineHeight: "1.7"
    })
  );

  if (detail) {
    card.appendChild(
      createTextElement("p", detail, {
        margin: "0",
        fontSize: "0.95rem",
        color: "var(--text-soft, #4f5d73)",
        lineHeight: "1.6"
      })
    );
  }

  return card;
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

function getHashSlug() {
  const rawHash = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;

  if (!rawHash) {
    return "";
  }

  try {
    return decodeURIComponent(rawHash);
  } catch {
    return rawHash;
  }
}

function toHash(slug) {
  return `#${encodeURIComponent(slug)}`;
}

function replaceHash(slug) {
  if (!slug) {
    return;
  }

  const nextHash = toHash(slug);

  if (window.location.hash === nextHash) {
    return;
  }

  if (window.history && typeof window.history.replaceState === "function") {
    const nextUrl = `${window.location.pathname}${window.location.search}${nextHash}`;
    window.history.replaceState(null, "", nextUrl);
    return;
  }

  window.location.hash = nextHash;
}

function updateHash(slug) {
  if (!slug) {
    return;
  }

  const nextHash = toHash(slug);

  if (window.location.hash === nextHash) {
    renderSelectedPost(slug);
    return;
  }

  window.location.hash = nextHash;
}

function isValidPost(post) {
  return Boolean(post && typeof post.slug === "string" && typeof post.title === "string");
}

function getPosts() {
  return state.posts;
}

function findPostBySlug(slug) {
  return getPosts().find((post) => post.slug === slug) || null;
}

function createTagList(tags) {
  const safeTags = Array.isArray(tags)
    ? tags.filter((tag) => typeof tag === "string" && tag.trim())
    : [];

  if (!safeTags.length) {
    return null;
  }

  const list = document.createElement("div");
  applyStyles(list, {
    display: "flex",
    flexWrap: "wrap",
    gap: "0.45rem"
  });

  safeTags.forEach((tag) => {
    const item = createTextElement("span", tag.trim(), {
      display: "inline-flex",
      alignItems: "center",
      padding: "0.22rem 0.65rem",
      borderRadius: "999px",
      background: "var(--accent-soft, rgba(51, 102, 255, 0.12))",
      color: "var(--heading, #0f172a)",
      fontSize: "0.82rem",
      fontWeight: "600",
      lineHeight: "1.4"
    });

    list.appendChild(item);
  });

  return list;
}

function createMetaText(post) {
  return [post.author, formatDate(post.publishedAt), post.source]
    .filter((part) => typeof part === "string" && part.trim())
    .join(" • ");
}

function createPostButton(post, isSelected) {
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.slug = post.slug;
  button.setAttribute("aria-pressed", String(isSelected));

  if (isSelected) {
    button.setAttribute("aria-current", "true");
  }

  applyStyles(button, {
    width: "100%",
    display: "grid",
    gap: "0.55rem",
    padding: "1rem",
    textAlign: "left",
    borderRadius: "1rem",
    border: isSelected
      ? "1px solid var(--accent, #3366ff)"
      : "1px solid var(--border, rgba(15, 23, 42, 0.1))",
    background: isSelected
      ? "var(--accent-soft, rgba(51, 102, 255, 0.12))"
      : "var(--surface-soft, rgba(255, 255, 255, 0.7))",
    color: "inherit",
    cursor: "pointer",
    boxShadow: isSelected ? "0 10px 24px rgba(51, 102, 255, 0.12)" : "none"
  });

  button.appendChild(
    createTextElement("strong", post.title, {
      color: "var(--heading, #0f172a)",
      fontSize: "1rem",
      lineHeight: "1.4"
    })
  );

  const metaText = createMetaText(post);
  if (metaText) {
    button.appendChild(
      createTextElement("span", metaText, {
        color: "var(--text-soft, #4f5d73)",
        fontSize: "0.88rem",
        lineHeight: "1.5"
      })
    );
  }

  if (typeof post.excerpt === "string" && post.excerpt.trim()) {
    button.appendChild(
      createTextElement("span", post.excerpt.trim(), {
        color: "var(--text, #162033)",
        fontSize: "0.95rem",
        lineHeight: "1.65"
      })
    );
  }

  const tagList = createTagList(post.tags);
  if (tagList) {
    button.appendChild(tagList);
  }

  button.addEventListener("click", () => {
    updateHash(post.slug);
  });

  return button;
}

function renderPostList() {
  if (!postList) {
    return;
  }

  clearNode(postList);

  const wrapper = document.createElement("div");
  applyStyles(wrapper, {
    display: "grid",
    gap: "1rem"
  });

  const siteTitle = typeof state.site.title === "string" && state.site.title.trim()
    ? state.site.title.trim()
    : "Posts";
  const siteDescription = typeof state.site.description === "string" && state.site.description.trim()
    ? state.site.description.trim()
    : "";

  const header = document.createElement("section");
  applyStyles(header, {
    display: "grid",
    gap: "0.5rem"
  });

  header.appendChild(
    createTextElement("h2", siteTitle, {
      margin: "0",
      color: "var(--heading, #0f172a)",
      fontSize: "1.35rem",
      lineHeight: "1.25"
    })
  );

  if (siteDescription) {
    header.appendChild(
      createTextElement("p", siteDescription, {
        margin: "0",
        color: "var(--text-soft, #4f5d73)",
        lineHeight: "1.7"
      })
    );
  }

  wrapper.appendChild(header);

  const posts = getPosts();
  if (!posts.length) {
    wrapper.appendChild(
      createMessageCard(
        "No posts available",
        "articles.json loaded, but there are no posts to show.",
        "Add at least one post object to the posts array.",
        false
      )
    );
    postList.appendChild(wrapper);
    return;
  }

  const list = document.createElement("div");
  applyStyles(list, {
    display: "grid",
    gap: "0.85rem"
  });

  posts.forEach((post) => {
    list.appendChild(createPostButton(post, post.slug === state.selectedSlug));
  });

  wrapper.appendChild(list);
  postList.appendChild(wrapper);
}

function createSectionParagraph(text) {
  return createTextElement("p", text, {
    margin: "0",
    color: "var(--text, #162033)",
    lineHeight: "1.8"
  });
}

function renderContentSections(container, content) {
  const sections = Array.isArray(content) ? content : [];

  if (!sections.length) {
    container.appendChild(
      createMessageCard(
        "No content available",
        "This post does not have any content sections yet.",
        "Populate the content array in articles.json.",
        false
      )
    );
    return;
  }

  sections.forEach((entry) => {
    const section = document.createElement("section");
    applyStyles(section, {
      display: "grid",
      gap: "0.75rem"
    });

    if (typeof entry === "string" && entry.trim()) {
      section.appendChild(createSectionParagraph(entry.trim()));
      container.appendChild(section);
      return;
    }

    if (!entry || typeof entry !== "object") {
      return;
    }

    if (typeof entry.heading === "string" && entry.heading.trim()) {
      section.appendChild(
        createTextElement("h3", entry.heading.trim(), {
          margin: "0",
          color: "var(--heading, #0f172a)",
          fontSize: "1.15rem",
          lineHeight: "1.35"
        })
      );
    }

    const paragraphs = Array.isArray(entry.paragraphs)
      ? entry.paragraphs.filter((paragraph) => typeof paragraph === "string" && paragraph.trim())
      : [];

    paragraphs.forEach((paragraph) => {
      section.appendChild(createSectionParagraph(paragraph.trim()));
    });

    if (section.childNodes.length) {
      container.appendChild(section);
    }
  });

  if (!container.childNodes.length) {
    container.appendChild(
      createMessageCard(
        "No content available",
        "This post does not have any renderable content sections.",
        "Check the content array shape in articles.json.",
        false
      )
    );
  }
}

function updateDocumentTitle(post) {
  const siteTitle = typeof state.site.title === "string" && state.site.title.trim()
    ? state.site.title.trim()
    : "Blog";

  document.title = post ? `${post.title} — ${siteTitle}` : siteTitle;
}

function renderPostDetail(post) {
  if (!postDetail) {
    return;
  }

  clearNode(postDetail);

  if (!post) {
    postDetail.appendChild(
      createMessageCard(
        "No post selected",
        "Choose a post from the list to view its details.",
        "",
        false
      )
    );
    updateDocumentTitle(null);
    return;
  }

  const article = document.createElement("article");
  applyStyles(article, {
    display: "grid",
    gap: "1.25rem"
  });

  const header = document.createElement("header");
  applyStyles(header, {
    display: "grid",
    gap: "0.75rem"
  });

  header.appendChild(
    createTextElement("p", post.source || "Post", {
      margin: "0",
      color: "var(--text-soft, #4f5d73)",
      fontSize: "0.92rem",
      fontWeight: "600",
      lineHeight: "1.5"
    })
  );

  header.appendChild(
    createTextElement("h2", post.title, {
      margin: "0",
      color: "var(--heading, #0f172a)",
      fontSize: "clamp(1.75rem, 3vw, 2.5rem)",
      lineHeight: "1.15"
    })
  );

  const metaText = createMetaText(post);
  if (metaText) {
    header.appendChild(
      createTextElement("p", metaText, {
        margin: "0",
        color: "var(--text-soft, #4f5d73)",
        lineHeight: "1.6"
      })
    );
  }

  if (typeof post.excerpt === "string" && post.excerpt.trim()) {
    header.appendChild(
      createTextElement("p", post.excerpt.trim(), {
        margin: "0",
        color: "var(--text, #162033)",
        lineHeight: "1.75",
        fontSize: "1rem"
      })
    );
  }

  const headerTags = createTagList(post.tags);
  if (headerTags) {
    header.appendChild(headerTags);
  }

  if (typeof post.url === "string" && post.url.trim()) {
    const sourceLink = document.createElement("a");
    sourceLink.href = post.url;
    sourceLink.target = "_blank";
    sourceLink.rel = "noreferrer noopener";
    sourceLink.textContent = "Open original article";
    applyStyles(sourceLink, {
      color: "var(--accent, #3366ff)",
      fontWeight: "600",
      lineHeight: "1.6"
    });
    header.appendChild(sourceLink);
  }

  article.appendChild(header);

  const content = document.createElement("div");
  applyStyles(content, {
    display: "grid",
    gap: "1.5rem"
  });

  renderContentSections(content, post.content);
  article.appendChild(content);

  postDetail.appendChild(article);
  updateDocumentTitle(post);
}

function renderSelectedPost(slug) {
  const posts = getPosts();

  if (!posts.length) {
    state.selectedSlug = "";
    renderPostList();
    renderPostDetail(null);
    return;
  }

  const post = findPostBySlug(slug) || posts[0];
  state.selectedSlug = post.slug;
  renderPostList();
  renderPostDetail(post);
}

function syncSelectionWithHash() {
  const posts = getPosts();

  if (!posts.length) {
    renderSelectedPost("");
    return;
  }

  const slugFromHash = getHashSlug();
  const matchedPost = slugFromHash ? findPostBySlug(slugFromHash) : null;
  const nextPost = matchedPost || posts[0];

  if (!slugFromHash || !matchedPost) {
    replaceHash(nextPost.slug);
  }

  renderSelectedPost(nextPost.slug);
}

function renderFetchError(error) {
  const detail = error instanceof Error && error.message ? error.message : "Unknown error.";

  if (postList) {
    clearNode(postList);
    postList.appendChild(
      createMessageCard(
        "Failed to load posts",
        "The page could not load ./articles.json.",
        detail,
        true
      )
    );
  }

  if (postDetail) {
    clearNode(postDetail);
    postDetail.appendChild(
      createMessageCard(
        "Content unavailable",
        "Post details are unavailable because the content source could not be loaded.",
        detail,
        true
      )
    );
  }

  console.error(error);
}

async function loadBlog() {
  setBusy(true);

  try {
    const response = await fetch("./articles.json");

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    const data = await response.json();
    const posts = Array.isArray(data && data.posts)
      ? data.posts.filter(isValidPost)
      : [];

    state.site = data && typeof data.site === "object" && data.site ? data.site : {};
    state.posts = posts;

    syncSelectionWithHash();
  } catch (error) {
    state.site = {};
    state.posts = [];
    state.selectedSlug = "";
    renderFetchError(error);
  } finally {
    setBusy(false);
  }
}

window.addEventListener("hashchange", () => {
  if (!getPosts().length) {
    return;
  }

  syncSelectionWithHash();
});

initThemeToggle();
void loadBlog();
