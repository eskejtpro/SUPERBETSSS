# Testowanie

| Kontrola | Status | Wynik |
| --- | --- | --- |
| Sprawdzenie składni Python | PASS | `compile(app.py)` — 2026-11-14 |
| Uruchomienie GUI | PASS | Poprawiona wersja uruchomiona 2026-11-14; okno `Live FIFA Analyzer` odpowiada. |
| Sprawdzenie JavaScript dodatku | PASS | `node --check chrome_bridge/content.js` i `popup.js`. |
| Lokalny most CORS | PASS | `OPTIONS /snapshot` zwrócił 204 oraz metody `POST, OPTIONS`. |
| Endpoint zdrowia lokalnego mostu | PASS | `GET /health` zwrócił `{"ok": true, "received_at": null}`. |
| Lokalny panel WWW | PASS | `GET /` zwrócił HTTP 200. |
| API live | PASS | `GET /api/live` zwrócił 6 rzeczywistych meczów. |
| API ustawień | PASS | `PUT` i następujący `GET /api/settings` zwróciły zapisane wartości. |
| Zasoby panelu | PASS | `GET /styles.css` i `GET /app.js` zwróciły HTTP 200. |
| Historia meczu | PASS | `GET /api/history` dla odebranego meczu zwrócił 10 migawek. |
| Odczyt strony live | PASS | 2026-11-14: odebrano 6 rzeczywistych meczów e-piłki z aktywnej karty Chrome. |
| Dane meczu | PASS | Potwierdzono nazwy graczy, wynik, połowę, czas oraz format `2 × 4 min`. |
| Sortowanie | PASS | Dane mają obliczalny czas pozostały dla formatu `2 × 4 min`; lista korzysta z tego klucza. |

Testy są prowadzone po uruchomieniu aplikacji na stronie źródłowej.
