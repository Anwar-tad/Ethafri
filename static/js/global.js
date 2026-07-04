/* ============================================================
📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/static/js/global.js
📝 ስሪት፦ v1.5 WebSocket Publisher & PWA Service Worker Registered
✅ የተፈቱ ችግሮች፦ Integrated PWA Service Worker for offline asset caching, WebSocket custom event broadcasting, and global image fallback.
📅 ቀን፦ Saturday, July 04, 2026
============================================================ */

(function() {
    'use strict';

    document.addEventListener("DOMContentLoaded", function() {
        console.log("🚀 EthAfri Smart System Initialized.");

        // መሠረታዊ ተግባራትን በአንድነት ማስነሳት
        initLanguageSwitcher();
        initBottomNav();
        initAutoDismissAlerts();
        initProductImageLazyLoading();
        initAgentStatusObserver(); 
        initKeyboardShortcuts();
        initGlobalImageFallback(); // ምስሎች መጫን ሲሳናቸው ጥበቃ የሚያደርግ የጋራ ሎጂክ
        initScrollDraggables();    // ማንኛውንም አግድም ማውጫ በጣት እንዲንቀሳቀስ የሚያደርግ
        initServiceWorker();       // 🟢 አዲስ፦ የ PWA Service Worker መመዝገቢያ ፈንክሽን [1]
    });

    // ============================================================
    // 🟢 1. PWA SERVICE WORKER REGISTRATION (የኦፍላይን መቆለፍ መከላከያ)
    // ============================================================
    function initServiceWorker() {
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', function() {
                // service-worker.js ፋይልን በብሮውዘር ላይ በደህንነት መመዝገብ [1]
                navigator.serviceWorker.register('/static/js/service-worker.js')
                    .then(function(registration) {
                        console.log('🟢 PWA Service Worker registered successfully with scope: ', registration.scope);
                    })
                    .catch(function(error) {
                        console.warn('⚠️ PWA Service Worker registration failed: ', error);
                    });
            });
        }
    }

    // ============================================================
    // 🤖 2. AGENT STATUS OBSERVER (WebSocket Connection)
    // ============================================================
    function initAgentStatusObserver() {
        const dashboard = document.querySelector('[data-agent-monitor]');
        if (!dashboard) return;

        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const socket = new WebSocket(protocol + window.location.host + '/ws/agent-status/');

        socket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            
            // የ CL ተርሚናሉ (agent_status.html) በእውነተኛ ሰዓት እንዲያድግ ክስተቱን ማሰራጨት [1]
            const event = new CustomEvent('agent_update', { detail: data });
            document.dispatchEvent(event);
            
            if (data.type === 'status_update') {
                updateDashboardUI(data);
            }
        };

        socket.onclose = function() {
            console.warn("⚠️ Agent status socket closed. Reconnecting...");
            setTimeout(initAgentStatusObserver, 5000);
        };
    }

    function updateDashboardUI(data) {
        const pendingEl = document.getElementById('pending-tasks-count');
        const runningEl = document.getElementById('running-task-name');
        
        if (pendingEl) pendingEl.innerText = data.task_stats.pending;
        if (runningEl) {
            runningEl.innerText = data.pending_tasks[0]?.name || "CEO is Analyzing...";
            runningEl.classList.add('text-success', 'fw-bold');
        }
    }

    // ============================================================
    // 🌍 3. LANGUAGE & UI HELPERS
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
        document.querySelectorAll(".bottom-nav-custom a, .bottom-nav a").forEach(link => {
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
    // 📦 4. PRODUCT TOOLS (LAZY LOADING & FALLBACK)
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

    function initGlobalImageFallback() {
        document.querySelectorAll('img').forEach(img => {
            img.addEventListener('error', function() {
                this.src = 'https://loremflickr.com/400/300/product?lock=' + Date.now();
            });
        });
    }

    function initScrollDraggables() {
        document.querySelectorAll('.scroll-draggable').forEach(scrollContainer => {
            let isDown = false;
            let startX;
            let scrollLeft;

            scrollContainer.addEventListener('mousedown', (e) => {
                isDown = true;
                startX = e.pageX - scrollContainer.offsetLeft;
                scrollLeft = scrollContainer.scrollLeft;
            });

            scrollContainer.addEventListener('mouseleave', () => { isDown = false; });
            scrollContainer.addEventListener('mouseup', () => { isDown = false; });

            scrollContainer.addEventListener('mousemove', (e) => {
                if (!isDown) return;
                e.preventDefault();
                const x = e.pageX - scrollContainer.offsetLeft;
                const walk = (x - startX) * 1.5;
                scrollContainer.scrollLeft = scrollLeft - walk;
            });
        });
    }

    // ============================================================
    // ⌨️ 5. KEYBOARD SHORTCUTS
    // ============================================================
    function initKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'g') {
                window.location.href = '/growth-dashboard/';
            }
        });
    }

    window.copyToClipboard = function(text, btn) {
        navigator.clipboard.writeText(text).then(() => {
            const originalIcon = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check text-success"></i>';
            setTimeout(() => btn.innerHTML = originalIcon, 2000);
        });
    };

})();