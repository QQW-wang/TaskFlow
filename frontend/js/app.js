"use strict";

/**
 * TaskFlow 前端逻辑。
 * 这是一个刻意保持简单的原生 JS 页面，方便把注意力放在后端接口上。
 * 如果后端端口不是 8000，只需要修改下面的 API_BASE。
 */
const API_BASE = "http://127.0.0.1:8000/api/v1";
const TOKEN_KEY = "taskflow_token";

const STATUS_LABELS = {
  todo: "待开始",
  in_progress: "进行中",
  done: "已完成",
};

const PRIORITY_LABELS = {
  low: "低优先级",
  medium: "中优先级",
  high: "高优先级",
};

const FILTER_LABELS = {
  all: "全部任务",
  todo: "待开始",
  in_progress: "进行中",
  done: "已完成",
};

const state = {
  token: localStorage.getItem(TOKEN_KEY) || "",
  user: null,
  tasks: [],
  stats: null,
  filter: "all",
  keyword: "",
  page: 1,
  pageSize: 8,
  pages: 0,
  total: 0,
  editingId: null,
};

const $ = (id) => document.getElementById(id);

const els = {
  authView: $("authView"),
  appView: $("appView"),
  authTitle: $("authTitle"),
  authSubtitle: $("authSubtitle"),
  loginForm: $("loginForm"),
  loginError: $("loginError"),
  registerForm: $("registerForm"),
  registerError: $("registerError"),
  userName: $("userName"),
  userEmail: $("userEmail"),
  userAvatar: $("userAvatar"),
  logoutBtn: $("logoutBtn"),
  todayLabel: $("todayLabel"),
  pageGreeting: $("pageGreeting"),
  searchInput: $("searchInput"),
  newTaskBtn: $("newTaskBtn"),
  statTotal: $("statTotal"),
  statTodo: $("statTodo"),
  statProgress: $("statProgress"),
  statRate: $("statRate"),
  statProgressBar: $("statProgressBar"),
  sidebarRate: $("sidebarRate"),
  sidebarProgress: $("sidebarProgress"),
  sidebarProgressText: $("sidebarProgressText"),
  listTitle: $("listTitle"),
  listMeta: $("listMeta"),
  taskList: $("taskList"),
  emptyState: $("emptyState"),
  emptyText: $("emptyText"),
  emptyCreateBtn: $("emptyCreateBtn"),
  pagination: $("pagination"),
  prevPage: $("prevPage"),
  pageInfo: $("pageInfo"),
  nextPage: $("nextPage"),
  taskModal: $("taskModal"),
  taskModalTitle: $("taskModalTitle"),
  taskForm: $("taskForm"),
  taskId: $("taskId"),
  taskTitle: $("taskTitle"),
  taskDescription: $("taskDescription"),
  taskStatus: $("taskStatus"),
  taskPriority: $("taskPriority"),
  taskDueDate: $("taskDueDate"),
  taskError: $("taskError"),
  taskSubmitBtn: $("taskSubmitBtn"),
  toast: $("toast"),
};

let searchTimer = null;
let toastTimer = null;

/* ---------- 通用工具 ---------- */

function createEl(tag, className = "", text = null) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== null) element.textContent = text;
  return element;
}

function setFormError(element, message) {
  element.textContent = message || "";
}

function showToast(message, type = "success") {
  window.clearTimeout(toastTimer);
  els.toast.textContent = message;
  els.toast.dataset.type = type;
  els.toast.classList.add("is-visible");
  toastTimer = window.setTimeout(() => {
    els.toast.classList.remove("is-visible");
  }, 2800);
}

async function withButton(button, action) {
  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = "请稍候...";
  try {
    return await action();
  } finally {
    button.disabled = false;
    button.textContent = originalText;
  }
}

function extractError(data) {
  if (!data) return "请求失败，请稍后重试";
  const detail = data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = Array.isArray(item.loc) ? item.loc.slice(1).join(".") : "参数";
        return `${field}：${item.msg}`;
      })
      .join("；");
  }
  return "请求失败，请稍后重试";
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (state.token) {
    headers.set("Authorization", `Bearer ${state.token}`);
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch {
    throw new Error("无法连接后端，请确认 uvicorn 已在 8000 端口启动");
  }

  if (response.status === 401 && state.token) {
    logout(false);
    throw new Error("登录已过期，请重新登录");
  }

  let data = null;
  if (response.status !== 204) {
    const text = await response.text();
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = null;
      }
    }
  }

  if (!response.ok) {
    throw new Error(extractError(data));
  }
  return data;
}

