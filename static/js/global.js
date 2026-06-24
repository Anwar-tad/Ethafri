/* ============================================================
📁 ፋይል፦ EthAfri/static/js/global.js
📝 ለውጥ፦ Master CEO Agent Aware - Real-time Status + UI Optimizations
✅ የተፈቱ ችግሮች፦ Page Reload Dependency, Static UI Feedback
📅 ቀን፦ 2026-06-24
============================================================ */

(function() {
    'use strict';

    document.addEventListener("DOMContentLoaded", function() {
        console.log("🚀 EthAfri Smart System Initialized.");

        // መሠረታዊ ተግባራትን አስነሳ
        initLanguageSwitcher();
        initBottomNav();
        initAutoDismissAlerts();
        initProductImageLazyLoading();
        initAgentStatusObserver(); // 🤖 አዲስ፡ የኤጀንቱን ሁኔታ በሪል-ታይም መከታተያ
        initKeyboardShortcuts();
    });

    // ============================================================
    // 🤖 1. AGENT STATUS OBSERVER (WebSocket Connection)
    // ============================================================
    function initAgentStatusObserver() {
        const dashboard = document.querySelector('[data-agent-monitor]');
        if (!dashboard) return;

        // የ WebSocket ግንኙነት መክፈቻ (ከ consumers.py ጋር ይገናኛል)
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const socket = new WebSocket(protocol + window.location.host + '/ws/agent-status/');

        socket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            if (data.type === 'status_update') {
                updateDashboardUI(data);
            }
        };

        socket.onclose = function() {
            console.warn("⚠️ Agent socket closed. Reconnecting in 5s...");
            setTimeout(initAgentStatusObserver, 5000);
        };
    }

    function updateDashboardUI(data) {
        // ዳሽቦርዱ ላይ ያሉ ቁጥሮችን በሪል-ታይም መቀየር
        const pendingEl = document.getElementById('pending-tasks-count');
        const runningEl = document.getElementById('running-task-name');
        
        if (pendingEl) pendingEl.innerText = data.task_stats.pending;
        if (runningEl) {
            runningEl.innerText = data.pending_tasks[0]?.name || "CEO is Analyzing...";
            runningEl.classList.add('text-success', 'fw-bold');
        }
    }

    // ============================================================
    // 🌍 2. LANGUAGE & UI HELPERS
    // ============================================================
    function initLanguageSwitcher() {
        const langSelect = document.querySelector('select[name="language"]');
        if (langSelect) {
            langSelect.addEventListener("change", function() {
                document.body.style.opacity = "0.5";
                this.form.submit();
            });
        }
    }

    function initBottomNav() {
        const currentPath = window.location.pathname;
        document.querySelectorAll(".bottom-nav a").forEach(link => {
            if (link.getAttribute("href") === currentPath) {
                link.classList.add("active");
            }
        });
    }

    function initAutoDismissAlerts() {
        document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
            setTimeout(() => {
                alert.style.transition = 'opacity 0.6s ease';
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 600);
            }, 5000);
        });
    }

    // ============================================================
    // 📦 3. PRODUCT TOOLS
    // ============================================================
    function initProductImageLazyLoading() {
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src || img.src;
                        observer.unobserve(img);
                    }
                });
            });
            document.querySelectorAll('.product-card img').forEach(img => observer.observe(img));
        }
    }

    // ============================================================
    // ⌨️ 4. ADMIN KEYBOARD SHORTCUTS
    // ============================================================
    function initKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // Ctrl + G -> ወደ Growth Dashboard ለመሄድ
            if (e.ctrlKey && e.key === 'g') {
                window.location.href = '/growth-dashboard/';
            }
        });
    }

    // 📋 Utility: Copy to Clipboard
    window.copyToClipboard = function(text, btn) {
        navigator.clipboard.writeText(text).then(() => {
            const originalIcon = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check text-success"></i>';
            setTimeout(() => btn.innerHTML = originalIcon, 2000);
        });
    };

})();