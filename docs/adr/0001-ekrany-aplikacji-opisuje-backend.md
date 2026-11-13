# Ekrany aplikacji opisuje backend

Kodu telewizora (`tv/`) po pierwszym wdrożeniu nie da się już zaktualizować, a 10 000 telewizorów ma dalej dostawać zmiany w aplikacjach. Dlatego telewizor nie zna żadnej konkretnej aplikacji: umie tylko narysować ekran opisany przez backend w JSON-ie z zamkniętego słownika ogólnych bloków (układ wiersz/kolumna, tekst, obraz z zapasowym kolorem, kafelek, siatka kafelków w N kolumnach, przewijana lista, przycisk) i wykonać akcje z zamkniętego słownika (przejdź do ekranu, odtwórz strumień, pauza/wznów, głośność, wstecz). Music Box jest pierwszą aplikacją zbudowaną w ten sposób; aplikacje bez własnego ekranu dostają od backendu ekran z samą nazwą, jak dotąd.

## Considered Options

- **Stały ekran radia w `tv/`**: najmniej kodu, ale układ zamrożony na zawsze.
- **Gotowe bloki radiowe** ("siatka stacji", "odtwarzacz z listą"): zmiany tylko w granicach ich parametrów.
- **Kod aplikacji (HTML/JS) z backendu**: pełna swoboda, ale backend de facto wdraża kod telewizora i jego błąd psuje ekran.

## Consequences

- Słownik bloków i akcji jest kontraktem na całe życie telewizora: nowej akcji (np. nagrywania) nie da się dodać później. Lepiej teraz dołożyć ogólną akcję niż jej zabraknąć.
- Telewizor nie liczy nic po swojej stronie: np. "następna stacja" to przycisk z akcją "przejdź do ekranu", której cel wylicza backend.
- "Przejdź do ekranu" może zastąpić bieżący ekran zamiast odłożyć go na stos (`replace`), żeby przełączanie stacji w odtwarzaczu nie wydłużało drogi powrotu: BACK zawsze wraca do siatki stacji.
- Strumień do grania jest polem opisu ekranu (`stream`): telewizor gra go, chyba że gra już ten sam adres, więc odświeżenie ekranu nie przerywa dźwięku.
