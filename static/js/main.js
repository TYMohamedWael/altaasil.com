/**
 * main.js – Core functionality for Littattafan Hausa
 */

(function () {
    'use strict';

    /* ── CSRF Token Helper ─────────────────────────────────── */
    window.getCSRF = function () {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    };

    /* ── Dark Mode ─────────────────────────────────────────── */
    window.toggleDark = function () {
        var root = document.getElementById('htmlRoot');
        root.classList.toggle('dark');
        var isDark = root.classList.contains('dark');
        localStorage.setItem('darkMode', isDark);
        var btn = document.getElementById('darkBtn');
        if (btn) btn.textContent = isDark ? '☀️' : '🌙';
    };

    // Apply saved preference on load
    if (localStorage.getItem('darkMode') === 'true') {
        document.getElementById('htmlRoot').classList.add('dark');
        var btn = document.getElementById('darkBtn');
        if (btn) btn.textContent = '☀️';
    }

    /* ── Language Switcher Dropdown ─────────────────────────── */
    window.toggleLangDropdown = function () {
        var dropdown = document.getElementById('langDropdown');
        var chevron = document.getElementById('langChevron');
        var btn = document.getElementById('langToggleBtn');
        if (!dropdown) return;

        var isOpen = !dropdown.classList.contains('hidden');
        if (isOpen) {
            dropdown.classList.add('hidden');
            if (chevron) chevron.style.transform = '';
            if (btn) btn.setAttribute('aria-expanded', 'false');
        } else {
            dropdown.classList.remove('hidden');
            if (chevron) chevron.style.transform = 'rotate(180deg)';
            if (btn) btn.setAttribute('aria-expanded', 'true');
        }
    };

    // Close language dropdown on outside click
    document.addEventListener('click', function (e) {
        var wrapper = document.getElementById('langSwitcher');
        var dropdown = document.getElementById('langDropdown');
        if (wrapper && dropdown && !wrapper.contains(e.target)) {
            dropdown.classList.add('hidden');
            var chevron = document.getElementById('langChevron');
            var btn = document.getElementById('langToggleBtn');
            if (chevron) chevron.style.transform = '';
            if (btn) btn.setAttribute('aria-expanded', 'false');
        }
    });

    // Close on Escape
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            var dropdown = document.getElementById('langDropdown');
            if (dropdown && !dropdown.classList.contains('hidden')) {
                dropdown.classList.add('hidden');
                var chevron = document.getElementById('langChevron');
                var btn = document.getElementById('langToggleBtn');
                if (chevron) chevron.style.transform = '';
                if (btn) {
                    btn.setAttribute('aria-expanded', 'false');
                    btn.focus();
                }
            }
        }
    });

    /* ── Mobile Menu Toggle ────────────────────────────────── */
    window.toggleMobileMenu = function () {
        var menu = document.getElementById('mobileMenu');
        var openIcon = document.getElementById('menuIcon');
        var closeIcon = document.getElementById('menuCloseIcon');
        if (!menu) return;
        menu.classList.toggle('open');
        if (openIcon) openIcon.classList.toggle('hidden');
        if (closeIcon) closeIcon.classList.toggle('hidden');
    };

    /* ── Bottom Nav Active State ───────────────────────────── */
    (function setActiveNav() {
        var path = window.location.pathname;
        var navMap = {
            'bnav-home': ['/', '/ha', '/en', '/ar'],
            'bnav-books': ['/books/'],
            'bnav-categories': ['/categories/'],
            'bnav-profile': ['/profile/'],
            'bnav-login': ['/login/']
        };
        Object.keys(navMap).forEach(function (id) {
            var el = document.getElementById(id);
            if (!el) return;
            navMap[id].forEach(function (p) {
                if (path === p || (p !== '/' && path.indexOf(p) !== -1)) {
                    el.classList.add('active');
                }
            });
        });
    })();

    /* ── Scroll-to-Top Button ──────────────────────────────── */
    (function initScrollTop() {
        // Create button if not present
        var existing = document.querySelector('.scroll-top-btn');
        if (!existing) {
            var btn = document.createElement('button');
            btn.className = 'scroll-top-btn bg-primary text-white w-11 h-11 rounded-full shadow-lg flex items-center justify-center hover:bg-primary-light transition-colors';
            btn.setAttribute('aria-label', 'Scroll to top');
            btn.innerHTML = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18"/></svg>';
            btn.addEventListener('click', function () {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
            document.body.appendChild(btn);
            existing = btn;
        }
        window.addEventListener('scroll', function () {
            if (window.scrollY > 300) {
                existing.classList.add('visible');
            } else {
                existing.classList.remove('visible');
            }
        }, { passive: true });
    })();

    /* ── Smooth Scroll for Anchor Links ────────────────────── */
    document.addEventListener('click', function (e) {
        var link = e.target.closest('a[href^="#"]');
        if (!link) return;
        var target = document.querySelector(link.getAttribute('href'));
        if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });

    /* ── Toast Notification System ─────────────────────────── */
    window.showToast = function (message, type) {
        type = type || 'success';
        var container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        var toast = document.createElement('div');
        toast.className = 'toast toast-' + type;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(function () {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(function () { toast.remove(); }, 300);
        }, 4000);
    };

    /* ── Lazy Loading for Images ───────────────────────────── */
    if ('IntersectionObserver' in window) {
        var lazyObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    var img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                    }
                    img.classList.add('loaded');
                    lazyObserver.unobserve(img);
                }
            });
        }, { rootMargin: '100px' });

        document.querySelectorAll('img[data-src]').forEach(function (img) {
            lazyObserver.observe(img);
        });
    }

    /* ── Service Worker Registration ───────────────────────── */
    if ('serviceWorker' in navigator) {
        var swPath = document.querySelector('meta[name="sw-path"]');
        var swUrl = swPath ? swPath.content : '/static/sw.js';
        navigator.serviceWorker.register(swUrl).catch(function () { });
    }

})();
