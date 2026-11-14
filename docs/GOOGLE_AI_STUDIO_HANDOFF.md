# Dokumentacja przekazania projektu do Google AI Studio

> Dokument opisuje stan repozytorium `eskejtpro/SUPERBETSSS` na gałęzi `main`. To dokumentacja istniejącej implementacji, a nie deklaracja, że wszystkie integracje zostały przetestowane na koncie użytkownika.

## 1. Cel produktu

SUPERBETSSS LIVE Monitor to lokalna aplikacja do obserwacji aktualnie widocznych meczów e-piłki nożnej LIVE na stronie Superbet. Aplikacja:
- odczytuje widoczne dane meczów z aktualnie otwartej strony Superbet przez rozszerzenie Chrome,
- przesyła migawkę do lokalnego serwera Python,
- prezentuje wykryte mecze w panelu WWW,
- sortuje spotkania według szacowanego czasu pozostałego do końca,
- wyróżnia nazwę drużyny prowadzącej, gdy przewaga i czas do końca spełniają ustawione warunki,
- zapisuje lokalną historię odczytów w SQLite.

Aplikacja jest obserwacyjna. Nie składa zakładów, nie tworzy kuponów, nie wykonuje transakcji i nie potrzebuje danych logowania do konta Superbet. Logowanie oraz interakcje ze stroną wykonuje użytkownik w swojej przeglądarce.

## 2. Stos technologiczny i uruchamianie

- Backend: Python 3.12+ (standardowa biblioteka, bez wymaganych zewnętrznych pakietów).
- Serwer HTTP: `http.server.ThreadingHTTPServer`.
- Baza danych: SQLite przez `sqlite3`.
- Frontend: HTML, CSS i JavaScript bez frameworka.
- Integracja z serwisem: rozszerzenie Chrome Manifest V3 w katalogu `chrome_bridge/`.
- Lokalny adres: `http://127.0.0.1:8765`.
- Start: `python app.py` lub plik `Uruchom panel.bat`.

Aplikacja nasłuchuje wyłącznie na `127.0.0.1`, a nie na publicznym interfejsie sieciowym. Nie zakładaj, że backend jest wdrożony do chmury.

## 3. Struktura repozytorium

| Ścieżka | Rola |
|---|---|
| `app.py` | Serwer HTTP, normalizacja danych, wyliczanie czasu do końca, stan LIVE, SQLite, ustawienia i API |
| `web/index.html` | Struktura panelu, tabela/karty, szczegóły meczu, okno ustawień |
| `web/app.js` | Pobieranie danych API, renderowanie, filtrowanie, sortowanie, podświetlanie, ustawienia i polling |
| `web/styles.css` | Wygląd panelu, responsywność, motyw i klasy wyróżnień |
| `chrome_bridge/manifest.json` | Konfiguracja rozszerzenia Chrome MV3 |
| `chrome_bridge/content.js` | Odczyt widocznych elementów strony Superbet i publikacja migawki co 20 s |
| `chrome_bridge/background.js` | Przekazanie migawki do lokalnego endpointu `/snapshot` |
| `chrome_bridge/popup.html`, `popup.js` | Popup rozszerzenia i stan połączenia (jeśli występuje w aktualnej wersji) |
| `tests/` | Testy jednostkowe logiki backendu |
| `SETUP.md` | Instrukcja konfiguracji środowiska |
| `README.md` | Skrócony opis projektu i zakres funkcji |

Dane robocze tworzone są lokalnie w katalogu `data/`: `live_matches.sqlite3` i `settings.json`. Nie należy umieszczać danych użytkownika ani bazy runtime w repozytorium.

## 4. Przepływ danych

1. Użytkownik otwiera stronę Superbet e-piłka nożna LIVE w Chrome.
2. Skrypt content script rozszerzenia analizuje elementy DOM, przede wszystkim linki pasujące do selektora `a[href*="/kursy/e-pilka-nozna/"]`.
3. Rozpoznaje nazwy uczestników, wynik, połowę, zegar, status, kontekst ligi/formatu i adres meczu.
4. Co 20 sekund rozszerzenie wysyła komunikat `live-fifa-snapshot` do service workera.
5. `background.js` wysyła JSON przez HTTP POST do `http://127.0.0.1:8765/snapshot`.
6. Backend waliduje i normalizuje rekordy, aktualizuje bieżący stan i zapisuje migawkę w SQLite.
7. Frontend odpytuje `GET /api/live` i odświeża panel co 20 sekund.

Schemat poglądowy:

```text
Superbet DOM (Chrome)
        |
        v
chrome_bridge/content.js
        |  runtime message co 20 s
        v
chrome_bridge/background.js
        |  POST http://127.0.0.1:8765/snapshot
        v
app.py -> walidacja / normalizacja -> LiveState
                         |                |
                         v                v
                       SQLite         GET /api/live
                                          |
                                          v
                                    web/app.js
                                          |
                                          v
                                    panel WWW
```

