const CACHE_NAME = 'temiryol-v3'; // Kesh versiyasini yangiladik

// Keshlanishi kerak bo'lgan asosiy resurslar
const ASSETS_TO_CACHE = [
    '/',                       // Login sahifasi
    '/second/',              // Asosiy menyu
    '/bosspage/',              // Boss sahifasi
    '/static/icons/image.png', // PWA ikonka
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
];

// 1. Install - Service Worker o'rnatilmoqda va fayllar keshlanmoqda
self.addEventListener('install', (event) => {
    console.log("SW: O'rnatilmoqda...");
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log("SW: Resurslar keshga saqlanmoqda");
            // addAll bitta faylda xato bo'lsa hammasini to'xtatadi,
            // shuning uchun ehtiyotkorlik bilan ishlatamiz
            return cache.addAll(ASSETS_TO_CACHE).catch(err => {
                console.error("SW: Keshga yuklashda xatolik:", err);
            });
        })
    );
    self.skipWaiting();
});

// 2. Activate - Eski kesh versiyalarini tozalash
self.addEventListener('activate', (event) => {
    console.log("SW: Faollashdi");
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cache) => {
                    if (cache !== CACHE_NAME) {
                        console.log("SW: Eski kesh tozalandi:", cache);
                        return caches.delete(cache);
                    }
                })
            );
        })
    );
    return self.clients.claim();
});

// 3. Fetch - So'rovlarni boshqarish
self.addEventListener('fetch', (event) => {
    // POST so'rovlarini (masalan, login qilish yoki ma'lumot yuborish) keshlamaymiz
    if (event.request.method !== 'GET') return;

    // Statik fayllar (rasmlar, CSS) uchun "Cache-first"
    // Sahifalar (HTML) uchun "Network-first" (yangiliklarni ko'rish uchun)
    event.respondWith(
        fetch(event.request)
            .then((response) => {
                // Agar tarmoqdan javob kelsa, uni keshga ham saqlab qo'yamiz (ixtiyoriy)
                if (response && response.status === 200) {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseClone);
                    });
                }
                return response;
            })
            .catch(() => {
                // Agar internet bo'lmasa, keshdan qidiramiz
                return caches.match(event.request).then((cachedResponse) => {
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    // Agar keshda ham bo'lmasa va bu HTML sahifa bo'lsa (oflayn xabar o'rniga)
                    console.log("Resurs na internetda, na keshda bor.");
                });
            })
    );
});
