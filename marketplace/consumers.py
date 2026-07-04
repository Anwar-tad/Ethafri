<!-- ============================================================
📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/templates/marketplace/agent_status.html
📝 ስሪት፦ v10.18 (Autonomous Agent Monitor - Complete & Hardened Rotator)
✅ የተፈቱ ችግሮች፦ Dynamic API Key Rotator health matrix, real-time CPU load stream, interactive command shortcuts, live pending task lists, and synchronized errors badge.
📅 ቀን፦ Saturday, July 04, 2026
============================================================ -->

{% extends 'marketplace/base.html' %}
{% load i18n %}
{% load static %}

{% block extra_css %}
{% if theme.custom_css %}
<style>
    {{ theme.custom_css|safe }}
</style>
{% endif %}
<style>
    /* ካርዶቹ በይነተገናኝ እንዲሆኑ የተገጠመ ስታይል */
    .stat-box {
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    .stat-box:hover {
        transform: translateY(-3px);
    }
    .active-pending {
        border-color: #ffc107 !important;
        box-shadow: 0 4px 15px rgba(255, 193, 7, 0.25) !important;
    }
    .active-resolved {
        border-color: #198754 !important;
        box-shadow: 0 4px 15px rgba(25, 135, 84, 0.25) !important;
    }
    /* የቀጥታ የልብ ትርታ አኒሜሽን (Pulse Indicator) */
    .pulse-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        display: inline-block;
    }
    .pulse-healthy {
        background-color: #198754;
        box-shadow: 0 0 0 0 rgba(25, 135, 84, 0.7);
        animation: pulse-green 2s infinite;
    }
    .pulse-cooldown {
        background-color: #dc3545;
        box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7);
        animation: pulse-red 2s infinite;
    }
    .pulse-offline {
        background-color: #6c757d;
    }
    @keyframes pulse-green {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(25, 135, 84, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 5px rgba(25, 135, 84, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(25, 135, 84, 0); }
    }
    @keyframes pulse-red {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 5px rgba(220, 53, 69, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(220, 53, 69, 0); }
    }
</style>
{% endblock %}

{% block content %}
<div class="container-fluid py-4" id="agent-monitor" data-agent-monitor>
    
    <!-- 🏥 Dashboard Header -->
    <div class="row mb-4 align-items-center">
        <div class="col-md-5">
            <h2 class="fw-bold"><i class="fas fa-heartbeat text-danger me-2"></i> Autonomous Agent Monitor</h2>
            <p class="text-muted small">Live diagnostics of the EthAfri brain, memory, and parallel execution.</p>
        </div>
        <div class="col-md-7 text-md-end">
            <!-- ⚡ የቀጥታ የሰርቨር ሲፒዩ ጫና መከታተያ ባጅ -->
            <span class="badge bg-dark border border-info rounded-pill px-3 py-2 me-2">
                <i class="fas fa-microchip text-info me-2"></i> CPU Load: <span id="cpu-load-counter">0.50</span>
            </span>
            <span class="badge bg-dark border border-success rounded-pill px-3 py-2">
                <i class="fas fa-clock text-success me-2"></i> Uptime: <span id="uptime-counter">00:00:00</span>
            </span>
        </div>
    </div>

    <div class="row g-4">
        <!-- 🧠 Memory, Security & Model Matrix (ግራ) -->
        <div class="col-lg-4">
            
            <!-- ካርዶቹ በይነተገናኝ ሆነው ተዋቅረዋል -->
            <div class="row g-2 mb-4">
                <div class="col-6">
                    <div class="stat-box p-3 border bg-dark text-white rounded shadow-sm text-center" id="pending-card" onclick="toggleDetails('pending')" style="cursor: pointer;">
                        <div class="text-uppercase small text-muted">Pending Tasks</div>
                        <div class="h4 text-warning" id="pending-count-badge">{{ backlog_stats.pending|default:0 }}</div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="stat-box p-3 border bg-dark text-white rounded shadow-sm text-center" id="resolved-card" onclick="toggleDetails('resolved')" style="cursor: pointer;">
                        <div class="text-uppercase small text-muted">Resolved Issues</div>
                        <div class="h4 text-success" id="resolved-count-badge">{{ healing_stats.resolved|default:0 }}</div>
                    </div>
                </div>
            </div>

            <!-- 📋 በይነተገናኝ የዝርዝር ሰሌዳ (ካርዱ ሲነካ ዝርዝሩን ከታች ማሳያ) -->
            <div class="status-card p-3 mb-4 bg-dark text-white rounded border border-secondary" id="details-panel" style="display: none;">
                
                <!-- የ Pending ስራዎች ዝርዝር ሰሌዳ -->
                <div id="pending-details" style="display: none;">
                    <h6 class="fw-bold mb-3 text-warning"><i class="fas fa-clock me-2"></i>{% trans "Pending Backlog" %}</h6>
                    <div id="pending-tasks-list" style="max-height: 250px; overflow-y: auto;">
                        <!-- በጃቫስክሪፕት በላይቭ ሰዓት ይሞላል -->
                    </div>
                </div>

                <!-- የተጠገኑ ስህተቶች ዝርዝር ሰሌዳ -->
                <div id="resolved-details" style="display: none;">
                    <h6 class="fw-bold mb-3 text-success"><i class="fas fa-check-double me-2"></i>{% trans "Resolved Issues" %}</h6>
                    <div id="resolved-tasks-list" style="max-height: 250px; overflow-y: auto;">
                        {% for log in healed_logs %}
                        <div class="p-2 mb-2 border-bottom border-secondary border-opacity-25 small d-flex justify-content-between">
                            <span><i class="fas fa-check-circle text-success me-2"></i>{{ log.error_message|truncatechars:35 }}</span>
                            <small class="text-muted">{{ log.created_at|date:"H:i" }}</small>
                        </div>
                        {% empty %}
                        <div class="text-muted small py-2">{% trans "No resolved logs found." %}</div>
                        {% endfor %}
                    </div>
                </div>

            </div>
            
            <!-- 📡 API Routing & Live Health Rotator Matrix -->
            <div class="status-card p-4 mb-4 bg-dark text-white rounded border border-secondary">
                <h5 class="fw-bold mb-3 text-info"><i class="fas fa-network-wired me-2"></i> API Health & Rotator</h5>
                <div id="api-rotator-matrix">
                    <!-- 1. GEMINI -->
                    <div class="d-flex justify-content-between align-items-center mb-2 small border-bottom border-secondary pb-1">
                        <span><i class="pulse-dot pulse-healthy me-2" id="status-dot-gemini"></i>Google Gemini 2.5</span>
                        <span class="badge bg-success" id="badge-gemini">Healthy</span>
                    </div>
                    <!-- 2. GROQ -->
                    <div class="d-flex justify-content-between align-items-center mb-2 small border-bottom border-secondary pb-1">
                        <span><i class="pulse-dot pulse-healthy me-2" id="status-dot-groq"></i>Groq Llama 3.1</span>
                        <span class="badge bg-warning text-dark" id="badge-groq">Active</span>
                    </div>
                    <!-- 3. MISTRAL -->
                    <div class="d-flex justify-content-between align-items-center mb-2 small border-bottom border-secondary pb-1">
                        <span><i class="pulse-dot pulse-healthy me-2" id="status-dot-mistral"></i>Mistral AI Large</span>
                        <span class="badge bg-danger" id="badge-mistral">Active</span>
                    </div>
                    <!-- 4. OPENROUTER -->
                    <div class="d-flex justify-content-between align-items-center mb-2 small border-bottom border-secondary pb-1">
                        <span><i class="pulse-dot pulse-healthy me-2" id="status-dot-openrouter"></i>OpenRouter DeepSeek R1</span>
                        <span class="badge bg-info" id="badge-openrouter">Active</span>
                    </div>
                    <!-- 5. HUGGINGFACE -->
                    <div class="d-flex justify-content-between align-items-center mb-2 small border-bottom border-secondary pb-1">
                        <span><i class="pulse-dot pulse-healthy me-2" id="status-dot-huggingface"></i>HuggingFace Serverless</span>
                        <span class="badge bg-secondary" id="badge-huggingface">Active</span>
                    </div>
                    <!-- 6. GITHUB -->
                    <div class="d-flex justify-content-between align-items-center mb-1 small">
                        <span><i class="pulse-dot pulse-healthy me-2" id="status-dot-github"></i>GitHub Models Catalog</span>
                        <span class="badge bg-primary" id="badge-github">Active</span>
                    </div>
                </div>
            </div>

            <!-- 🛠️ Executive Command Shortcuts -->
            {% if user.is_staff %}
            <div class="status-card p-4 mb-4 bg-dark text-white rounded border border-secondary">
                <h5 class="fw-bold mb-3 text-white"><i class="fas fa-tools me-2 text-white-50"></i> Quick Actions</h5>
                <div class="d-grid gap-2">
                    <a href="{% url 'trigger_evolution' %}" class="btn btn-sm btn-outline-success text-start">
                        <i class="fas fa-sync-alt me-2"></i> Trigger CEO Evolution Cycle
                    </a>
                    <a href="{% url 'owner_directive' %}" class="btn btn-sm btn-outline-info text-start">
                        <i class="fas fa-crown me-2"></i> Post Owner Directive
                    </a>
                </div>
            </div>
            {% endif %}
        </div>

        <!-- 📟 Live Agent CL Terminal (ቀኝ) -->
        <div class="col-lg-8">
            <div class="terminal-window h-100 d-flex flex-column bg-dark rounded shadow-lg" style="min-height: 520px;">
                <div class="terminal-header p-2 border-bottom border-secondary bg-secondary bg-opacity-25">
                    <small class="text-white-50">ethafri-ceo-agent@system:~/logs</small>
                </div>
                <div class="terminal-body flex-grow-1 p-3 text-light font-monospace" id="cl-terminal" style="overflow-y: auto; max-height: 470px;">
                    <div class="terminal-line">
                        <span class="text-muted">[{{ live_time|date:"H:i:s" }}]</span> 
                        <span class="text-info">➜ WebSocket Connected. Waiting for next CEO Cycle...</span>
                    </div>
                    {% for log in cycle_logs %}
                    <div class="terminal-line">
                        {% if log.message %}
                            <span class="text-muted">[{{ log.time }}]</span> 
                            <span class="{% if log.type == 'success' %}text-success{% elif log.type == 'error' %}text-danger{% else %}text-info{% endif %}">➜ {{ log.message }}</span>
                        {% else %}
                            <span class="text-info">➜ {{ log }}</span>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>

    <!-- ============================================================
    👑 3. ADMIN DIAGNOSTIC CENTER (የአድሚን መመርመሪያ ማዕከል)
    ============================================================ -->
    {% if user.is_staff %}
    <div class="row g-4 mt-2">
        <!-- 1. የትውስታ መዝገብ (RAG Memory) -->
        <div class="col-md-4">
            <div class="status-card p-4 bg-dark text-white rounded border border-info h-100">
                <h5 class="fw-bold mb-3 text-info"><i class="fas fa-brain me-2"></i> RAG Memory Map</h5>
                <div class="d-flex justify-content-between mb-2 pb-1 border-bottom border-secondary small">
                    <span>{% trans "Overall Success Rate" %}</span>
                    <span class="text-success fw-bold">{{ success_rate|floatformat:1 }}%</span>
                </div>
                {% for stat in memory_stats %}
                <div class="d-flex justify-content-between align-items-center mb-1 text-white-50 small">
                    <span><i class="fas fa-database me-2" style="font-size: 0.7rem;"></i>{{ stat.memory_type|title }} Memories</span>
                    <span class="badge bg-secondary">{{ stat.count }}</span>
                </div>
                {% empty %}
                <div class="text-muted small py-2">{% trans "No semantic memories stored yet." %}</div>
                {% endfor %}
            </div>
        </div>

        <!-- 2. የደህንነት ኦዲት (Security Log) -->
        <div class="col-md-4">
            <div class="status-card p-4 bg-dark text-white rounded border border-danger h-100">
                <h5 class="fw-bold mb-3 text-danger"><i class="fas fa-shield-halved me-2"></i> Security Shield Logs</h5>
                <div class="d-flex justify-content-between mb-2 pb-1 border-bottom border-secondary small">
                    <span>{% trans "Vulnerabilities Found" %}</span>
                    <span class="text-danger fw-bold">
                        {% if security_issues %}
                            {{ security_issues|length }} Active
                        {% else %}
                            0 Active
                        {% endif %}
                    </span>
                </div>
                <div style="max-height: 150px; overflow-y: auto;">
                    {% for issue in security_issues %}
                    <div class="p-1 mb-1 border-bottom border-secondary border-opacity-25 small text-white-50">
                        <span class="badge bg-danger me-1" style="font-size: 0.55rem;">{{ issue.severity|upper }}</span>
                        {{ issue.description|truncatechars:45 }}
                    </div>
                    {% empty %}
                    <div class="text-success small py-2"><i class="fas fa-check-circle me-2"></i>{% trans "No vulnerabilities detected. AST Shield is solid!" %}</div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- 3. የ AI የትንበያ መዝገቦች (Predictions) -->
        <div class="col-md-4">
            <div class="status-card p-4 bg-dark text-white rounded border border-warning h-100">
                <h5 class="fw-bold mb-3 text-warning"><i class="fas fa-chart-line me-2"></i> Predictive Brain Forecasts</h5>
                <div class="d-flex justify-content-between mb-2 pb-1 border-bottom border-secondary small">
                    <span>{% trans "Total System Predictions" %}</span>
                    <span class="text-warning fw-bold">{{ prediction_stats.total|default:0 }}</span>
                </div>
                <div class="small text-white-50">
                    <div class="d-flex justify-content-between mb-1">
                        <span>Traffic Forecasts</span>
                        <span>{{ prediction_stats.traffic|default:0 }}</span>
                    </div>
                    <div class="d-flex justify-content-between mb-1">
                        <span>SEO Forecasts</span>
                        <span>{{ prediction_stats.seo|default:0 }}</span>
                    </div>
                    <div class="d-flex justify-content-between">
                        <span>Marketing Notifications</span>
                        <span>{{ marketing_stats.notifications|default:0 }} pending</span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- 🛠️ 4. ንቁ የሰርቨር ስህተቶች ሰሌዳ (Active Unresolved Errors Table) -->
    <div class="row mt-4">
        <div class="col-12">
            <div class="status-card p-4 bg-dark text-white rounded border border-secondary">
                <h5 class="fw-bold mb-3 text-danger"><i class="fas fa-bug me-2"></i> Active Unresolved Server Errors</h5>
                <div class="table-responsive small">
                    <table class="table table-dark table-hover table-borderless align-middle mb-0">
                        <thead>
                            <tr class="border-bottom border-secondary text-white-50">
                                <th>{% trans "Task Name" %}</th>
                                <th>{% trans "Error Type" %}</th>
                                <th>{% trans "Error Message" %}</th>
                                <th>{% trans "Logged At" %}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for err in unresolved_errors %}
                            <tr class="border-bottom border-secondary border-opacity-10 text-white-50">
                                <td class="fw-bold text-white">{{ err.task_name }}</td>
                                <td><span class="badge bg-secondary">{{ err.error_type }}</span></td>
                                <td class="text-danger">{{ err.error_message|truncatechars:80 }}</td>
                                <td>{{ err.created_at|date:"Y-m-d H:i" }}</td>
                            </tr>
                            {% empty %}
                            <tr>
                                <td colspan="4" class="text-success text-center py-3"><i class="fas fa-check-circle me-2"></i>{% trans "Zero active unresolved errors! The healer is completely caught up." %}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    {% endif %}