## 5. Kontrakt danych

### 5.1 Migawka wysyłana przez rozszerzenie

Endpoint: `POST /snapshot`, nagłówek `Content-Type: application/json`.

Przykładowe wejście (wartości demonstracyjne):

```json
{
  "matches": [
    {
      "url": "https://superbet.pl/zaklady-bukmacherskie/e-pilka-nozna/live/example",
      "home": "Gracz A",
      "away": "Gracz B",
      "homeScore": 3,
      "awayScore": 1,
      "half": 2,
      "clock": 540,
      "clockLabel": "9'",
      "formatMinutes": 20,
      "competition": "e-Piłka nożna live",
      "status": "aktywny",
      "isLive": true
    }
  ]
}
```

Backend akceptuje wyłącznie rekordy z niepustymi nazwami obu drużyn oraz potwierdzoną połową 1/2 i nieujemnym czasem zegara. Rekordy niepoprawne są pomijane. Pole `isLive` z wejścia nie jest podstawą walidacji; backend sam ustawia `is_live: true` dla znormalizowanych rekordów.

### 5.2 Znormalizowany rekord

Kluczowe pola API `/api/live`:
- `key`: klucz meczu oparty na URL i nazwach uczestników,
- `competition`, `home`, `away`,
- `home_score`, `away_score`, `score_label`,
- `half`, `half_label`, `clock_seconds`, `clock_label`,
- `format_minutes`, `remaining_seconds`,
- `status`, `is_live`, `source_url`, `observed_at`,
- `analysis`: tekstowy opis nowego meczu lub zmian od poprzedniej migawki.

### 5.3 API backendu

| Metoda | Ścieżka | Działanie |
|---|---|---|
| POST | `/snapshot` | Odbiera migawkę z rozszerzenia; zwraca liczbę zaakceptowanych rekordów |
| GET | `/api/live` | Aktualne mecze i stan świeżości źródła |
| GET | `/api/health` | Podstawowy status backendu i liczba aktualnych meczów |
| GET | `/api/settings` | Odczyt ustawień |
| PUT | `/api/settings` | Zapis dozwolonych ustawień |
| GET | `/api/history?match_key=...&limit=30` | Historia meczu; limit backendu 1–100 |
| GET | `/api/export.json` | Eksport aktualnego payloadu JSON |
| GET | `/api/export.csv` | Eksport aktualnych meczów CSV |
| GET | inne ścieżki | Statyczne pliki z katalogu `web/` |

`/api/live` zwraca między innymi `matches`, `count`, `source_count`, `received_at`, `source_age_seconds`, `source_online`, `source_status` i `source_interval_seconds`. Źródło uznawane jest za aktualne, jeśli ostatnia migawka ma maksymalnie 50 sekund. Gdy sygnał jest nieaktualny, backend zwraca pustą listę aktualnych meczów.

## 6. Obliczanie czasu do końca i sortowanie

Backend wymaga dodatniego, parzystego `format_minutes`, połowy 1 lub 2 i zegara nieprzekraczającego długości połowy. Dla formatu 2 × N minut:
- długość połowy = N × 60 sekund,
- w pierwszej połowie: pozostały czas = reszta bieżącej połowy + cała druga połowa,
- w drugiej połowie: pozostały czas = reszta drugiej połowy.

Jeżeli format lub zegar nie pozwalają wiarygodnie policzyć czasu, `remaining_seconds` ma wartość `null`. Takie mecze są sortowane za meczami z wyliczonym czasem. Frontend sortuje rosnąco po czasie pozostałym, a następnie alfabetycznie.

Nie przedstawiaj wyliczonego czasu jako oficjalnego zegara Superbet. To estymacja na podstawie rozpoznanego formatu, połowy i zegara.

## 7. Reguła wyróżniania lidera

Implementacja w `web/app.js` funkcji `highlightInfo(match)`:
- ustawienie `highlight_enabled` musi być aktywne,
- `remaining_seconds` musi być znane, nieujemne i nie większe niż `highlight_remaining_seconds`,
- oba wyniki muszą być liczbami całkowitymi,
- wynik nie może być remisowy,
- bezwzględna różnica goli musi być co najmniej równa `highlight_goal_difference`.

Domyślnie: `highlight_enabled=true`, `highlight_goal_difference=3`, `highlight_remaining_seconds=90`. Zakresy walidowane przez backend: przewaga 1–10 goli, okno 15–600 sekund. Podświetlana jest nazwa prowadzącej drużyny; dodatkowo pokazywany jest komunikat o przewadze. Jest to wyłącznie reguła prezentacji, nie rekomendacja ani prognoza.

## 8. Ustawienia

