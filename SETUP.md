# Przygotowanie środowiska

1. Użyj Python 3.12 lub nowszego. Program korzysta wyłącznie ze standardowej biblioteki Pythona.
2. W Chrome otwórz `chrome://extensions`.
3. Włącz Tryb programisty, wybierz „Wczytaj rozpakowane” i wskaż folder `chrome_bridge` z projektu.
4. Otwórz kartę Superbet e-piłka nożna live. Logowanie, zgody i każdą interakcję z witryną wykonuje użytkownik.
5. Uruchom `python app.py`.
6. Otwórz `http://127.0.0.1:8765`, jeśli przeglądarka nie otworzy panelu automatycznie.

Dodatek odczytuje tylko widoczne dane meczów e-piłki nożnej co 20 sekund. Panel WWW może odświeżać swój widok co 3, 5, 10 lub 20 sekund.
