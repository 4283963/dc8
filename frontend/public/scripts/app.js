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
    </div>
  `;

  card.querySelector('.vuln-header').addEventListener('click', () => {
    card.classList.toggle('expanded');
  });

  return card;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

checkHealth();
setInterval(checkHealth, 10000);