/* ---------- 登录 / 注册 ---------- */

function switchAuthTab(tab) {
  const isLogin = tab === "login";
  document.querySelectorAll("[data-auth-tab]").forEach((button) => {
    const active = button.dataset.authTab === tab;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", String(active));
  });

  els.loginForm.classList.toggle("is-hidden", !isLogin);
  els.registerForm.classList.toggle("is-hidden", isLogin);
  els.authTitle.textContent = isLogin ? "欢迎回来" : "创建你的账号";
  els.authSubtitle.textContent = isLogin
    ? "登录后继续管理你的任务。"
    : "只需几步，就能拥有自己的任务空间。";
  setFormError(els.loginError, "");
  setFormError(els.registerError, "");
}

function showAuth() {
  els.appView.classList.add("is-hidden");
  els.authView.classList.remove("is-hidden");
  setFormError(els.loginError, "");
  setFormError(els.registerError, "");
}

function showApp() {
  els.authView.classList.add("is-hidden");
  els.appView.classList.remove("is-hidden");

  const username = state.user?.username || "用户";
  els.userName.textContent = username;
  els.userEmail.textContent = state.user?.email || "—";
  els.userAvatar.textContent = Array.from(username)[0]?.toUpperCase() || "U";

  const hour = new Date().getHours();
  let greeting = "晚上好";
  if (hour < 6) greeting = "夜深了";
  else if (hour < 12) greeting = "早上好";
  else if (hour < 18) greeting = "下午好";
  els.pageGreeting.textContent = `${greeting}，${username}`;
  setDateLabel();
}

function persistSession(data) {
  state.token = data.access_token;
  state.user = data.user;
  localStorage.setItem(TOKEN_KEY, state.token);
  showApp();
}

async function afterLoggedIn(data, message) {
  persistSession(data);
  setLoading();
  try {
    await refreshAll();
  } catch (error) {
    showToast(error.message, "error");
  }
  showToast(message || `欢迎回来，${state.user.username}`);
}

function logout(notify = true) {
  state.token = "";
  state.user = null;
  state.tasks = [];
  state.stats = null;
  state.filter = "all";
  state.keyword = "";
  state.page = 1;
  state.pages = 0;
  state.total = 0;
  localStorage.removeItem(TOKEN_KEY);
  els.searchInput.value = "";
  syncFilterUI();
  showAuth();
  if (notify) showToast("已退出登录");
}

/* ---------- 任务数据 ---------- */

function setDateLabel() {
  const now = new Date();
  const weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
  els.todayLabel.textContent = `${now.getFullYear()} 年 ${now.getMonth() + 1} 月 ${now.getDate()} 日 · ${weekdays[now.getDay()]}`;
}

function setLoading() {
  els.emptyState.classList.add("is-hidden");
  els.taskList.classList.remove("is-hidden");
  els.pagination.classList.add("is-hidden");
  els.taskList.replaceChildren(createEl("div", "loading-state", "正在加载任务…"));
}

function syncFilterUI() {
  document.querySelectorAll("[data-filter]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.filter === state.filter);
  });
  els.listTitle.textContent = FILTER_LABELS[state.filter] || "任务";
}

async function refreshAll() {
  await Promise.all([loadTasks(), loadStats()]);
}

async function loadTasks() {
  const params = new URLSearchParams({
    page: String(state.page),
    page_size: String(state.pageSize),
  });
  if (state.filter !== "all") params.set("status", state.filter);
  if (state.keyword) params.set("keyword", state.keyword);

  const data = await api(`/tasks?${params.toString()}`);
  if (data.pages > 0 && state.page > data.pages) {
    state.page = data.pages;
    return loadTasks();
  }
  if (data.total === 0) state.page = 1;

  state.tasks = data.items;
  state.total = data.total;
  state.pages = data.pages;
  renderTasks();
  updateListMeta();
  updatePagination();
}

async function loadStats() {
  state.stats = await api("/tasks/stats");
  renderStats();
}

