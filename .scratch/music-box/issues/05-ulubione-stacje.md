# 05 — Ulubione stacje

**What to build:** Widz dodaje grającą stację do ulubionych przyciskiem w odtwarzaczu, a ten sam przycisk ją usuwa. Ulubione stacje mają gwiazdkę i są na początku siatki, listy po prawej i kolejności poprzednia/następna. Przycisk nad siatką pokazuje tylko ulubione. Ulubione należą do telewizora i przetrwają restart backendu.

**Blocked by:** 04 — Odtwarzacz Music Box

**Status:** ready-for-agent

- [x] Przycisk „☆ Dodaj do ulubionych” / „★ Usuń z ulubionych” w odtwarzaczu
- [x] Gwiazdka przed nazwą stacji na kafelku i w liście; tekst zapasowy logo bez zmian
- [x] Ulubione na początku siatki, listy i kolejności poprzednia/następna; reszta w kolejności z Radio Browser
- [x] Przycisk „★ Tylko ulubione” / „Wszystkie stacje” nad siatką (`?view=favourites`, podmienia ekran, więc BACK wraca do menu); pusty widok podpowiada, jak dodać ulubione
- [x] Odtwarzacz otwarty z widoku ulubionych chodzi tylko po ulubionych (poprzednia/następna, CH±, lista), BACK wraca do widoku ulubionych
- [x] `POST /api/devices/<id>/apps/musicbox/favourites` z `{"station", "favourite"}`; 404 dla nieznanego telewizora, niewidocznej aplikacji i nieznanej stacji, 400 dla złych pól
- [x] Ulubione per telewizor w `data/favourites.json` (`--reset` ich nie kasuje)
- [x] Telewizor wykonuje ogólną akcję `post` (wyślij i odśwież ekran, z zachowaniem fokusu i dźwięku)
- [x] Testy API bez sieci; ręczna weryfikacja na TV-006
- [x] Wszystkie testy zielone

## Comments

- Decyzje z rozmowy: ten sam przycisk dodaje i usuwa.
- Zmiana decyzji: zamiast samej gwiazdki ulubione idą na początek listy, a przycisk nad siatką pokazuje tylko ulubione. Odtwarzacz z widoku ulubionych chodzi tylko po ulubionych.
- Widok ulubionych pokazuje ulubione obecne na bieżącej liście stacji; ulubiona stacja, która wypadła z listy, w nim nie występuje.
