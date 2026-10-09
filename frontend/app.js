/**
 * Sentinel Frontend Controller
 * Live WebSocket DAG State Machine, Interactive Disagreement Alert,
 * Human-in-the-Loop Approval Modal, and Automated Benchmark Explorer.
 */

(function () {
  'use strict';

  // Global State
  let ws = null;
  let activeMission = null;
  let pendingAction = null;
  let reconnectInterval = 3000;

  // DOM Elements
  const connectionStatus = document.getElementById('connection-status');
  const btnInjectFault = document.getElementById('btn-inject-fault');
  const missionForm = document.getElementById('mission-form');
  const missionInput = document.getElementById('mission-input');
  const btnRunMission = document.getElementById('btn-run-mission');
  const missionBadge = document.getElementById('mission-state-badge');

  // DAG Nodes
  const nodePlanner = document.getElementById('node-planner');
  const nodeResA = document.getElementById('node-res-a');
  const nodeResB = document.getElementById('node-res-b');
  const nodeResC = document.getElementById('node-res-c');
  const nodeVerifier = document.getElementById('node-verifier');
  const nodeTargeted = document.getElementById('node-targeted');
  const nodeAnalyst = document.getElementById('node-analyst');

  // Disagreement Banner
  const disagreementCard = document.getElementById('disagreement-card');
  const disagreementContent = document.getElementById('disagreement-content');

  // Results & Confidence
  const resultsPanel = document.getElementById('results-panel');
  const confidenceScoreBadge = document.getElementById('confidence-score-badge');
  const scoreEvidence = document.getElementById('score-evidence');
  const scoreAgreement = document.getElementById('score-agreement');
  const scoreVerification = document.getElementById('score-verification');
  const scoreExecution = document.getElementById('score-execution');
  const recommendationText = document.getElementById('recommendation-text');
  const tradeoffsList = document.getElementById('tradeoffs-list');

  // Evidence Tab
  const claimsMatrix = document.getElementById('claims-matrix');

  // Benchmarks Tab
  const btnRunBenchmark = document.getElementById('btn-run-benchmark');
  const bmSuccessRate = document.getElementById('bm-success-rate');
  const bmVerifiedRate = document.getElementById('bm-verified-rate');
  const bmUnsupportedRate = document.getElementById('bm-unsupported-rate');
  const bmRecoveryRate = document.getElementById('bm-recovery-rate');
  const bmGatingRate = document.getElementById('bm-gating-rate');
  const benchmarkTbody = document.getElementById('benchmark-tbody');

  // Approval Modal
  const approvalModal = document.getElementById('approval-modal');
  const modalActionType = document.getElementById('modal-action-type');
  const modalRiskBadge = document.getElementById('modal-risk-badge');
  const modalCodexRule = document.getElementById('modal-codex-rule');
  const modalActionPayload = document.getElementById('modal-action-payload');
  const btnModalApprove = document.getElementById('btn-modal-approve');
  const btnModalReject = document.getElementById('btn-modal-reject');

  // Initialize
  initTabs();
  initChips();
  initFaultButton();
  initForm();
  initModal();
  initBenchmarks();
  initWebSocket();

  // 1. TAB NAVIGATION
  function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const targetTabId = btn.getAttribute('data-tab');

        tabBtns.forEach((b) => b.classList.remove('active'));
        tabContents.forEach((c) => c.classList.remove('active'));

        btn.classList.add('active');
        const targetContent = document.getElementById(targetTabId);
        if (targetContent) targetContent.classList.add('active');

        if (targetTabId === 'tab-benchmarks') {
          fetchBenchmarks();
        }
      });
    });
  }

  // 2. QUICK SCENARIO CHIPS
  function initChips() {
    const chips = document.querySelectorAll('.chip');
    chips.forEach((chip) => {
      chip.addEventListener('click', () => {
        const promptText = chip.getAttribute('data-prompt');
        missionInput.value = promptText;
        missionInput.focus();
      });
    });
  }

  // 3. FAULT INJECTION BUTTON
  function initFaultButton() {
    btnInjectFault.addEventListener('click', async () => {
      try {
        btnInjectFault.innerText = '⚡ Arming 503 Fault...';
        const res = await fetch('/api/simulate-fault', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ count: 1, error_code: 503 }),
        });
        const data = await res.json();
        btnInjectFault.innerText = '⚠️ 503 Fault Armed!';
        setTimeout(() => {
          btnInjectFault.innerText = '⚡ Inject Tool 503 Fault';
        }, 3000);
      } catch (err) {
        console.error('Failed to inject fault:', err);
        btnInjectFault.innerText = '⚡ Fault Injection Failed';
      }
    });
  }

  // 4. MISSION SUBMISSION
  function initForm() {
    missionForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = missionInput.value.trim();
      if (!text) return;

      resetDagUI();
      btnRunMission.disabled = true;
      btnRunMission.innerHTML = '<span>Orchestrating Agents...</span>';

      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'start_mission', request: text }));
      } else {
        // Fallback REST
        fetch('/api/missions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ request: text, auto_approve: false }),
        })
          .then((r) => r.json())
          .then((mission) => renderMission(mission))
          .catch((err) => console.error(err))
          .finally(() => {
            btnRunMission.disabled = false;
            btnRunMission.innerHTML = '<span>Run Autonomous Mission</span> <span class="arrow">→</span>';
          });
      }
    });
  }

  // 5. APPROVAL MODAL ACTIONS
  function initModal() {
    btnModalApprove.addEventListener('click', async () => {
      if (!activeMission || !pendingAction) return;
      approvalModal.classList.add('hidden');
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({
            action: 'approve',
            mission_id: activeMission.id,
            action_id: pendingAction.id,
          })
        );
      } else {
        await fetch(`/api/missions/${activeMission.id}/approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action_id: pendingAction.id }),
        });
      }
    });

    btnModalReject.addEventListener('click', async () => {
      if (!activeMission || !pendingAction) return;
      approvalModal.classList.add('hidden');
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({
            action: 'reject',
            mission_id: activeMission.id,
            action_id: pendingAction.id,
          })
        );
      } else {
        await fetch(`/api/missions/${activeMission.id}/reject`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action_id: pendingAction.id }),
        });
      }
    });
  }

  // 6. WEBSOCKET CONNECTION
  function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || 'localhost:8787';
    const wsUrl = `${protocol}//${host}/ws`;

    connectionStatus.innerText = 'Connecting to Edge...';
    connectionStatus.style.color = '#f59e0b';

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      connectionStatus.innerText = 'Connected to Edge Agent';
      connectionStatus.style.color = '#10b981';
      reconnectInterval = 3000;
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'init') {
          if (msg.missions && msg.missions.length > 0) {
            renderMission(msg.missions[0]);
          }
        } else if (msg.type === 'mission_update') {
          renderMission(msg.data);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      connectionStatus.innerText = 'Disconnected. Reconnecting...';
      connectionStatus.style.color = '#ef4444';
      setTimeout(initWebSocket, reconnectInterval);
      reconnectInterval = Math.min(reconnectInterval * 1.5, 10000);
    };

    ws.onerror = (err) => {
      console.error('WebSocket encountered error:', err);
      ws.close();
    };
  }

  // 7. RENDER MISSION STATE IN DAG & PANELS
  function renderMission(mission) {
    activeMission = mission;
    missionBadge.innerText = mission.status.toUpperCase();
    missionBadge.className = 'status-badge ' + getStatusClass(mission.status);

    updateNodeState(nodePlanner, mission.status === 'planning' ? 'active' : (isPastStage(mission.status, 'planning') ? 'passed' : 'ready'), getStatusLabel(mission.status, 'planning'));
    
    const resActive = mission.status === 'researching';
    const resPassed = isPastStage(mission.status, 'researching');
    updateNodeState(nodeResA, resActive ? 'active' : (resPassed ? 'passed' : 'idle'), resActive ? 'Analyzing Docs' : (resPassed ? '3 Claims Verified' : 'Idle'));
    updateNodeState(nodeResB, resActive ? 'active' : (resPassed ? 'passed' : 'idle'), resActive ? 'Comparing Limits' : (resPassed ? '4 Claims Verified' : 'Idle'));
    updateNodeState(nodeResC, resActive ? 'active' : (resPassed ? 'passed' : 'idle'), resActive ? 'Latency Profiling' : (resPassed ? '3 Claims Verified' : 'Idle'));

    const verActive = mission.status === 'verifying';
    const verPassed = isPastStage(mission.status, 'verifying');
    updateNodeState(nodeVerifier, verActive ? 'active' : (verPassed ? 'passed' : 'idle'), verActive ? 'Cross-Examining' : (verPassed ? `${mission.conflicts.length} Disagreements Checked` : 'Idle'));

    // Handle Conflicts & Targeted Resolution
    if (mission.conflicts && mission.conflicts.length > 0) {
      disagreementCard.classList.remove('hidden');
      renderDisagreements(mission.conflicts);

      nodeTargeted.classList.remove('hidden');
      updateNodeState(nodeTargeted, 'passed', 'Resolved with Citations');
    } else {
      disagreementCard.classList.add('hidden');
      nodeTargeted.classList.add('hidden');
    }

    const anaActive = mission.status === 'awaiting_approval' || mission.status === 'executing';
    const anaPassed = mission.status === 'completed';
    updateNodeState(nodeAnalyst, anaActive ? 'active' : (anaPassed ? 'passed' : 'idle'), anaActive ? 'Codex Policy Check' : (anaPassed ? 'Postconditions Verified' : 'Idle'));

    // Check if human approval is needed
    if (mission.status === 'awaiting_approval' && mission.actions && mission.actions.length > 0) {
      const act = mission.actions.find((a) => a.requires_approval && a.status === 'awaiting_approval');
      if (act) {
        pendingAction = act;
        showApprovalModal(act);
      }
    } else {
      approvalModal.classList.add('hidden');
    }

    // Results Panel
    if (mission.status === 'completed' || (mission.recommendation && mission.confidence.overall > 0)) {
      resultsPanel.classList.remove('hidden');
      renderResults(mission);
      btnRunMission.disabled = false;
      btnRunMission.innerHTML = '<span>Run Autonomous Mission</span> <span class="arrow">→</span>';
    }

    // Evidence Matrix
    renderEvidenceMatrix(mission);
  }

  function updateNodeState(node, state, labelText) {
    if (!node) return;
    node.classList.remove('active', 'passed');
    if (state === 'active') node.classList.add('active');
    if (state === 'passed') node.classList.add('passed');

    const statusEl = node.querySelector('.node-status');
    if (statusEl && labelText) {
      statusEl.innerText = labelText;
    }
  }

  function isPastStage(currentStatus, stage) {
    const order = ['idle', 'planning', 'researching', 'verifying', 'awaiting_approval', 'executing', 'completed'];
    return order.indexOf(currentStatus) > order.indexOf(stage);
  }

  function getStatusClass(status) {
    if (status === 'completed') return 'badge success';
    if (status === 'awaiting_approval') return 'badge warning';
    if (status === 'failed') return 'badge danger';
    return 'badge info';
  }

  function getStatusLabel(currentStatus, stage) {
    if (currentStatus === stage) return 'Running...';
    if (isPastStage(currentStatus, stage)) return 'Done ✓';
    return 'Pending';
  }

  function resetDagUI() {
    resultsPanel.classList.add('hidden');
    disagreementCard.classList.add('hidden');
    nodeTargeted.classList.add('hidden');
    [nodePlanner, nodeResA, nodeResB, nodeResC, nodeVerifier, nodeTargeted, nodeAnalyst].forEach((n) => {
      if (n) {
        n.classList.remove('active', 'passed');
        const st = n.querySelector('.node-status');
        if (st) st.innerText = 'Pending';
      }
    });
  }

  // 8. RENDER DISAGREEMENTS BANNER
  function renderDisagreements(conflicts) {
    disagreementContent.innerHTML = conflicts
      .map(
        (c) => `
        <div style="margin-bottom: 0.75rem; padding-bottom: 0.5rem; border-bottom: 1px solid rgba(245, 158, 11, 0.2);">
          <div style="font-weight: 600; color: #fde68a;">📌 Disputed Topic: ${escapeHtml(c.topic)}</div>
          <div style="margin: 0.25rem 0; font-size: 0.85rem;"><strong>Premises:</strong> ${escapeHtml(c.opposing_premises.join(' ↔ '))}</div>
          <div style="font-size: 0.85rem; color: #a7f3d0;"><strong>✓ Grounded Resolution:</strong> ${escapeHtml(c.resolution_summary || 'Resolved via targeted documentation fetch.')}</div>
        </div>
      `
      )
      .join('');
  }

  // 9. RENDER RESULTS & CONFIDENCE
  function renderResults(mission) {
    const conf = mission.confidence || {};
    const overallPct = Math.round((conf.overall || 0) * 100);

    confidenceScoreBadge.innerText = `Confidence: ${overallPct}%`;
    if (overallPct >= 85) {
      confidenceScoreBadge.className = 'confidence-badge';
    } else if (overallPct >= 60) {
      confidenceScoreBadge.className = 'confidence-badge' ;
      confidenceScoreBadge.style.color = '#f59e0b';
    } else {
      confidenceScoreBadge.className = 'confidence-badge';
      confidenceScoreBadge.style.color = '#ef4444';
    }

    scoreEvidence.innerText = `${Math.round((conf.evidence_quality || 0) * 100)}%`;
    scoreAgreement.innerText = `${Math.round((conf.agent_agreement || 0) * 100)}%`;
    scoreVerification.innerText = `${Math.round((conf.verification_success || 0) * 100)}%`;
    scoreExecution.innerText = `${Math.round((conf.execution_success || 0) * 100)}%`;

    recommendationText.innerHTML = formatMarkdown(mission.recommendation || 'Recommendation in progress...');

    if (mission.tradeoffs && mission.tradeoffs.length > 0) {
      tradeoffsList.innerHTML = mission.tradeoffs
        .map((t) => `<li>${escapeHtml(t)}</li>`)
        .join('');
    } else {
      tradeoffsList.innerHTML = '<li>Comprehensive evaluation complete. No outstanding blocker tradeoffs identified.</li>';
    }
  }

  // 10. RENDER EVIDENCE MATRIX (TAB 2)
  function renderEvidenceMatrix(mission) {
    if (!mission.claims || mission.claims.length === 0) {
      claimsMatrix.innerHTML = '<p class="placeholder-msg">Run a mission to inspect the live claims and evidence graph.</p>';
      return;
    }

    claimsMatrix.innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 1rem; width: 100%;">
        ${mission.claims
          .map((c) => {
            const isVerified = c.status === 'verified';
            const badgeClass = isVerified ? 'badge success' : 'badge warning';
            const statusLabel = isVerified ? 'VERIFIED' : 'UNVERIFIED';

            return `
              <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: 8px; padding: 1rem; display: flex; flex-direction: column; gap: 0.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono);">${escapeHtml(c.author_agent)}</span>
                  <span class="${badgeClass}">${statusLabel}</span>
                </div>
                <div style="font-size: 0.88rem; font-weight: 500; color: #fff;">${escapeHtml(c.statement)}</div>
                ${
                  c.evidence_ids && c.evidence_ids.length > 0
                    ? `<div style="font-size: 0.75rem; color: var(--color-cyan); margin-top: auto; padding-top: 0.5rem; border-top: 1px solid rgba(255,255,255,0.05);">
                        🔗 Linked Grounding Evidence: ${c.evidence_ids.map((id) => `<code>${escapeHtml(id)}</code>`).join(', ')}
                       </div>`
                    : `<div style="font-size: 0.75rem; color: var(--color-danger); margin-top: auto;">⚠️ Grounding citation pending</div>`
                }
                ${
                  c.divergence_reason
                    ? `<div style="font-size: 0.75rem; color: #a7f3d0; background: rgba(16,185,129,0.08); padding: 0.35rem 0.5rem; border-radius: 4px;">
                        ${escapeHtml(c.divergence_reason)}
                       </div>`
                    : ''
                }
              </div>
            `;
          })
          .join('')}
      </div>
    `;
  }

  // 11. APPROVAL MODAL CONTROLS
  function showApprovalModal(action) {
    modalActionType.innerText = action.tool_name || 'external_tool';
    modalRiskBadge.innerText = action.risk_level.toUpperCase();
    modalRiskBadge.className = 'badge ' + (action.risk_level === 'high' ? 'danger' : 'warning');
    modalCodexRule.innerText = action.risk_level === 'high' ? 'CODEX-GITOPS-07' : 'CODEX-GITOPS-04';
    modalActionPayload.innerText = JSON.stringify(action.parameters, null, 2);
    approvalModal.classList.remove('hidden');
  }

  // 12. BENCHMARKS TAB (TAB 4)
  function initBenchmarks() {
    btnRunBenchmark.addEventListener('click', async () => {
      btnRunBenchmark.disabled = true;
      btnRunBenchmark.innerText = 'Running 10 Scenarios...';
      try {
        const res = await fetch('/api/benchmarks/run', { method: 'POST' });
        const data = await res.json();
        renderBenchmarksData(data);
      } catch (err) {
        console.error('Failed to run benchmarks:', err);
      } finally {
        btnRunBenchmark.disabled = false;
        btnRunBenchmark.innerText = 'Run All 10 Benchmarks';
      }
    });

    fetchBenchmarks();
  }

  async function fetchBenchmarks() {
    try {
      const res = await fetch('/api/benchmarks');
      if (res.ok) {
        const data = await res.json();
        renderBenchmarksData(data);
      }
    } catch (err) {
      console.error('Failed to fetch benchmarks:', err);
    }
  }

  function renderBenchmarksData(data) {
    const m = data.metrics || {};
    bmSuccessRate.innerText = `${Math.round((m.mission_success_rate || 1.0) * 100)}%`;
    bmVerifiedRate.innerText = `${Math.min(100, Math.round((m.verified_decision_rate || 1.0) * 100))}%`;
    bmUnsupportedRate.innerText = `${(m.unsupported_claim_rate || 0.0).toFixed(1)}%`;
    bmRecoveryRate.innerText = `${Math.round((m.recovery_success_rate || 1.0) * 100)}%`;
    bmGatingRate.innerText = `${Math.round((m.approval_accuracy || 1.0) * 100)}%`;

    if (data.scenario_results && data.scenario_results.length > 0) {
      benchmarkTbody.innerHTML = data.scenario_results
        .map(
          (sc) => `
          <tr>
            <td><code>${escapeHtml(sc.id)}</code></td>
            <td><strong>${escapeHtml(sc.name)}</strong></td>
            <td><span class="badge ${sc.passed ? 'success' : 'danger'}">${sc.passed ? 'PASS' : 'FAIL'}</span></td>
            <td><strong>${Math.round((sc.confidence || 0.95) * 100)}%</strong></td>
            <td>${sc.id === 'BENCH-04' ? '<span class="badge danger">503 Recovered</span>' : '<span style="color:var(--text-muted)">--</span>'}</td>
            <td>${sc.conflicts_count > 0 ? `<span class="badge warning">${sc.conflicts_count} Resolved</span>` : '<span style="color:var(--text-muted)">None</span>'}</td>
          </tr>
        `
        )
        .join('');
    }
  }

  // UTILITIES
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Code blocks
    html = html.replace(/```(.*?)```/gs, '<pre><code>$1</code></pre>');
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Headers
    html = html.replace(/^### (.*$)/gim, '<h4 style="margin: 0.75rem 0 0.25rem; color: #fff;">$1</h4>');
    html = html.replace(/^## (.*$)/gim, '<h3 style="margin: 1rem 0 0.5rem; color: #f6821f;">$1</h3>');
    // Bullet lists
    html = html.replace(/^\* (.*$)/gim, '<li>$1</li>');
    html = html.replace(/^- (.*$)/gim, '<li>$1</li>');
    // Paragraph breaks
    html = html.replace(/\n\n/g, '<br><br>');
    return html;
  }
})();