Domyślne ustawienia backendu:
- `ui_refresh_seconds: 20` (backend wymusza 20),
- `theme: "dark"`,
- `default_sort: "remaining"`,
- `compact_mode: false`,
- `show_paused: true`,
- `highlight_enabled: true`,
- `highlight_goal_difference: 3`,
- `highlight_remaining_seconds: 90`.

Ustawienia są przechowywane w `data/settings.json`. Backend ignoruje nieznane klucze i odrzuca wartości poza dozwolonymi zakresami. Frontend ma widok tabeli i kart, wyszukiwanie, filtr połowy i statusu, szczegóły wybranego meczu oraz historię.

## 9. Ograniczenia i ryzyka, których nie wolno ukrywać

1. Rozszerzenie czyta wyłącznie elementy obecne w aktualnie załadowanym DOM. Nie gwarantuje wykrycia wszystkich meczów dostępnych na serwerach Superbet.
2. Dalsze mecze mogą wymagać przewinięcia, zmiany zakładki lub doładowania strony.
3. Selektory DOM i heurystyki parsowania są zależne od aktualnego HTML Superbet i mogą przestać działać po zmianie serwisu.
4. Rozpoznawanie nazw, wyniku, formatu, połowy i zegara wymaga testu na rzeczywistej stronie w Chrome. Nie deklaruj pełnej poprawności bez takiej walidacji.
5. Jeśli format meczu nie zostanie rozpoznany, czasu do końca nie da się policzyć i mecz trafi niżej na liście.
6. Backend lokalny musi działać na komputerze użytkownika. Sam frontend hostowany statycznie, np. w GitHub Pages, nie uruchomi Pythona ani nie odbierze lokalnej migawki.
7. Rozszerzenie komunikuje się z adresem loopback `127.0.0.1:8765`. Każda zmiana hosta lub portu wymaga zsynchronizowania konfiguracji rozszerzenia i backendu.
8. Nie dodawaj automatycznego logowania, obchodzenia zabezpieczeń, automatycznego klikania zakładów ani wykonywania transakcji.
9. Nie zapisuj w repozytorium ciasteczek, tokenów, haseł, danych konta, prywatnych zrzutów ekranu ani bazy użytkownika.

## 10. Testy

Testy znajdują się w `tests/`. Uruchomienie:
```bash
python -m unittest discover -s tests -v
```

Aktualne pliki testów obejmują:
- `test_highlight_settings.py`: domyślne ustawienia, personalizacja i walidacja progów,
- `test_live_filter.py`: akceptowanie rekordów LIVE i odrzucanie rekordów bez połowy/zegara,
- `test_match_sorting.py`: obliczanie czasu i kolejność sortowania.

Testy jednostkowe backendu nie potwierdzają poprawności selektorów DOM na aktualnej stronie Superbet. To osobny test integracyjny wymagający Chrome i rzeczywistej strony.

## 11. Instrukcje dla Google AI Studio

Przed zmianami:
1. Przeanalizuj repozytorium i przeczytaj tę dokumentację oraz `README.md` i `SETUP.md`.
2. Obejrzyj faktyczną zawartość plików; nie zakładaj, że dokumentacja zastępuje kod.
3. Ustal, czy zadanie dotyczy tylko wyglądu, frontendu, backendu, rozszerzenia Chrome czy całego przepływu.
4. Zachowaj zgodność kontraktu API i istniejących funkcji, chyba że użytkownik wyraźnie zleci zmianę.
5. Nie przepisuj całego projektu bez potrzeby. Wprowadzaj małe, odwracalne zmiany.
6. Nie wstawiaj przykładowych meczów jako prawdziwych danych LIVE. Dane demonstracyjne muszą być jawnie oznaczone jako DEMO.
7. Po zmianach uruchom testy jednostkowe i zgłoś dokładnie, co przeszło, a czego nie dało się sprawdzić.
8. Jeśli zmieniasz parser DOM, opisz selektory i heurystyki oraz poproś o test na stronie Superbet w Chrome.
9. Nie wymyślaj endpointów, pól danych ani funkcji, których nie ma w kodzie. Jeśli proponujesz nową funkcję, oddziel ją od opisu istniejącego stanu.
10. Nie umieszczaj sekretów ani kluczy API w kodzie frontendowym, repozytorium ani historii Git.

## 12. Definicja ukończenia zadania

Każda zmiana powinna zawierać:
- listę zmienionych plików i uzasadnienie,
- informację, czy zmieniono API lub schemat danych,
- wynik testów z komendą,
- znane ograniczenia i kroki wymagające ręcznego testu,
- potwierdzenie, że istniejące lokalne uruchamianie nadal jest obsługiwane.

## 13. Przydatne odnośniki

- Repozytorium: https://github.com/eskejtpro/SUPERBETSSS
- Instrukcja instalacji: [SETUP.md](../SETUP.md)
- Opis projektu: [README.md](../README.md)
- Główny backend: [app.py](../app.py)
