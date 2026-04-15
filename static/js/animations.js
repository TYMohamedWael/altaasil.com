/**
 * animations.js – Micro-interactions and animations for Littattafan Hausa
 */

(function () {
    'use strict';

    /* ── Intersection Observer: Fade-in on Scroll ──────────── */
    if ('IntersectionObserver' in window) {
        var revealObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    revealObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

        document.querySelectorAll('.scroll-reveal').forEach(function (el) {
            revealObserver.observe(el);
        });

        // Re-observe on DOM changes (for dynamic content)
        var mutObserver = new MutationObserver(function () {
            document.querySelectorAll('.scroll-reveal:not(.visible)').forEach(function (el) {
                revealObserver.observe(el);
            });
        });
        mutObserver.observe(document.body, { childList: true, subtree: true });
    }

    /* ── Number Counter Animation ──────────────────────────── */
    window.animateCounter = function (el, target, duration) {
        duration = duration || 1500;
        var start = 0;
        var startTime = null;

        function step(timestamp) {
            if (!startTime) startTime = timestamp;
            var progress = Math.min((timestamp - startTime) / duration, 1);
            // Ease-out cubic
            var eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.floor(eased * target).toLocaleString();
            if (progress < 1) {
                requestAnimationFrame(step);
            } else {
                el.textContent = target.toLocaleString();
            }
        }
        requestAnimationFrame(step);
    };

    // Auto-detect stat counters
    if ('IntersectionObserver' in window) {
        var counterObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    var el = entry.target;
                    var target = parseInt(el.dataset.count || el.textContent, 10);
                    if (!isNaN(target)) {
                        window.animateCounter(el, target);
                    }
                    counterObserver.unobserve(el);
                }
            });
        }, { threshold: 0.5 });

        document.querySelectorAll('[data-count]').forEach(function (el) {
            counterObserver.observe(el);
        });
    }

    /* ── Staggered Card Reveal ─────────────────────────────── */
    if ('IntersectionObserver' in window) {
        var cardObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    var cards = entry.target.querySelectorAll('.card-reveal');
                    cards.forEach(function (card, i) {
                        card.style.animationDelay = (i * 0.1) + 's';
                        card.classList.add('animate-fadeInUp');
                    });
                    cardObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });

        document.querySelectorAll('.card-reveal-container').forEach(function (el) {
            cardObserver.observe(el);
        });
    }

    /* ── Smooth Page Transitions ───────────────────────────── */
    document.addEventListener('DOMContentLoaded', function () {
        document.body.classList.add('animate-fadeIn');
    });

    /* ── Ripple Effect on Buttons ──────────────────────────── */
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('.ripple-btn');
        if (!btn) return;

        var rect = btn.getBoundingClientRect();
        var ripple = document.createElement('span');
        var size = Math.max(rect.width, rect.height);

        ripple.style.cssText =
            'position:absolute;border-radius:50%;background:rgba(255,255,255,0.3);' +
            'width:' + size + 'px;height:' + size + 'px;' +
            'left:' + (e.clientX - rect.left - size / 2) + 'px;' +
            'top:' + (e.clientY - rect.top - size / 2) + 'px;' +
            'transform:scale(0);animation:ripple 0.6s linear;pointer-events:none;';

        btn.style.position = 'relative';
        btn.style.overflow = 'hidden';
        btn.appendChild(ripple);

        setTimeout(function () { ripple.remove(); }, 600);
    });

    // Inject ripple keyframes
    var style = document.createElement('style');
    style.textContent = '@keyframes ripple{to{transform:scale(4);opacity:0;}}';
    document.head.appendChild(style);

})();