function renderStats() {
  const stats = state.stats || {
    total: 0,
    todo: 0,
    in_progress: 0,
    done: 0,
    completion_rate: 0,
  };
  const counts = {
    all: stats.total,
    todo: stats.todo,
    in_progress: stats.in_progress,
    done: stats.done,
  };

  els.statTotal.textContent = String(stats.total);
  els.statTodo.textContent = String(stats.todo);
  els.statProgress.textContent = String(stats.in_progress);
  els.statRate.textContent = `${stats.completion_rate}%`;
  els.statProgressBar.style.width = `${Math.min(Number(stats.completion_rate) || 0, 100)}%`;

  els.sidebarRate.textContent = `${stats.completion_rate}%`;
  els.sidebarProgress.style.width = `${Math.min(Number(stats.completion_rate) || 0, 100)}%`;
  els.sidebarProgressText.textContent = stats.total
    ? `${stats.done} / ${stats.total} 件已完成`
    : "添加第一个任务，开始今天的计划。";

  document.querySelectorAll("[data-count]").forEach((element) => {
    const key = element.dataset.count;
    element.textContent = String(counts[key] ?? 0);
  });
}

function updateListMeta() {
  const parts = [`共 ${state.total} 件`];
  if (state.keyword) parts.push(`关键词“${state.keyword}”`);
  els.listMeta.textContent = parts.join(" · ");
}

function updatePagination() {
  const hasTasks = state.total > 0;
  els.pagination.classList.toggle("is-hidden", !hasTasks);
  if (!hasTasks) return;

  els.pageInfo.textContent = `第 ${state.page} / ${Math.max(state.pages, 1)} 页`;
  els.prevPage.disabled = state.page <= 1;
  els.nextPage.disabled = state.page >= state.pages;
}

function formatDue(task) {
  if (!task.due_date) return null;
  const date = new Date(task.due_date);
  if (Number.isNaN(date.getTime())) return null;

  const now = new Date();
  const options = {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  };
  if (date.getFullYear() !== now.getFullYear()) options.year = "numeric";

  return {
    text: `截止 ${date.toLocaleString("zh-CN", options)}`,
    overdue: date.getTime() < now.getTime() && task.status !== "done",
  };
}

function buildTaskCard(task) {
  const isDone = task.status === "done";
  const card = createEl(
    "article",
    `task-card priority-${task.priority}${isDone ? " is-done" : ""}`,
  );

  const check = createEl("button", `task-check${isDone ? " is-checked" : ""}`, isDone ? "✓" : "");
  check.type = "button";
  check.dataset.toggleId = String(task.id);
  check.setAttribute("aria-label", isDone ? "重新打开任务" : "标记任务为已完成");

  const body = createEl("div", "task-body");
  const titleRow = createEl("div", "task-title-row");
  titleRow.appendChild(createEl("h4", "task-title", task.title));
  titleRow.appendChild(
    createEl("span", `badge badge-${task.status}`, STATUS_LABELS[task.status] || task.status),
  );
  body.appendChild(titleRow);

  if (task.description) {
    body.appendChild(createEl("p", "task-desc", task.description));
  }

  const meta = createEl("div", "task-meta");
  meta.appendChild(
    createEl("span", "priority-chip", PRIORITY_LABELS[task.priority] || task.priority),
  );
  const due = formatDue(task);
  if (due) {
    meta.appendChild(createEl("span", `due-chip${due.overdue ? " is-overdue" : ""}`, due.text));
  }
  body.appendChild(meta);

  const actions = createEl("div", "task-actions");
  const editButton = createEl("button", "task-action", "编辑");
  editButton.type = "button";
  editButton.dataset.editId = String(task.id);
  const deleteButton = createEl("button", "task-action is-danger", "删除");
  deleteButton.type = "button";
  deleteButton.dataset.deleteId = String(task.id);
  actions.append(editButton, deleteButton);

  card.append(check, body, actions);
  return card;
}

