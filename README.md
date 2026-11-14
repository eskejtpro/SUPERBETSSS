# SUPERBETSSS LIVE Monitor

Lokalny, obserwacyjny panel WWW do monitorowania widocznych meczów e-piłki nożnej na Superbet. Nie składa zakładów, nie tworzy kuponów i nie wykonuje transakcji.

Uruchomienie: `python app.py` lub `Uruchom panel.bat`. Panel działa lokalnie pod `http://127.0.0.1:8765`. Historia meczów jest zapisywana w SQLite, a ustawienia w `data/settings.json`.

## Funkcje
- Odczyt meczów z aktualnie załadowanego DOM Superbet przez rozszerzenie Chrome.
- Ręczne skanowanie całej strony e-piłki LIVE: rozszerzenie przewija listę, doładowuje kolejne sekcje i zbiera wykryte spotkania.
- Filtr „Wszystkie rozgrywki LIVE” oraz wybór konkretnej ligi/turnieju; licznik wykrytych rozgrywek.
- Losowe odświeżanie danych co 18–28 sekund i sortowanie według szacowanego czasu do końca.
- Cztery reguły podświetlania: potwierdzona przewaga, potencjalna przewaga, wysokie tempo bramkowe i wyrównana końcówka.
- Konfigurowalne progi i kolory, powiadomienia przeglądarkowe, sygnał dźwiękowy i historia alertów w bieżącej sesji.
- Historia odczytów meczów w lokalnej bazie SQLite oraz eksport JSON/CSV.
- Trwałe archiwum spotkań, w których drużyna osiągnęła przewagę co najmniej 3 goli (konfigurowalny próg 3–10), z wynikiem, liderem, największą przewagą, ligą i czasem wykrycia.
- Ustawienie włączania/wyłączania archiwizacji oraz limit 25–500 wpisów; wyczyszczenie archiwum wymaga osobnego potwierdzenia.

## Ograniczenia
Rozszerzenie odczytuje tylko mecze obecne w aktualnie załadowanym DOM strony Superbet; nie gwarantuje wykrycia spotkań, których strona jeszcze nie załadowała. Doliczony czas i przerwy są uwzględniane wyłącznie, gdy źródło dostarczy odpowiednie dane. Prognoza tempa jest estymacją na podstawie dotychczasowego wyniku i czasu, a nie gwarancją rezultatu.

## Testy developerskie
`python -m unittest discover -s tests -v`
