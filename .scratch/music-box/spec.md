# Music Box: polskie radio online

**Status:** ready-for-agent

## Problem Statement

Użytkownik telewizora Lumio otwiera aplikację **Music Box** i widzi tylko jej nazwę. Nie da się niczego posłuchać. Do tego kod telewizora po pierwszym wdrożeniu jest zamrożony, więc każdą przyszłą poprawkę Music Box (i każdej innej aplikacji) trzeba będzie zrobić wyłącznie po stronie backendu, a obecny telewizor nie ma jak przyjąć od backendu niczego poza listą aplikacji.

## Solution

Po otwarciu Music Box telewizor pokazuje **siatkę stacji**: 20 najpopularniejszych działających polskich stacji radiowych jako kafelki z logo i nazwą. Wybranie stacji otwiera **odtwarzacz**: stacja gra, po lewej jest jej nazwa i logo z przyciskami (poprzednia/następna, play/pauza, głośność, powrót), po prawej lista pozostałych stacji. Stacje pochodzą z otwartego serwisu Radio Browser, bez klucza API.

Telewizor nie wie nic o radiu. Każdy **ekran aplikacji** opisuje backend w JSON-ie z zamkniętego słownika **bloków** i **akcji** (ADR 0001), a telewizor tylko go rysuje i wykonuje akcje. Dzięki temu zmiany układu, tekstów czy logiki Music Box po wdrożeniu robi się na backendzie.

## User Stories

1. Jako widz chcę po otwarciu Music Box zobaczyć kafelki ze stacjami, żeby wybrać, czego posłuchać.
2. Jako widz chcę widzieć na kafelku logo i nazwę stacji, żeby szybko rozpoznać stację.
3. Jako widz chcę, żeby stacja bez logo (albo z logo, które się nie ładuje) miała kolorowy kafelek z nazwą, żeby siatka nie miała dziur.
4. Jako widz chcę, żeby kolor kafelka bez logo był zawsze ten sam dla danej stacji, żeby siatka nie migała przy odświeżeniu.
5. Jako widz chcę poruszać się po siatce strzałkami pilota, tak jak po menu aplikacji, żeby nie uczyć się nowej obsługi.
6. Jako widz chcę, żeby OK na kafelku uruchamiało stację, żeby jednym przyciskiem zacząć słuchać.
7. Jako widz chcę, żeby po wybraniu stacji dźwięk zaczął grać od razu, bez dodatkowego potwierdzenia.
8. Jako widz chcę w odtwarzaczu widzieć nazwę i logo grającej stacji, żeby wiedzieć, czego słucham.
9. Jako widz chcę po prawej stronie odtwarzacza listę pozostałych stacji, żeby przełączyć się bez wracania do siatki.
10. Jako widz chcę wybrać stację z listy po prawej strzałkami i OK, żeby przełączyć się na nią.
11. Jako widz chcę przyciski „poprzednia” i „następna stacja”, żeby przechodzić po kolei po liście.
12. Jako widz chcę, żeby CH+ i CH− w odtwarzaczu przełączały na następną i poprzednią stację, żeby przełączać jak w telewizji.
13. Jako widz chcę przycisk play/pauza, żeby wyciszyć radio bez wychodzenia z odtwarzacza.
14. Jako widz chcę przyciski głośności +/−, żeby ustawić głośność radia, bo pilot nie ma przycisków głośności.
15. Jako widz chcę widoczny przycisk „wróć do stacji”, który robi to samo co BACK, żeby było jasne, jak wyjść.
16. Jako widz chcę, żeby BACK w odtwarzaczu wracał do siatki stacji, a HOME do menu telewizora.
17. Jako widz chcę, żeby po wejściu do odtwarzacza fokus był na play/pauza, żeby OK od razu pauzowało.
18. Jako widz chcę zobaczyć komunikat, gdy stacja nie nadaje, zamiast ciszy bez wyjaśnienia.
19. Jako widz chcę, żeby co minutę odświeżała się lista stacji, ale żeby grająca stacja nie przerywała.
20. Jako widz chcę, żeby grająca stacja grała dalej, nawet gdy wypadnie z listy przy odświeżeniu.
21. Jako widz w dowolnym regionie (NA, EU, APAC) chcę dostać tę samą listę polskich stacji.
22. Jako widz chcę, żeby Music Box działał, nawet gdy Radio Browser chwilowo nie odpowiada, żeby awaria cudzego serwisu nie psuła mi radia.
23. Jako widz chcę, żeby Music Box miał stacje także po restarcie backendu w czasie awarii Radio Browser.
24. Jako widz chcę, żeby pozostałe aplikacje po otwarciu wyglądały tak jak dotąd (nazwa aplikacji), żeby zmiana nic im nie zepsuła.
25. Jako operator backendu chcę, żeby 10 000 telewizorów odświeżających co minutę nie generowało ruchu do Radio Browser, żeby nas nie zablokowano.
26. Jako operator chcę, żeby backend nie przesyłał dźwięku, żeby nie płacić za transfer ok. 1,3 Gb/s.
27. Jako operator chcę zmieniać liczbę stacji, kryteria wyboru i częstotliwość odświeżania na backendzie, bez dotykania telewizora.
28. Jako operator chcę zmieniać układ ekranów Music Box (np. przenieść listę na lewo, dodać opis) bez dotykania telewizora.
29. Jako operator chcę zmieniać, co ile minut telewizor odświeża ekran, z poziomu backendu.
30. Jako operator chcę, żeby backend przełączał się na inny serwer Radio Browser, gdy jeden nie odpowiada.
31. Jako operator chcę, żeby backend przedstawiał się Radio Browser ogólną nazwą klienta, bez danych użytkowników.
32. Jako programista innej aplikacji chcę zbudować jej ekran z tych samych bloków, żeby kolejne aplikacje też dało się zmieniać po zamrożeniu telewizora.
33. Jako programista chcę testować ekrany przez API bez sieci, żeby testy były szybkie i powtarzalne.

