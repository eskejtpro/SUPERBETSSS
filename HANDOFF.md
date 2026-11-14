# Przekazanie projektu — Live FIFA Analyzer

Data stanu: 2026-11-14

## Cel

Lokalny panel WWW w Pythonie do obserwacji aktualnie rozgrywanych meczów e-piłki nożnej live. Program odczytuje wyłącznie widoczne dane z aktywnej karty Chrome przez dodatek MV3. Nie składa zakładów, nie tworzy kuponów, nie odczytuje salda i nie wykonuje działań finansowych.

## Uruchomienie

1. Otwórz Chrome i kartę Superbet: e-piłka nożna → live.
2. W `chrome://extensions` włącz Tryb programisty.
3. Wybierz „Wczytaj rozpakowane” i wskaż `A:\Projekt pc\chrome_bridge`.
4. Jeśli dodatek był już załadowany po zmianie kodu, kliknij jego przeładowanie i odśwież kartę Superbet.
5. Uruchom `python app.py` z katalogu `A:\Projekt pc` albo kliknij `Uruchom panel.bat`.
6. Panel jest dostępny pod `http://127.0.0.1:8765`.

Nie ma potrzeby instalowania FastAPI, Uvicorn ani innych pakietów. `requirements.txt` informuje o braku zewnętrznych zależności.

## Architektura

- `app.py` — lokalny serwer HTTP, API, walidacja migawek, SQLite, stan live, analiza zmian i ustawienia.
- `web/index.html` — struktura panelu.
- `web/styles.css` — wygląd panelu.
- `web/app.js` — pobieranie API, tabela/karty, filtry, sortowanie, szczegóły, historia i ustawienia.
- `chrome_bridge/manifest.json` — konfiguracja dodatku Chrome MV3.
- `chrome_bridge/content.js` — odczyt widocznych meczów z karty Superbet co 20 sekund.
- `chrome_bridge/background.js` — wysyłka migawek z service workera do localhost.
- `chrome_bridge/popup.*` — prosty status dodatku.
- `data/live_matches.sqlite3` — lokalna historia migawek.
- `data/settings.json` — ustawienia panelu, tworzone podczas zapisu.

Przepływ danych: Superbet w Chrome → content script → service worker → `POST /snapshot` → `LiveState` → SQLite/API → panel WWW.

## API

- `GET /api/live` — aktualne mecze i analiza zmian.
- `GET /api/health` — stan serwera, czas ostatniego sygnału i liczba meczów.
- `GET /api/history?match_key=...&limit=30` — historia wybranego meczu.
- `GET /api/settings` — ustawienia panelu.
- `PUT /api/settings` — zapis ustawień.
- `GET /api/export.json` — eksport aktualnego stanu JSON.
- `GET /api/export.csv` — eksport aktualnego stanu CSV.
- `POST /snapshot` — lokalny endpoint odbioru danych z dodatku.

Serwer nasłuchuje wyłącznie na `127.0.0.1:8765`.

## Zweryfikowane rezultaty

- składnia Python: PASS,
- składnia JavaScript dodatku i panelu: PASS,
- lokalny most HTTP/CORS/PNA: PASS,
- `GET /`: HTTP 200,
- `GET /api/live`: PASS,
- odebrano 6 rzeczywistych meczów live,
- zapis SQLite i historia: PASS,
- `GET/PUT /api/settings`: PASS.

## Ograniczenia i ryzyka

- Dodatek wymaga otwartej karty Superbet; po zamknięciu lub zmianie układu strony dane przestaną napływać.
- Parser zależy od widocznego DOM strony i może wymagać aktualizacji po zmianie strony źródłowej.
- Automatyczna analiza jest obecnie regułowa i lokalna. Zewnętrzny model AI nie jest jeszcze podłączony.
- Brak potwierdzenia instalatora Windows, długiego testu stabilności ani testu na wielu rozdzielczościach.
- Nie dodawać kluczy API, haseł ani danych konta do repozytorium, SQLite, dodatku ani logów.

## Następne zadania

1. Obserwować kilka kolejnych cykli 20-sekundowych i sprawdzić zmianę wyników/połów.
2. Dopracować parser po zmianach layoutu Superbet.
3. Dodać testy jednostkowe normalizacji i sortowania.
4. Ustalić dostawcę AI i sposób przechowywania klucza przed integracją modelu.
5. Przygotować opcjonalny pakiet Windows po osobnej weryfikacji.

## Bezpieczne zatrzymanie

Zamknij proces `python app.py` lub użyj `Ctrl+C` w konsoli. Dane historyczne w `data/live_matches.sqlite3` pozostają lokalnie.
