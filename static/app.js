const api = {
  async getProjects() { return (await fetch('/api/projects')).json(); },
  async createProject(project_name) {
    return (await fetch('/api/projects', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({project_name})
    })).json();
  },
  async run(payload) {
    return (await fetch('/api/run', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    })).json();
  },
  async saveConfig(payload) {
    return (await fetch('/api/save-config', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    })).json();
  }
};

let currentProject = '';

function getPayload() {
  const itemsRaw = document.getElementById('items').value.trim();
  const items = itemsRaw ? itemsRaw.split('\n').map(s => s.trim()).filter(Boolean) : [];
  return {
    project_name: currentProject,
    prompt_template: document.getElementById('promptTemplate').value,
    items,
    model_name: document.getElementById('modelName').value,
    extract_company_ticker: document.getElementById('extractToggle').checked,
  };
}

async function refreshProjects() {
  const data = await api.getProjects();
  const select = document.getElementById('projectSelect');
  select.innerHTML = '';
  for (const p of data.projects || []) {
    const opt = document.createElement('option');
    opt.value = p.name;
    opt.textContent = p.name;
    select.appendChild(opt);
  }
  if (!currentProject && (data.projects || []).length > 0) {
    currentProject = data.projects[0].name;
  }
  if (currentProject) {
    select.value = currentProject;
    document.getElementById('currentProject').textContent = currentProject;
  }
}

async function createProject() {
  const name = document.getElementById('projectName').value.trim() || document.getElementById('projectSelect').value;
  if (!name) return alert('请输入项目名称');
  await api.createProject(name);
  currentProject = name;
  document.getElementById('currentProject').textContent = currentProject;
  await refreshProjects();
}

document.getElementById('projectSelect').addEventListener('change', (e) => {
  currentProject = e.target.value;
  document.getElementById('currentProject').textContent = currentProject;
});

async function runPrompts() {
  if (!currentProject) return alert('请先创建/选择项目');
  const payload = getPayload();
  const result = await api.run(payload);
  document.getElementById('resultText').textContent = JSON.stringify(result.results || result, null, 2);
}

async function saveConfig() {
  if (!currentProject) return alert('请先创建/选择项目');
  const config_name = document.getElementById('configName').value.trim();
  if (!config_name) return alert('请输入配置名称');
  const payload = getPayload();
  const res = await api.saveConfig({ ...payload, config_name });
  alert(`保存成功，当前配置数：${res.saved_count}`);
}

refreshProjects();

window.createProject = createProject;
window.runPrompts = runPrompts;
window.saveConfig = saveConfig;
