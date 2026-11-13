# 05 — Ulubione stacje

**What to build:** Widz dodaje grającą stację do ulubionych przyciskiem w odtwarzaczu, a ten sam przycisk ją usuwa. Ulubione stacje mają gwiazdkę na kafelku siatki i w liście po prawej; kolejność listy się nie zmienia. Ulubione należą do telewizora i przetrwają restart backendu.

**Blocked by:** 04 — Odtwarzacz Music Box

**Status:** ready-for-agent

- [x] Przycisk „☆ Dodaj do ulubionych” / „★ Usuń z ulubionych” w odtwarzaczu
- [x] Gwiazdka przed nazwą stacji na kafelku i w liście; kolejność i tekst zapasowy logo bez zmian
- [x] `POST /api/devices/<id>/apps/musicbox/favourites` z `{"station", "favourite"}`; 404 dla nieznanego telewizora, niewidocznej aplikacji i nieznanej stacji, 400 dla złych pól
- [x] Ulubione per telewizor w `data/favourites.json` (`--reset` ich nie kasuje)
- [x] Telewizor wykonuje ogólną akcję `post` (wyślij i odśwież ekran, z zachowaniem fokusu i dźwięku)
- [x] Testy API bez sieci; ręczna weryfikacja na TV-006
- [x] Wszystkie testy zielone

## Comments

- Decyzje z rozmowy: tylko gwiazdka (bez zmiany kolejności), ten sam przycisk dodaje i usuwa.
