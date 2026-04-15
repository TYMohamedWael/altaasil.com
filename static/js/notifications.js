/**
 * notifications.js – Notification system for Littattafan Hausa
 */

(function () {
    'use strict';

    var notifDropdownOpen = false;

    window.toggleNotifications = function () {
        var dd = document.getElementById('notifDropdown');
        if (!dd) return;
        notifDropdownOpen = !notifDropdownOpen;
        dd.classList.toggle('open', notifDropdownOpen);
        if (notifDropdownOpen) window.fetchNotifications();
    };

    window.fetchNotifications = function () {
        fetch('/api/notifications/')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var list = document.getElementById('notifList');
                if (!list) return;
                var items = data.results || data.notifications || data || [];
                var unread = 0;
                if (!Array.isArray(items) || items.length === 0) {
                    list.innerHTML = '<div class="p-4 text-center text-xs text-gray-400">Babu sanarwa</div>';
                } else {
                    var html = '';
                    items.slice(0, 8).forEach(function (n) {
                        if (!n.is_read) unread++;
                        html += '<div class="p-3 hover:bg-cream/50 cursor-pointer transition-colors ' +
                            (n.is_read ? 'opacity-60' : '') +
                            '" onclick="markNotifRead(\'' + n.id + '\')">';
                        html += '<p class="text-sm text-gray-700">' + (n.message || n.title || '') + '</p>';
                        html += '<p class="text-[10px] text-gray-400 mt-1">' + (n.created_at_display || n.created_at || '') + '</p>';
                        html += '</div>';
                    });
                    list.innerHTML = html;
                }
                window.updateNotifBadge(typeof data.unread_count !== 'undefined' ? data.unread_count : unread);
            })
            .catch(function () {
                var list = document.getElementById('notifList');
                if (list) list.innerHTML = '<div class="p-4 text-center text-xs text-gray-400">Ba a iya loda sanarwa</div>';
            });
    };

    window.updateNotifBadge = function (count) {
        var badge = document.getElementById('notifBadge');
        var mobileBadge = document.getElementById('mobileNotifBadge');
        if (count > 0) {
            if (badge) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.classList.remove('hidden');
            }
            if (mobileBadge) {
                mobileBadge.textContent = count;
                mobileBadge.classList.remove('hidden');
            }
        } else {
            if (badge) badge.classList.add('hidden');
            if (mobileBadge) mobileBadge.classList.add('hidden');
        }
    };

    window.markNotifRead = function (id) {
        var csrfEl = document.querySelector('[name=csrfmiddlewaretoken]') ||
            document.querySelector('meta[name="csrf-token"]');
        var csrfToken = csrfEl ? (csrfEl.content || csrfEl.value) : '';
        fetch('/api/notifications/' + id + '/read/', {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken }
        }).then(function () {
            window.fetchNotifications();
        }).catch(function () { });
    };

    // Close dropdown on outside click
    document.addEventListener('click', function (e) {
        var wrapper = document.getElementById('notifWrapper');
        if (wrapper && !wrapper.contains(e.target) && notifDropdownOpen) {
            window.toggleNotifications();
        }
    });

    // Initial badge count fetch
    if (document.getElementById('notifBadge')) {
        window.fetchNotifications();
    }

})();
