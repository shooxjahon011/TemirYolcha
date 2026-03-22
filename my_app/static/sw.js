// Kesh nomi va saqlanishi kerak bo'lgan resurslar ro'yxati
const CACHE_NAME = 'temiryol-v1';
const ASSETS_TO_CACHE = [
    '/',
    '/static/icons/image.png',
    // Agar boshqa muhim rasm yoki CSS/JS fayllar bo'lsa, bu yerga qo'shing
];

// 1. Install - Service Worker o'rnatilmoqda
self.addEventListener('install', (event) => {
    console.log("Service Worker: O'rnatilmoqda...");
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log("Service Worker: Fayllar keshga saqlanmoqda");
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
    self.skipWaiting();
});

// 2. Activate - Eski keshni tozalash
self.addEventListener('activate', (event) => {
    console.log("Service Worker: Faollashdi");
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cache) => {
                    if (cache !== CACHE_NAME) {
                        console.log("Service Worker: Eski kesh tozalanmoqda");
                        return caches.delete(cache);
                    }
                })
            );
        })
    );
    return self.clients.claim();
});

// 3. Fetch - Tarmoq so'rovlarini boshqarish (Oflayn ishlash uchun)
self.addEventListener('fetch', (event) => {
    // Faqat GET so'rovlarini keshdan qidiramiz (POST so'rovlari GPS uchun, ularni keshlab bo'lmaydi)
    if (event.request.method !== 'GET') return;

    event.respondWith(
        caches.match(event.request).then((response) => {
            // Agar keshda bo'lsa keshdan beramiz, aks holda tarmoqqa so'rov yuboramiz
            return response || fetch(event.request).catch(() => {
                // Agar tarmoq ham, kesh ham bo'lmasa (masalan, oflayn rejimda)
                console.log("Internet aloqasi yo'q");
            });
        })
    );
});