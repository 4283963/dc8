const API_BASE = '';

const els = {
  statusIndicator: document.getElementById('status-indicator'),
  statusText: document.querySelector('#status-indicator .status-text'),
  projectPath: document.getElementById('project-path'),
  browseBtn: document.getElementById('browse-btn'),
  scanJava: document.getElementById('scan-java'),
  scanCpp: document.getElementById('scan-cpp'),
  scanBtn: document.getElementById('scan-btn'),
  scanResult: document.getElementById('scan-result'),
  scanMessage: document.getElementById('scan-message'),
  statFiles: document.getElementById('stat-files'),
  statChunks: document.getElementById('stat-chunks'),
  auditQuery: document.getElementById('audit-query'),
  auditBtn: document.getElementById('audit-btn'),
  resultsSection: document.getElementById('results-section'),
  auditSummary: document.getElementById('audit-summary'),
  vulnerabilitiesList: document.getElementById('vulnerabilities-list'),
  vulnCount: document.getElementById('vuln-count'),
  loadingOverlay: document.getElementById('loading-overlay'),
  loadingText: document.getElementById('loading-text'),
  quickBtns: document.querySelectorAll('.quick-btn'),
};

let projectScanned = false;
let currentProjectPath = '';

async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (res.ok) {
      setStatus(true);
    } else {
      setStatus(false);
    }
  } catch (e) {
    setStatus(false);
  }
}

function setStatus(connected) {
  const indicator = els.statusIndicator;
  const text = els.statusText;
  if (connected) {
    indicator.className = 'status status-connected';
    text.textContent = '已连接';
  } else {
    indicator.className = 'status status-disconnected';
    text.textContent = '未连接';
  }
}

function showLoading(text = '处理中...') {
  els.loadingText.textContent = text;
  els.loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
  els.loadingOverlay.classList.add('hidden');
}

els.browseBtn.addEventListener('click', async () => {
  try {
    const dirHandle = await window.showDirectoryPicker();
    els.projectPath.value = dirHandle.name;
    els.projectPath.dataset.fullPath = dirHandle.name;
  } catch (e) {
    alert('请手动输入项目目录的绝对路径。\n\n提示：由于浏览器安全限制，需要您手动输入路径。\n例如：/Users/username/projects/my-java-app');
    els.projectPath.focus();
  }
});

els.scanBtn.addEventListener('click', async () => {
  const projectPath = els.projectPath.value.trim();
  if (!projectPath) {
    alert('请输入项目目录路径');
    return;
  }

  const fileTypes = [];
  if (els.scanJava.checked) fileTypes.push('java');
  if (els.scanCpp.checked) fileTypes.push('cpp');

  if (fileTypes.length === 0) {
    alert('请至少选择一种文件类型');
    return;
  }

  showLoading('正在扫描代码...');

  try {
    const res = await fetch(`${API_BASE}/api/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_path: projectPath,
        file_types: fileTypes,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || '扫描失败');
    }

    projectScanned = true;
    showScanResult(data);
    currentProjectPath = projectPath;
  } catch (e) {
    alert(`扫描失败: ${e.message}`);
  } finally {
    hideLoading();
  }
});

function showScanResult(data) {
  els.scanResult.classList.remove('hidden');
  els.scanMessage.textContent = data.message;
  els.statFiles.textContent = data.total_files;
  els.statChunks.textContent = data.total_chunks;
}

els.quickBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    const query = btn.dataset.query;
    els.auditQuery.value = `帮我审计这个项目有哪些${query}`;
  });
});

els.auditBtn.addEventListener('click', async () => {
  const query = els.auditQuery.value.trim();
  if (!query) {
    alert('请输入审计查询');
    return;
  }

  showLoading('AI 正在分析代码...');

  try {
    const res = await fetch(`${API_BASE}/api/audit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: query,
        top_k: 5,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || '审计失败');
    }

    renderAuditResults(data);
  } catch (e) {
    alert(`审计失败: ${e.message}`);
  } finally {
    hideLoading();
  }
});

function renderAuditResults(data) {
  els.resultsSection.classList.remove('hidden');
  els.vulnCount.textContent = data.total_found;
  els.auditSummary.textContent = data.summary;

  els.vulnerabilitiesList.innerHTML = '';

  if (data.vulnerabilities.length === 0) {
    els.vulnerabilitiesList.innerHTML = `
      <div class="no-vulns">
        <p>✅ 未发现明显的安全漏洞</p>
      </div>
    `;
    return;
  }

  const sorted = [...data.vulnerabilities].sort((a, b) => {
    const order = { critical: 0, high: 1, medium: 2, low: 3 };
    return order[a.severity] - order[b.severity];
  });

  sorted.forEach((vuln, index) => {
    const card = createVulnerabilityCard(vuln, index === 0);
    els.vulnerabilitiesList.appendChild(card);
  });
}