## Implementation Decisions

**Ekran aplikacji opisany przez backend (ADR 0001)**
- Nowy endpoint dla każdej aplikacji: `GET /api/devices/<device_id>/apps/<app_id>/screen`, z opcjonalnym parametrem `station=<stationuuid>` (ogólnie: parametry ekranu przekazywane w query). Zwraca opis ekranu: drzewo bloków, czas odświeżenia w sekundach (domyślnie 60) i ewentualny strumień do grania.
- 404 dla nieznanego urządzenia (istniejące `device_not_found`) i dla aplikacji, której urządzenie nie widzi w katalogu.
- Aplikacja bez własnego ekranu dostaje ekran domyślny: sam tekst z nazwą aplikacji, czyli dzisiejsze zachowanie.
- Słownik bloków (zamknięty po pierwszym wdrożeniu `tv/`): układ (wiersz/kolumna z proporcjami dzieci), tekst, obraz (z adresem i zapasowym kolorem + tekstem, gdy brak lub błąd ładowania), kafelek (obraz/kolor + podpis, fokusowalny, z akcją), przewijana lista (fokusowalne pozycje z akcjami), przycisk (etykieta + akcja), siatka (kafelki w N kolumnach).
- Słownik akcji (zamknięty): przejdź do ekranu (ścieżka ekranu z parametrami), odtwórz strumień (URL), pauza/wznów, głośność (krok ±), wstecz.
- Telewizor niczego nie wylicza: „następna/poprzednia stacja” to akcje „przejdź do ekranu” z celem wyliczonym przez backend. Opis ekranu przypisuje też CH+/CH− do akcji (np. pole z akcjami klawiszy), żeby backend decydował, co robią w danej aplikacji. Bez przypisania CH± działają jak dotąd (kanały TV).
- Opis ekranu wskazuje blok, który ma fokus na starcie (w odtwarzaczu: play/pauza).
- Odświeżenie: telewizor co `refresh` sekund pobiera ten sam ekran i przerysowuje bloki, zachowując fokus, gdy to możliwe. Jeśli strumień w nowym opisie jest ten sam co grający, dźwięk nie jest przerywany; grająca stacja nie przerywa się także wtedy, gdy wypadła z listy.
- Gdy odświeżenie ekranu się nie uda (błąd HTTP albo brak sieci), telewizor zostawia bieżący ekran i dźwięk bez zmian.
- Backend pamięta każdą stację z dotychczasowych pobrań (po `stationuuid`), żeby odtwarzacz stacji, która wypadła z listy, dalej się budował. Nieznany uuid daje 404 `station_not_found`.
- Błąd strumienia: opis ekranu niesie tekst komunikatu, który telewizor pokazuje, gdy element audio zgłosi błąd.
- Głośność to głośność elementu audio w telewizorze, krokami 10%, trzymana w pamięci na czas sesji.

