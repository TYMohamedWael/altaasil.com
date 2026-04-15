const CACHE_NAME = 'hausa-books-v1';
const STATIC_CACHE = 'hausa-books-static-v1';
const PDF_CACHE = 'hausa-books-pdf-v1';

const STATIC_ASSETS = [
    '/',
    '/static/manifest.json',
    'https://cdn.tailwindcss.com',
];

// Install - cache static assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

// Activate - clean old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => 
            Promise.all(keys.filter(k => !k.startsWith('hausa-books-')).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

// Fetch - smart caching strategies
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    
    // Static assets: cache-first
    if (url.pathname.startsWith('/static/') || url.hostname === 'cdn.tailwindcss.com' || url.hostname === 'fonts.googleapis.com') {
        event.respondWith(
            caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
                const clone = response.clone();
                caches.open(STATIC_CACHE).then(cache => cache.put(event.request, clone));
                return response;
            }))
        );
        return;
    }
    
    // PDF files: cache when opened
    if (url.pathname.includes('/media/books/')) {
        event.respondWith(
            caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
                const clone = response.clone();
                caches.open(PDF_CACHE).then(cache => cache.put(event.request, clone));
                return response;
            }))
        );
        return;
    }
    
    // HTML pages: network-first with offline fallback
    if (event.request.headers.get('accept')?.includes('text/html')) {
        event.respondWith(
            fetch(event.request).then(response => {
                const clone = response.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                return response;
            }).catch(() => caches.match(event.request).then(cached => cached || caches.match('/offline/')))
        );
        return;
    }
    
    // API: stale-while-revalidate
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            caches.match(event.request).then(cached => {
                const fetchPromise = fetch(event.request).then(response => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                    return response;
                });
                return cached || fetchPromise;
            })
        );
        return;
    }
    
    // Default: network first
    event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});
