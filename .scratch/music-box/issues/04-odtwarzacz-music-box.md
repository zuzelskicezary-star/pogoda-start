# 04 — Odtwarzacz Music Box

**What to build:** Po wybraniu stacji gra ona od razu. Odtwarzacz pokazuje po lewej logo i nazwę grającej stacji z przyciskami (poprzednia, play/pauza, następna, głośność −/+, wróć do stacji), po prawej listę pozostałych stacji do wyboru. CH+/CH− przełączają stacje, BACK wraca do siatki. Odświeżenie co minutę nie przerywa dźwięku. Spec: `.scratch/music-box/spec.md`.

**Blocked by:** 02 — Siatka stacji Music Box

**Status:** ready-for-agent

- [ ] Ekran odtwarzacza dla `station=<uuid>` niesie strumień do grania (`url_resolved`), tekst błędu strumienia i fokus startowy na play/pauza
- [ ] Poprzednia/następna i CH−/CH+ to akcje „przejdź do ekranu” z celem wyliczonym przez backend (z zawijaniem na końcach listy)
- [ ] Lista po prawej zawiera pozostałe stacje; wybranie pozycji przełącza stację
- [ ] Backend pamięta każdą stację z dotychczasowych pobrań (po uuid), więc stacja, która wypadła z listy przy odświeżeniu, nadal ma ekran odtwarzacza i gra dalej
- [ ] Nieznany uuid daje 404 `station_not_found`; gdy odświeżenie ekranu się nie uda (404, brak sieci), telewizor zostawia bieżący ekran i dźwięk
- [ ] Telewizor wykonuje akcje: odtwórz strumień, pauza/wznów, głośność ±10%; gra strumień prosto od nadawcy
- [ ] Odświeżenie z tym samym strumieniem nie przerywa dźwięku; błąd audio pokazuje tekst z opisu ekranu
- [ ] BACK i przycisk „wróć” prowadzą do siatki stacji, HOME do menu; wyjście z Music Box zatrzymuje dźwięk
- [ ] Testy API z atrapą źródła: kształt odtwarzacza, cele poprzedniej/następnej, stacja spoza listy, nieznany uuid; ręczna weryfikacja na TV-006 (dźwięk, pauza, głośność, CH±, odświeżenie)
- [ ] Wszystkie testy zielone