function createVulnerabilityCard(vuln, expanded = false) {
  const card = document.createElement('div');
  card.className = `vulnerability-card ${expanded ? 'expanded' : ''}`;
  card.dataset.vulnId = vuln.id;

  const severityClass = `severity-${vuln.severity}`;
  const severityLabel = {
    low: '低危',
    medium: '中危',
    high: '高危',
    critical: '严重',
  }[vuln.severity] || vuln.severity;

  const lineInfo = vuln.line_number ? ` (第 ${vuln.line_number} 行)` : '';

  card.innerHTML = `
    <div class="vuln-header">
      <div class="vuln-title">
        <span class="vuln-type">${escapeHtml(vuln.type)}</span>
        <span class="vuln-file">${escapeHtml(vuln.file_path)}${lineInfo}</span>
      </div>
      <span class="severity-badge ${severityClass}">${severityLabel}</span>
    </div>
    <div class="vuln-body">
      <div class="vuln-section">
        <h4>漏洞描述</h4>
        <p>${escapeHtml(vuln.description)}</p>
      </div>
      ${vuln.code_snippet ? `
      <div class="vuln-section">
        <h4>相关代码</h4>
        <pre class="code-snippet">${escapeHtml(vuln.code_snippet)}</pre>
      </div>
      ` : ''}
      <div class="vuln-section">
        <h4>修复建议</h4>
        <div class="suggestion-box">${escapeHtml(vuln.suggestion)}</div>
      </div>
      <div class="vuln-actions">
        <button class="btn btn-repair" type="button" data-vuln-id="${vuln.id}">
          <span class="btn-icon">🔧</span>
          智能修复
        </button>
        <div class="repair-status hidden" data-vuln-id="${vuln.id}">
          <span class="repair-status-text"></span>
        </div>
      </div>
    </div>
  `;

  card.querySelector('.vuln-header').addEventListener('click', () => {
    card.classList.toggle('expanded');
  });

  const repairBtn = card.querySelector('.btn-repair');
  repairBtn.addEventListener('click', async (e) => {
    e.stopPropagation();
    await handleRepair(vuln, card);
  });

  return card;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

async function handleRepair(vuln, card) {
  const repairBtn = card.querySelector('.btn-repair');
  const repairStatus = card.querySelector('.repair-status');
  const statusText = card.querySelector('.repair-status-text');

  if (!currentProjectPath) {
    alert('请先扫描项目目录');
    return;
  }

  repairBtn.disabled = true;
  repairBtn.innerHTML = '<span class="btn-icon">⏳</span>修复中...';
  repairStatus.classList.remove('hidden');
  repairStatus.className = 'repair-status repair-status-working';
  statusText.textContent = 'AI Agent 正在分析并修复漏洞...';

  try {
    const res = await fetch(`${API_BASE}/api/repair`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vulnerability_id: vuln.id,
        project_path: currentProjectPath,
        file_path: vuln.file_path,
        line_number: vuln.line_number,
        vulnerability_type: vuln.type,
        description: vuln.description,
        code_snippet: vuln.code_snippet,
        suggestion: vuln.suggestion,
      }),
    });

    const data = await res.json();

    if (data.status === 'success' && data.result && data.result.success) {
      repairStatus.className = 'repair-status repair-status-success';
      const msg = data.result.changes_applied || data.result.message || '修复成功';
      statusText.innerHTML = `✅ ${msg}`;
      repairBtn.innerHTML = '<span class="btn-icon">✔</span>已修复';
      repairBtn.disabled = true;
      repairBtn.classList.add('btn-repaired');

      if (data.result.backup_path) {
        statusText.innerHTML += `<br><small>备份文件：${escapeHtml(data.result.backup_path)}</small>`;
      }
    } else {
      repairStatus.className = 'repair-status repair-status-error';
      statusText.innerHTML = `❌ 修复失败：${escapeHtml(data.error || (data.result && data.result.message) || '未知错误')}`;
      repairBtn.innerHTML = '<span class="btn-icon">🔧</span>智能修复';
      repairBtn.disabled = false;
    }
  } catch (e) {
    repairStatus.className = 'repair-status repair-status-error';
    statusText.innerHTML = `❌ 修复失败：${escapeHtml(e.message)}`;
    repairBtn.innerHTML = '<span class="btn-icon">🔧</span>智能修复';
    repairBtn.disabled = false;
  }
}

checkHealth();
setInterval(checkHealth, 10000);
