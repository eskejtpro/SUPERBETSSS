# Przygotowanie środowiska

1. Użyj Python 3.12 lub nowszego. Program korzysta wyłącznie ze standardowej biblioteki Pythona.
2. W Chrome otwórz `chrome://extensions`.
3. Włącz Tryb programisty, wybierz „Wczytaj rozpakowane” i wskaż folder `chrome_bridge`.
4. Otwórz stronę Superbet e-piłka nożna LIVE. Logowanie i interakcje z witryną wykonujesz samodzielnie.
5. Uruchom `python app.py` albo `Uruchom panel.bat`.
6. Panel otworzy się pod `http://127.0.0.1:8765`.

Rozszerzenie odczytuje wyłącznie dane widoczne w aktualnie załadowanym DOM. Panel odświeża dane co 20 sekund. W wersji użytkowej nie ma fikcyjnych meczów ani testowych alertów.