function renderTasks() {
  els.taskList.replaceChildren();

  if (state.tasks.length === 0) {
    els.taskList.classList.add("is-hidden");
    els.emptyState.classList.remove("is-hidden");
    els.emptyText.textContent = state.keyword
      ? "没有找到匹配的任务，换个关键词试试。"
      : state.filter === "all"
        ? "创建第一个任务，把今天想做的事写下来。"
        : "这个视图里还没有任务，先添加一个吧。";
    return;
  }

  els.taskList.classList.remove("is-hidden");
  els.emptyState.classList.add("is-hidden");
  const fragment = document.createDocumentFragment();
  state.tasks.forEach((task) => fragment.appendChild(buildTaskCard(task)));
  els.taskList.appendChild(fragment);
}

function renderListError(message) {
  els.emptyState.classList.add("is-hidden");
  els.pagination.classList.add("is-hidden");
  els.taskList.classList.remove("is-hidden");

  const box = createEl("div", "loading-state");
  box.appendChild(createEl("p", "", `加载失败：${message}`));
  const retry = createEl("button", "btn btn-ghost", "重新加载");
  retry.type = "button";
  retry.addEventListener("click", () => {
    setLoading();
    refreshAll().catch((error) => renderListError(error.message));
  });
  box.appendChild(retry);
  els.taskList.replaceChildren(box);
}

/* ---------- 任务操作 ---------- */

