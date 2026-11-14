# Architektura

`app.py` uruchamia lokalny serwer HTTP na `127.0.0.1:8765`. Dodatek Chrome `chrome_bridge` zbiera wyłącznie widoczne wiersze e-piłki z karty użytkownika. Skrypt strony przekazuje je do service workera dodatku, a ten wysyła je do endpointu `POST /snapshot`. `MatchDatabase` zapisuje migawki do SQLite, `LiveState` utrzymuje aktualną listę i automatyczną analizę zmian, a katalog `web/` zawiera panel WWW.

Endpointy: `GET /api/live`, `GET /api/history`, `GET/PUT /api/settings`, `GET /api/health`, `GET /api/export.json`, `GET /api/export.csv` oraz `POST /snapshot`.

Przepływ: strona Chrome otwarta przez użytkownika → odczyt DOM co 20 s przez dodatek → service worker Chrome → localhost → walidacja → SQLite → API → panel WWW.