**Stacje**
- Moduł źródła stacji z jednym wąskim interfejsem: „daj aktualną listę stacji”. Pod spodem: pobieranie z Radio Browser (`/json/stations/search`, `countrycode=PL`, `hidebroken=true`, `order=votes`, `reverse=true`, `limit=20`), lista serwerów-luster z przełączaniem przy błędzie, ogólny User-Agent (np. `LumioTV/1.0`).
- Ta sama lista dla każdego telewizora, niezależnie od regionu. Liczba stacji i kraj to ustawienia backendu.
- Odświeżanie w tle co 15 minut, niezależnie od liczby telewizorów. Telewizory czytają wyłącznie kopię w pamięci.
- Każde udane pobranie zapisywane do stanu runtime (`stations` w data/); po restarcie backend startuje z tej kopii. Nieudane pobranie zostawia ostatnią dobrą listę.
- Stacja w opisie ekranu: identyfikator `stationuuid`, nazwa, logo (`favicon`), strumień (`url_resolved`), kolor zapasowy wyliczany deterministycznie z nazwy.
- Telewizor gra strumień prosto od nadawcy; backend nie przesyła dźwięku.
- Źródło stacji jest wstrzykiwane do API, tak jak store, żeby testy podstawiały atrapę.

**Pusta lista** (pierwszy start bez sieci, bez kopii na dysku): siatka stacji pokazuje tekst „Brak dostępnych stacji, spróbuj później”.

## Testing Decisions

- Dobry test sprawdza zachowanie widoczne z zewnątrz: odpowiedź API (kody, kształt opisu ekranu, kolejność stacji, cele akcji), nie wewnętrzne struktury ani prywatne funkcje.
- Główny szew: endpoint ekranu, testowany przez `Api.handle` i przez serwer HTTP (`ServerTestCase` w `tests/support.py`), z atrapą źródła stacji. Wzorce: `tests/test_api_contract.py`, `tests/test_catalog.py`.
- Drugi szew: granica z Radio Browser. Pobieranie testowane z atrapą transportu HTTP (bez prawdziwej sieci): przełączanie luster, zachowanie ostatniej dobrej listy, zapis i odczyt kopii z data/.
- Testy nie mogą łączyć się z internetem.
- Telewizor (`tv/`) nie ma testów automatycznych; każdy ticket ruszający `tv/` weryfikuje się ręcznie w przeglądarce (`run_server`, `?device=TV-006` albo `TV-004`, bo tylko one spełniają wymagania Music Box: FW ≥ 2.9 i API ≥ 5).
- Wszystkie istniejące testy muszą dalej przechodzić.

## Out of Scope

- RadioWave: zostaje bez zmian (pokazuje tylko nazwę).
- Stacje spoza Polski, wybór stacji per region, wyszukiwanie, ulubione, gatunki.
- Proxy lub przekierowanie strumieni przez backend.
- Zgłaszanie kliknięć i głosów do Radio Browser.
- Zmiana ekranów innych aplikacji poza ekranem domyślnym z nazwą.
- Przycisk głośności na pilocie i trwałe zapamiętywanie głośności.

## Further Notes

- „Pierwsze wdrożenie `tv/`” następuje po ukończeniu wszystkich ticketów tego zadania. Do tego momentu słownik bloków i akcji można jeszcze zmieniać; potem jest kontraktem na zawsze (ADR 0001).
- Ruch: ~170 żądań/s do endpointu ekranu przy 10 000 telewizorach; odpowiedź budowana z danych w pamięci, bez wywołań zewnętrznych na ścieżce żądania.
- Słownictwo: `CONTEXT.md` (Telewizor, Aplikacja, Ekran aplikacji, Blok, Akcja, Music Box, Stacja, Lista stacji, Siatka stacji, Odtwarzacz).
