document.addEventListener('DOMContentLoaded', () => {

    const elements = {
        issues: document.getElementById('stat-issues'),
        mrs: document.getElementById('stat-mrs'),
        pipelines: document.getElementById('stat-pipelines'),
        feed: document.getElementById('feed-list'),
        analysis: document.getElementById('analysis-content'),
        config: document.getElementById('config-list'),
        pipelineBoard: document.getElementById('pipeline-list'),
        toolsGrid: document.getElementById('tools-grid'),
        demoBtn: document.getElementById('demo-mode-toggle')
    };

    let previousStateStr = "";
    let demoMode = false;

    // ---- MOCK DATA (used when API is unreachable or Demo Mode is on) ----
    const MOCK_STATE = {
        activity_feed: [
            { type: "Issue", id: 503, title: "Security: Hardcoded API token in test files", state: "opened", analysis_status: "done", action_taken: true },
            { type: "Merge Request", id: 902, title: "Chore: Update httpx from 0.24.1 to 0.27.0", state: "opened", analysis_status: "done", action_taken: true },
            { type: "Issue", id: 502, title: "Feature: Add WebSocket support for Activity Feed", state: "opened", analysis_status: "done", action_taken: true },
            { type: "Merge Request", id: 901, title: "Fix: Handle unsupported webhook event types gracefully", state: "opened", analysis_status: "done", action_taken: true },
            { type: "Issue", id: 501, title: "Bug: Webhook endpoint fails on push events", state: "opened", analysis_status: "done", action_taken: true }
        ],
        pipelines: [
            { ref: "fix-webhook-push", status: "success", url: "#" },
            { ref: "update-httpx", status: "failed", url: "#" },
            { ref: "main", status: "running", url: "#" }
        ],
        entities: { issues: 3, mrs: 2, pipelines: 3 },
        latest_analysis: {
            target: "Security: Hardcoded API token in test files",
            result: "SEVERITY: Critical\\nCATEGORY: Security Vulnerability\\n\\nANALYSIS:\\nThis issue reports a hardcoded GitLab Personal Access Token (GL_PAT) found in tests/conftest.py. This is a severe security risk — if pushed to a public repository, an attacker could gain unauthorized access to the GitLab project.\\n\\nRECOMMENDED ACTIONS:\\n1. Immediately rotate the exposed token via GitLab Settings > Access Tokens\\n2. Replace the hardcoded token with os.environ.get('GITLAB_TOKEN')\\n3. Add tests/conftest.py patterns to .gitignore\\n4. Consider using GitLab CI/CD variables for test pipelines\\n5. Run git filter-branch to remove token from history\\n\\nACTION TAKEN: Posted triage comment to Issue #503 with remediation steps.",
            action_executed: true
        },
        config: {
            project: "ghost-engine-gitlab",
            webhook_endpoint: "/api/v1/webhook",
            mock_mode: true,
            components: ["GitLabEvent", "Issue", "MergeRequest", "PipelineStatus", "AgentAnalysis"],
            duo_platform: true
        },
        duo_tools: [
            { name: "triage_issue", description: "Analyzes GitLab issues to determine severity, category, and recommended actions", icon: "🏷️" },
            { name: "review_merge_request", description: "Reviews merge requests for code quality, potential issues, and approval readiness", icon: "🔍" },
            { name: "security_scan", description: "Scans events for security vulnerabilities, credential leaks, and insecure patterns", icon: "🛡️" },
            { name: "pipeline_analysis", description: "Analyzes CI/CD pipeline results and recommends actions for failures", icon: "⚙️" }
        ]
    };

    // ---- Demo "drip feed" for animation ----
    const DEMO_SEQUENCE = [
        { entities: { issues: 0, mrs: 0, pipelines: 1 }, activity_feed: [], pipelines: [{ ref: "main", status: "running", url: "#" }], latest_analysis: null },
        {
            entities: { issues: 1, mrs: 0, pipelines: 1 }, activity_feed: [
                { type: "Issue", id: 501, title: "Bug: Webhook endpoint fails on push events", state: "opened", analysis_status: "in_progress", action_taken: false }
            ], pipelines: [{ ref: "main", status: "running", url: "#" }], latest_analysis: null
        },
        {
            entities: { issues: 1, mrs: 0, pipelines: 1 }, activity_feed: [
                { type: "Issue", id: 501, title: "Bug: Webhook endpoint fails on push events", state: "opened", analysis_status: "done", action_taken: true }
            ], pipelines: [{ ref: "main", status: "running", url: "#" }], latest_analysis: { target: "Bug: Webhook endpoint fails on push events", result: "SEVERITY: Medium\\nCATEGORY: Bug\\n\\nThe webhook handler does not have a fallback for unsupported event types.\\n\\nRECOMMENDED: Add early return for unrecognized object_kind values.\\n\\nACTION: Posted comment to Issue #501.", action_executed: true }
        },
        {
            entities: { issues: 1, mrs: 1, pipelines: 2 }, activity_feed: [
                { type: "Merge Request", id: 901, title: "Fix: Handle unsupported webhook event types gracefully", state: "opened", analysis_status: "in_progress", action_taken: false },
                { type: "Issue", id: 501, title: "Bug: Webhook endpoint fails on push events", state: "opened", analysis_status: "done", action_taken: true }
            ], pipelines: [{ ref: "fix-webhook-push", status: "success", url: "#" }, { ref: "main", status: "running", url: "#" }], latest_analysis: { target: "Bug: Webhook endpoint fails on push events", result: "SEVERITY: Medium\\nCATEGORY: Bug\\n\\nThe webhook handler does not have a fallback for unsupported event types.\\n\\nRECOMMENDED: Add early return for unrecognized object_kind values.\\n\\nACTION: Posted comment to Issue #501.", action_executed: true }
        },
        MOCK_STATE // Final full state
    ];

    function startStreaming() {
        if (eventSource) {
            eventSource.close();
        }

        console.log("🛰️ Connecting to live activity stream...");
        eventSource = new EventSource('/api/v1/dashboard/stream');

        eventSource.onmessage = (event) => {
            if (demoMode) return; // Prioritize local demo sequence
            try {
                const state = JSON.parse(event.data);
                renderDashboard(state);
            } catch (e) {
                console.error("Error parsing stream data:", e);
            }
        };

        eventSource.onerror = (err) => {
            console.warn("⚠️ Stream connection lost. Polling fallback...", err);
            eventSource.close();
            // Fallback to polling if SSE fails
            setInterval(fetchState, 2000);
        };
    }

    async function fetchState() {
        try {
            const res = await fetch('/api/v1/dashboard/state');
            if (res.ok) {
                const data = await res.json();
                renderDashboard(data);
            }
        } catch (err) {
            if (!demoMode && previousStateStr === "") {
                renderDashboard(MOCK_STATE);
            }
        }
    }

    function renderDashboard(data) {
        // Render Stats
        animateValue(elements.issues, data.entities.issues);
        animateValue(elements.mrs, data.entities.mrs);
        animateValue(elements.pipelines, data.entities.pipelines);

        // Render Config
        const cfg = data.config || MOCK_STATE.config;
        elements.config.innerHTML = `
            <div class="config-item"><span class="config-key">Target Project</span><span class="config-val">${cfg.project}</span></div>
            <div class="config-item"><span class="config-key">Webhook</span><span class="config-val">${cfg.webhook_endpoint}</span></div>
            <div class="config-item"><span class="config-key">Mock Mode</span><span class="config-val">${cfg.mock_mode ? '🟢 ACTIVE' : '🔴 OFF'}</span></div>
            <div class="config-item"><span class="config-key">ECS Components</span><span class="config-val">${cfg.components.length} Registered</span></div>
            <div class="config-item"><span class="config-key">Duo Platform</span><span class="config-val">${cfg.duo_platform ? '🟢 ACTIVE' : '🔴 OFF'}</span></div>
        `;

        // Render Duo Tools
        const tools = data.duo_tools || MOCK_STATE.duo_tools;
        if (elements.toolsGrid && tools) {
            elements.toolsGrid.innerHTML = tools.map(tool => `
                <div class="tool-card">
                    <div class="tool-icon">${tool.icon}</div>
                    <div class="tool-info">
                        <div class="tool-name">${tool.name}</div>
                        <div class="tool-desc">${tool.description}</div>
                    </div>
                </div>
            `).join('');
        }

        // Render Pipelines
        if (!data.pipelines || data.pipelines.length === 0) {
            elements.pipelineBoard.innerHTML = `<div class="empty-state">No active pipelines detected.</div>`;
        } else {
            elements.pipelineBoard.innerHTML = data.pipelines.map(p => `
                <div class="pipeline-item">
                    <div class="pipe-ref">🌿 ${p.ref}</div>
                    <div class="pipe-status">
                        <span class="pipe-indicator ${p.status.toLowerCase()}"></span>
                        <span>${p.status}</span>
                    </div>
                </div>
            `).join('');
        }

        // Render AI Analysis
        if (data.latest_analysis) {
            const actionLine = data.latest_analysis.action_executed ? "\n\n✅ ACTION EXECUTED — POSTED TO GITLAB" : "";
            elements.analysis.innerHTML = `<strong>TARGET:</strong> ${data.latest_analysis.target}\n\n${data.latest_analysis.result.replace(/\\n/g, '\n')}${actionLine}`;
        } else {
            elements.analysis.innerHTML = `<div class="empty-state">Waiting for webhook events...</div>`;
        }

        // Render Feed
        if (!data.activity_feed || data.activity_feed.length === 0) {
            elements.feed.innerHTML = `<div class="empty-state">Monitoring webhook endpoint... waiting for events.</div>`;
        } else {
            elements.feed.innerHTML = data.activity_feed.map(item => {
                const isIssue = item.type === 'Issue';
                const statusClass = item.analysis_status === 'done' ? 'done' :
                    item.analysis_status === 'in_progress' ? 'progress' : '';
                const statusLabel = item.analysis_status === 'done' ? 'Analyzed ✅' :
                    item.analysis_status === 'in_progress' ? 'Analyzing ⏳' : 'Pending';

                return `
                <div class="feed-item ${isIssue ? 'type-issue' : 'type-mr'}">
                    <div class="feed-item-header">
                        <span class="feed-badge">${item.type} #${item.id}</span>
                        <div class="feed-status">
                            <span class="status-tag ${statusClass}">${statusLabel}</span>
                        </div>
                    </div>
                    <div class="feed-title">${item.title}</div>
                    <div class="feed-status">State: ${item.state} &nbsp;|&nbsp; Action: ${item.action_taken ? 'Executed ✅' : 'Pending ⏳'}</div>
                </div>
                `;
            }).join('');
        }
    }

    function animateValue(el, target) {
        const current = parseInt(el.textContent) || 0;
        if (current === target) return;
        el.textContent = target;
        el.style.transform = 'scale(1.2)';
        el.style.transition = 'transform 0.3s';
        setTimeout(() => { el.style.transform = 'scale(1)'; }, 300);
    }

    // Demo toggle logic — runs a scripted sequence
    elements.demoBtn.addEventListener('click', async () => {
        if (demoMode) return;
        demoMode = true;
        elements.demoBtn.textContent = '⏳ Demo Running...';
        elements.demoBtn.disabled = true;

        // Also try the backend first (in case server is running)
        try { await fetch('/api/v1/demo/trigger', { method: 'POST' }); } catch (e) { }

        // Play local demo sequence
        for (let i = 0; i < DEMO_SEQUENCE.length; i++) {
            const step = DEMO_SEQUENCE[i];
            step.config = MOCK_STATE.config;
            renderDashboard(step);
            await new Promise(r => setTimeout(r, 2500));
        }

        elements.demoBtn.textContent = '✅ Demo Complete';
        setTimeout(() => {
            elements.demoBtn.textContent = '⚡ Activate Demo Mode';
            elements.demoBtn.disabled = false;
            demoMode = false;
        }, 3000);
    });

    // Start streaming (will fall back to mock if server is unavailable)
    startStreaming();
    fetchState();
});
