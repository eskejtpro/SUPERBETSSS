# Wymagania

| ID | Wymaganie | Kryterium akceptacji |
| --- | --- | --- |
| R-01 | Tylko mecze e-piłki nożnej live | Lista ignoruje inne kategorie. |
| R-02 | Pełna lista meczów live | Każda rozpoznana pozycja widoczna w źródle tworzy wiersz. |
| R-03 | Dane meczu | Wiersz pokazuje ligę, format, zawodników, wynik, połowę, czas i status. |
| R-04 | Odświeżanie | Odczyt następuje co 20 sekund. |
| R-05 | Sortowanie | Najpierw mecze z najkrótszym szacowanym czasem do końca. |
| R-06 | Analiza | Program lokalnie opisuje wykryte zmiany wyniku, czasu i statusu. |
| R-07 | Historia | Migawki są trwale zapisywane lokalnie w SQLite. |
| R-08 | Bezpieczeństwo zakresu | Program nie wysyła zakładów ani nie odczytuje salda/konta. |
| R-09 | Lokalny panel WWW | Panel działa na `127.0.0.1` i pokazuje dane bez osobnego okna GUI. |
| R-10 | Funkcje panelu | Użytkownik może filtrować, sortować, przeglądać historię, eksportować dane i zapisywać ustawienia. |