async function toggleTask(taskId, button) {
  const task = state.tasks.find((item) => item.id === taskId);
  if (!task) return;

  const targetStatus = task.status === "done" ? "todo" : "done";
  button.disabled = true;
  try {
    await api(`/tasks/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify({ status: targetStatus }),
    });
    showToast(targetStatus === "done" ? "任务已完成 🎉" : "任务已重新打开");
    await refreshAll();
  } catch (error) {
    showToast(error.message, "error");
    button.disabled = false;
  }
}

async function deleteTask(taskId) {
  const task = state.tasks.find((item) => item.id === taskId);
  if (!task) return;
  if (!window.confirm(`确定删除「${task.title}」吗？`)) return;

  try {
    await api(`/tasks/${taskId}`, { method: "DELETE" });
    if (state.tasks.length === 1 && state.page > 1) state.page -= 1;
    showToast("任务已删除");
    await refreshAll();
  } catch (error) {
    showToast(error.message, "error");
  }
}

function toDateTimeLocal(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (number) => String(number).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function openTaskModal(task = null) {
  state.editingId = task ? task.id : null;
  els.taskForm.reset();
  setFormError(els.taskError, "");

  els.taskModalTitle.textContent = task ? "编辑任务" : "新建任务";
  els.taskSubmitBtn.textContent = task ? "保存修改" : "保存任务";
  els.taskId.value = task ? String(task.id) : "";
  els.taskStatus.value = task?.status || "todo";
  els.taskPriority.value = task?.priority || "medium";

  if (task) {
    els.taskTitle.value = task.title;
    els.taskDescription.value = task.description || "";
    els.taskDueDate.value = task.due_date ? toDateTimeLocal(task.due_date) : "";
  }

  els.taskModal.classList.remove("is-hidden");
  document.body.classList.add("modal-open");
  window.setTimeout(() => els.taskTitle.focus(), 30);
}

function closeTaskModal() {
  els.taskModal.classList.add("is-hidden");
  document.body.classList.remove("modal-open");
  state.editingId = null;
}

async function submitTask(event) {
  event.preventDefault();
  setFormError(els.taskError, "");

  const title = els.taskTitle.value.trim();
  if (!title) {
    setFormError(els.taskError, "请填写任务标题");
    els.taskTitle.focus();
    return;
  }

  const isEditing = state.editingId !== null;
  const taskId = state.editingId;
  const dueDateValue = els.taskDueDate.value;
  const payload = {
    title,
    description: els.taskDescription.value.trim() || null,
    status: els.taskStatus.value,
    priority: els.taskPriority.value,
    due_date: dueDateValue ? new Date(dueDateValue).toISOString() : null,
  };

  try {
    await withButton(els.taskSubmitBtn, async () => {
      if (isEditing) {
        await api(`/tasks/${taskId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        await api("/tasks", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      closeTaskModal();
      showToast(isEditing ? "任务已更新" : "任务已创建");
      await refreshAll();
    });
  } catch (error) {
    setFormError(els.taskError, error.message);
  }
}

/* ---------- 事件绑定 ---------- */

function bindEvents() {
  document.querySelectorAll("[data-auth-tab]").forEach((button) => {
    button.addEventListener("click", () => switchAuthTab(button.dataset.authTab));
  });

  els.loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setFormError(els.loginError, "");

    const form = new FormData(els.loginForm);
    const email = String(form.get("email") || "").trim();
    const password = String(form.get("password") || "");
    if (!email || !password) {
      setFormError(els.loginError, "请填写邮箱和密码");
      return;
    }

    const submitButton = els.loginForm.querySelector('button[type="submit"]');
    try {
      await withButton(submitButton, async () => {
        const data = await api("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
        await afterLoggedIn(data, "登录成功，开始今天的计划。");
      });
    } catch (error) {
      setFormError(els.loginError, error.message);
    }
  });

  els.registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setFormError(els.registerError, "");

    const form = new FormData(els.registerForm);
    const email = String(form.get("email") || "").trim();
    const username = String(form.get("username") || "").trim();
    const password = String(form.get("password") || "");
    const confirm = String(form.get("confirm") || "");

    if (!email || !username || !password) {
      setFormError(els.registerError, "请完整填写注册信息");
      return;
    }
    if (username.length < 2) {
      setFormError(els.registerError, "用户名至少需要 2 个字符");
      return;
    }
    if (password.length < 8) {
      setFormError(els.registerError, "密码至少需要 8 位");
      return;
    }
    if (password !== confirm) {
      setFormError(els.registerError, "两次输入的密码不一致");
      return;
    }

    const submitButton = els.registerForm.querySelector('button[type="submit"]');
    try {
      await withButton(submitButton, async () => {
        await api("/auth/register", {
          method: "POST",
          body: JSON.stringify({ email, username, password }),
        });
        const data = await api("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
        await afterLoggedIn(data, "账号创建成功，欢迎使用 TaskFlow。");
      });
    } catch (error) {
      setFormError(els.registerError, error.message);
    }
  });

  els.logoutBtn.addEventListener("click", () => logout(true));

  document.querySelectorAll("[data-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      state.filter = button.dataset.filter;
      state.page = 1;
      syncFilterUI();
      setLoading();
      loadTasks().catch((error) => {
        renderListError(error.message);
        showToast(error.message, "error");
      });
    });
  });

  els.searchInput.addEventListener("input", () => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => {
      state.keyword = els.searchInput.value.trim();
      state.page = 1;
      setLoading();
      loadTasks().catch((error) => {
        renderListError(error.message);
        showToast(error.message, "error");
      });
    }, 300);
  });

  els.newTaskBtn.addEventListener("click", () => openTaskModal());
  els.emptyCreateBtn.addEventListener("click", () => openTaskModal());
  els.taskForm.addEventListener("submit", submitTask);

  els.taskList.addEventListener("click", (event) => {
    const target = event.target.closest("button");
    if (!target) return;

    if (target.dataset.toggleId) {
      toggleTask(Number(target.dataset.toggleId), target);
    } else if (target.dataset.editId) {
      const task = state.tasks.find((item) => item.id === Number(target.dataset.editId));
      if (task) openTaskModal(task);
    } else if (target.dataset.deleteId) {
      deleteTask(Number(target.dataset.deleteId));
    }
  });

  els.prevPage.addEventListener("click", () => {
    if (state.page <= 1) return;
    state.page -= 1;
    setLoading();
    loadTasks().catch((error) => renderListError(error.message));
  });

  els.nextPage.addEventListener("click", () => {
    if (state.page >= state.pages) return;
    state.page += 1;
    setLoading();
    loadTasks().catch((error) => renderListError(error.message));
  });

  document.querySelectorAll("[data-close-modal]").forEach((element) => {
    element.addEventListener("click", closeTaskModal);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !els.taskModal.classList.contains("is-hidden")) {
      closeTaskModal();
    }
  });
}

/* ---------- 启动 ---------- */

async function restoreSession() {
  try {
    state.user = await api("/users/me");
    showApp();
    setLoading();
    await refreshAll();
  } catch (error) {
    logout(false);
    if (!String(error.message).includes("登录")) {
      showToast(error.message, "error");
    }
  }
}

async function init() {
  bindEvents();
  setDateLabel();
  syncFilterUI();

  if (state.token) {
    await restoreSession();
  } else {
    showAuth();
  }
}

init();