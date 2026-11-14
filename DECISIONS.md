# Decyzje

## D-01: źródło danych

Używamy wbudowanej, stale otwartej karty źródłowej i wyłącznie odczytu jej widocznego DOM. Powód: brak potwierdzonego oficjalnego API dla tego zakresu.

## D-02: okres odświeżania

20 sekund, zgodnie z wymaganiem użytkownika.

## D-03: lokalny most danych

Most działa wyłącznie na `127.0.0.1` i nie wymaga tokenu. Przenosi wyłącznie dane widocznych meczów; nie przesyła ich poza komputer.

## D-04: ograniczenie działania

Aplikacja jest obserwacyjna. Nie klika kursów, nie buduje kuponów, nie pobiera salda i nie realizuje płatności.
