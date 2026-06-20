/* ============================================================
📁 ፋይል፦ EthAfri/static/js/global.js
📝 ለውጥ፦ All Shared Scripts — Multi-Site Support + Product Cards
📅 ቀን፦ 2026-06-20
============================================================ */

(function() {
    'use strict';

    // ============================================================
    // 1. DOM Ready Handler
    // ============================================================
    document.addEventListener("DOMContentLoaded", function() {
        console.log("🚀 EthAfri Smart System Initialized.");

        // Initialize all modules
        initLanguageSwitcher();
        initBottomNav();
        initAutoDismissAlerts();
        initProductImageLazyLoading();
        initProductCardEnhancements();
        initTabPersistence();
        initFormHelpers();
        initKeyboardShortcuts();
        initResultAutoRefresh();
        initSiteSelector();
    });

    // ============================================================
    // 2. Language Switcher
    // ============================================================
    function initLanguageSwitcher() {
        const langSelect = document.querySelector('select[name="language"]');
        if (langSelect) {
            langSelect.addEventListener("change", function() {
                document.body.style.opacity = "0.6";
                document.body.style.transition = "opacity 0.3s ease";
                this.form.submit();
            });
        }
    }

    // ============================================================
    // 3. Bottom Navigation Active State
    // ============================================================
    function initBottomNav() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll(".bottom-nav a");
        navLinks.forEach(link => {
            const linkPath = link.getAttribute("href");
            if (linkPath && (currentPath === linkPath || 
                (linkPath !== '/' && currentPath.startsWith(linkPath)))) {
                link.classList.add("active");
                const icon = link.querySelector("i");
                if (icon) icon.style.transform = "scale(1.1)";
            }
        });
    }

    // ============================================================
    // 4. Auto-dismiss Alerts
    // ============================================================
    function initAutoDismissAlerts() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(alert => {
            setTimeout(() => {
                alert.style.transition = 'opacity 0.5s ease';
                alert.style.opacity = '0';
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.remove();
                    }
                }, 500);
            }, 5000);
        });
    }

    // ============================================================
    // 5. Product Image Lazy Loading (Shared: home + product_detail)
    // ============================================================
    function initProductImageLazyLoading() {
        if ('IntersectionObserver' in window) {
            const images = document.querySelectorAll(
                '.product-card .img-container img[data-src], ' +
                '.related-product-card .img-container img[data-src]'
            );
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                        imageObserver.unobserve(img);
                    }
                });
            });
            images.forEach(img => imageObserver.observe(img));
        }
    }

    // ============================================================
    // 6. Product Card Enhancements (Shared: home + product_detail)
    // ============================================================
    function initProductCardEnhancements() {
        const cards = document.querySelectorAll('.product-card, .related-product-card');
        cards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transition = 'transform 0.3s ease, box-shadow 0.3s ease';
            });
        });
    }

    // ============================================================
    // 7. Tab Persistence (Site Detail + Product Detail)
    // ============================================================
    function initTabPersistence() {
        // Site Detail Tabs
        const siteTabButtons = document.querySelectorAll('#siteTabs button');
        siteTabButtons.forEach(button => {
            button.addEventListener('shown.bs.tab', function(e) {
                const tabId = e.target.getAttribute('data-bs-target');
                if (tabId) {
                    try {
                        localStorage.setItem('activeSiteTab', tabId);
                    } catch (e) {}
                }
            });
        });

        // Product Detail Tabs
        const productTabButtons = document.querySelectorAll('#langTabs button');
        productTabButtons.forEach(button => {
            button.addEventListener('shown.bs.tab', function(e) {
                const tabId = e.target.getAttribute('data-bs-target');
                if (tabId) {
                    try {
                        localStorage.setItem('activeProductTab', tabId);
                    } catch (e) {}
                }
            });
        });

        // Restore Site Tab
        try {
            const savedSiteTab = localStorage.getItem('activeSiteTab');
            if (savedSiteTab) {
                const targetButton = document.querySelector(`#siteTabs button[data-bs-target="${savedSiteTab}"]`);
                if (targetButton && typeof bootstrap !== 'undefined') {
                    const tab = new bootstrap.Tab(targetButton);
                    tab.show();
                }
            }
        } catch (e) {}

        // Restore Product Tab
        try {
            const savedProductTab = localStorage.getItem('activeProductTab');
            if (savedProductTab) {
                const targetButton = document.querySelector(`#langTabs button[data-bs-target="${savedProductTab}"]`);
                if (targetButton && typeof bootstrap !== 'undefined') {
                    const tab = new bootstrap.Tab(targetButton);
                    tab.show();
                }
            }
        } catch (e) {}
    }

    // ============================================================
    // 8. Form Helpers
    // ============================================================
    function initFormHelpers() {
        // 8.1 Campaign Form — Auto-fill Subject
        const campaignType = document.getElementById('campaign_type');
        const campaignName = document.getElementById('name');
        const subjectField = document.getElementById('subject');
        
        if (campaignType && campaignName && subjectField) {
            campaignName.addEventListener('input', function() {
                if (!subjectField.value) {
                    const type = campaignType.options[campaignType.selectedIndex]?.text || 'Campaign';
                    subjectField.value = type + ': ' + this.value;
                }
            });
        }

        // 8.2 Product Form — Price Formatting
        const priceInput = document.getElementById('id_price');
        if (priceInput) {
            priceInput.addEventListener('blur', function() {
                const val = parseFloat(this.value);
                if (!isNaN(val) && val >= 0) {
                    this.value = val.toFixed(2);
                }
            });
        }

        // 8.3 Form Validation — Required fields
        const forms = document.querySelectorAll('form[data-validate]');
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                const required = this.querySelectorAll('[required]');
                let valid = true;
                required.forEach(field => {
                    if (!field.value.trim()) {
                        field.classList.add('is-invalid');
                        valid = false;
                    } else {
                        field.classList.remove('is-invalid');
                    }
                });
                if (!valid) {
                    e.preventDefault();
                    const firstInvalid = this.querySelector('.is-invalid');
                    if (firstInvalid) {
                        firstInvalid.focus();
                    }
                }
            });
        });
    }

    // ============================================================
    // 9. Keyboard Shortcuts (Admin)
    // ============================================================
    function initKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // Ctrl+Shift+E → Run Evolution
            if (e.ctrlKey && e.shiftKey && (e.key === 'e' || e.key === 'E')) {
                e.preventDefault();
                const evoBtn = document.querySelector('form[action*="trigger-evolution"] button[type="submit"]');
                if (evoBtn) {
                    evoBtn.click();
                }
            }
            // Ctrl+Shift+G → Growth Dashboard
            if (e.ctrlKey && e.shiftKey && (e.key === 'g' || e.key === 'G')) {
                e.preventDefault();
                const dashLink = document.querySelector('a[href*="growth-dashboard"]');
                if (dashLink) {
                    window.location.href = dashLink.href;
                }
            }
            // Ctrl+Shift+S → Sites Dashboard
            if (e.ctrlKey && e.shiftKey && (e.key === 's' || e.key === 'S')) {
                e.preventDefault();
                const sitesLink = document.querySelector('a[href*="sites-dashboard"]');
                if (sitesLink) {
                    window.location.href = sitesLink.href;
                }
            }
            // Ctrl+Shift+M → Marketing Dashboard
            if (e.ctrlKey && e.shiftKey && (e.key === 'm' || e.key === 'M')) {
                e.preventDefault();
                const marketingLink = document.querySelector('a[href*="marketing-dashboard"]');
                if (marketingLink) {
                    window.location.href = marketingLink.href;
                }
            }
        });
    }

    // ============================================================
    // 10. Result Auto-Refresh (Evolution Result)
    // ============================================================
    function initResultAutoRefresh() {
        const statusElement = document.querySelector('[data-task-status]');
        if (statusElement) {
            const status = statusElement.getAttribute('data-task-status');
            if (status === 'Running') {
                setTimeout(function() {
                    location.reload();
                }, 5000);
            }
        }
    }

    // ============================================================
    // 11. Site Selector (Multi-Site)
    // ============================================================
    function initSiteSelector() {
        const siteSelect = document.getElementById('site_select');
        if (siteSelect) {
            siteSelect.addEventListener('change', function() {
                const form = this.closest('form');
                if (form) {
                    form.submit();
                }
            });
        }
    }

    // ============================================================
    // 12. Utility: Smooth Scroll
    // ============================================================
    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    // ============================================================
    // 13. Utility: Copy to Clipboard (product_detail)
    // ============================================================
    window.copyToClipboard = function(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                const btn = event?.target?.closest('button');
                if (btn) {
                    const original = btn.innerHTML;
                    btn.innerHTML = '<i class="fas fa-check"></i>';
                    setTimeout(() => {
                        btn.innerHTML = original;
                    }, 2000);
                }
            }).catch(() => {
                fallbackCopy(text);
            });
        } else {
            fallbackCopy(text);
        }
    };

    function fallbackCopy(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            alert('Link copied to clipboard!');
        } catch (e) {
            alert('Could not copy link. Please copy manually.');
        }
        document.body.removeChild(textarea);
    }

    console.log("✅ EthAfri Global JS initialized successfully.");
})();