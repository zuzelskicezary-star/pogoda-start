# 04 — Odtwarzacz Music Box

**What to build:** Po wybraniu stacji gra ona od razu. Odtwarzacz pokazuje po lewej logo i nazwę grającej stacji z przyciskami (poprzednia, play/pauza, następna, głośność −/+, wróć do stacji), po prawej listę pozostałych stacji do wyboru. CH+/CH− przełączają stacje, BACK wraca do siatki. Odświeżenie co minutę nie przerywa dźwięku. Spec: `.scratch/music-box/spec.md`.

**Blocked by:** 02 — Siatka stacji Music Box

**Status:** ready-for-agent

- [x] Ekran odtwarzacza dla `station=<uuid>` niesie strumień do grania (`url_resolved`), tekst błędu strumienia i fokus startowy na play/pauza
- [x] Poprzednia/następna i CH−/CH+ to akcje „przejdź do ekranu” z celem wyliczonym przez backend (z zawijaniem na końcach listy)
- [x] Lista po prawej zawiera pozostałe stacje; wybranie pozycji przełącza stację
- [x] Backend pamięta każdą stację z dotychczasowych pobrań (po uuid), więc stacja, która wypadła z listy przy odświeżeniu, nadal ma ekran odtwarzacza i gra dalej
- [x] Nieznany uuid daje 404 `station_not_found`; gdy odświeżenie ekranu się nie uda (404, brak sieci), telewizor zostawia bieżący ekran i dźwięk
- [x] Telewizor wykonuje akcje: odtwórz strumień, pauza/wznów, głośność ±10%; gra strumień prosto od nadawcy
- [x] Odświeżenie z tym samym strumieniem nie przerywa dźwięku; błąd audio pokazuje tekst z opisu ekranu
- [x] BACK i przycisk „wróć” prowadzą do siatki stacji, HOME do menu; wyjście z Music Box zatrzymuje dźwięk
- [x] Testy API z atrapą źródła: kształt odtwarzacza, cele poprzedniej/następnej, stacja spoza listy, nieznany uuid; ręczna weryfikacja na TV-006 (dźwięk, pauza, głośność, CH±, odświeżenie)
- [x] Wszystkie testy zielone

## Comments

- Decyzje przy implementacji:
  - Pamięć stacji po uuid trzyma Music Box (źródło stacji zostaje przy wąskim `current()`), zapisuje każdą stację odczytaną z listy. Pamięć jest w procesie: po restarcie backendu stacja spoza listy dostaje 404, a telewizor zostawia bieżący ekran i dźwięk.
  - Stacja spoza listy: „następna” to pierwsza stacja listy, „poprzednia” ostatnia.
  - Przełączanie stacji (poprzednia/następna, CH±, lista po prawej) używa `open_screen` z `replace: true`, więc BACK zawsze wraca do siatki (ADR 0001).
  - Siatka stacji nie zatrzymuje dźwięku; zatrzymuje go wyjście z Music Box (BACK z siatki, HOME, CH± poza aplikacją, zasilanie).
  - Gdy przeglądarka blokuje autoodtwarzanie, telewizor pokazuje podpowiedź, żeby nacisnąć play/pauza.