</div>
{% endblock %}

{% block extra_js %}
<script>
    // ⏰ REAL SERVER UPTIME CALCULATOR
    const serverBootTimeStr = "{{ agent_status.timestamp|default:'' }}";
    const startTime = serverBootTimeStr ? Date.parse(serverBootTimeStr) : Date.now();
    
    setInterval(() => {
        const diff = Math.floor((Date.now() - startTime) / 1000);
        document.getElementById('uptime-counter').innerText = new Date(diff * 1000).toISOString().substr(11, 8);
    }, 1000);

    // 📟 Terminal Auto-Scroll
    function scrollTerminal() {
        const term = document.getElementById('cl-terminal');
        if (term) term.scrollTop = term.scrollHeight;
    }

    let livePendingTasks = [];

    // የ Pending ስራዎችን በእውነተኛ ሰዓት ወደ HTML መለወጫ
    function renderPendingTasksList() {
        const listContainer = document.getElementById('pending-tasks-list');
        if (!listContainer) return;
        
        if (livePendingTasks.length === 0) {
            listContainer.innerHTML = '<div class="text-muted small py-2">No pending tasks. Backlog is clear!</div>';
            return;
        }

        let html = '';
        livePendingTasks.forEach(task => {
            let badgeColor = 'bg-info';
            if (task.priority === 'Critical') badgeColor = 'bg-danger';
            else if (task.priority === 'High') badgeColor = 'bg-warning text-dark';
            
            html += `
                <div class="p-2 mb-2 border-bottom border-secondary border-opacity-25 small d-flex justify-content-between align-items-center">
                    <div>
                        <span class="badge ${badgeColor} me-2" style="font-size: 0.6rem;">${task.priority}</span>
                        <span class="fw-bold">${task.name}</span>
                    </div>
                    <small class="text-muted">📁 ${task.site || 'Global'}</small>
                </div>
            `;
        });
        listContainer.innerHTML = html;
    }

    function toggleDetails(type) {
        const panel = document.getElementById('details-panel');
        const pendingSection = document.getElementById('pending-details');
        const resolvedSection = document.getElementById('resolved-details');
        const pendingCard = document.getElementById('pending-card');
        const resolvedCard = document.getElementById('resolved-card');

        if (panel.style.display === 'block' && 
            ((type === 'pending' && pendingSection.style.display === 'block') || 
             (type === 'resolved' && resolvedSection.style.display === 'block'))) {
            panel.style.display = 'none';
            pendingCard.classList.remove('active-pending');
            resolvedCard.classList.remove('active-resolved');
            return;
        }

        panel.style.display = 'block';

        if (type === 'pending') {
            pendingSection.style.display = 'block';
            resolvedSection.style.display = 'none';
            pendingCard.classList.add('active-pending');
            resolvedCard.classList.remove('active-resolved');
            renderPendingTasksList();
        } else {
            pendingSection.style.display = 'none';
            resolvedSection.style.display = 'block';
            resolvedCard.classList.add('active-resolved');
            pendingCard.classList.remove('active-pending');
        }
    }

    // 📟 WebSocket Auto-Updater
    document.addEventListener('agent_update', function(event) {
        const data = event.detail;
        const term = document.getElementById('cl-terminal');
        if (!term) return;
        
        const timestamp = new Date().toLocaleTimeString();
        
        // 1. የቀጥታ ተርሚናል ሎጎችን ማሳየት
        if (data.type === 'terminal_log') {
            const log = data.log || {};
            let logClass = 'text-info';
            if (log.type === 'success') logClass = 'text-success';
            else if (log.type === 'error') logClass = 'text-danger';
            
            const line = document.createElement('div');
            line.className = 'terminal-line mb-1';
            line.innerHTML = `<span class="text-muted">[${log.time || timestamp}]</span> ➜ <span class="${logClass}">${log.message || ''}</span>`;
            term.appendChild(line);
            scrollTerminal();
        }
        // 2. የቁጥር መለኪያዎችን፣ ሲፒዩ ጫናን እና የባክሎግ መዝገቦችን ማዘመን
        else if (data.type === 'status_update' || data.type === 'live_stats') {
            const pendingCountEl = document.getElementById('pending-count-badge');
            const resolvedCountEl = document.getElementById('resolved-count-badge');
            const cpuLoadCounter = document.getElementById('cpu-load-counter');
            
            if (pendingCountEl && data.task_stats) {
                pendingCountEl.innerText = data.task_stats.pending;
            }
            if (resolvedCountEl && data.healing) {
                resolvedCountEl.innerText = data.healing.resolved;
            }
            if (cpuLoadCounter && data.cpu_load !== undefined) {
                cpuLoadCounter.innerText = parseFloat(data.cpu_load).toFixed(2);
            }

            // የላይቭ የባክሎግ ዝርዝር መዝገብን ማዘመን
            if (data.pending_tasks) {
                livePendingTasks = data.pending_tasks;
                if (document.getElementById('pending-details').style.display === 'block') {
                    renderPendingTasksList();
                }
            }
            
            // የኤፒአይ ኪዎች የቀጥታ ጤና መለኪያ (Dynamic API Health State Engine)
            const providers = ['gemini', 'groq', 'mistral', 'openrouter', 'huggingface', 'github'];
            providers.forEach(prov => {
                const dot = document.getElementById(`status-dot-${prov}`);
                const badge = document.getElementById(`badge-${prov}`);
                if (!dot || !badge) return;
                
                // በካሽ ውስጥ የተቀመጡ የ 429 እገዳዎችን (Cooldown) መፈተሽ
                const isCooldown = data.api_cooldowns ? data.api_cooldowns[prov] : false;
                const isConfigured = data.api_configured ? data.api_configured[prov] : true;
                
                if (!isConfigured) {
                    dot.className = 'pulse-dot pulse-offline me-2';
                    badge.className = 'badge bg-secondary';
                    badge.innerText = 'Offline';
                } else if (isCooldown) {
                    dot.className = 'pulse-dot pulse-cooldown me-2';
                    badge.className = 'badge bg-danger';
                    badge.innerText = 'Rate Limited';
                } else {
                    dot.className = 'pulse-dot pulse-healthy me-2';
                    badge.className = 'badge bg-success';
                    badge.innerText = 'Active';
                }
            });
        }
    });

    scrollTerminal();
</script>
{% endblock %}