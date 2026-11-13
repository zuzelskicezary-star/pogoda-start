# 01 — Ekrany aplikacji z backendu

**What to build:** Telewizor po otwarciu dowolnej aplikacji pobiera jej ekran z backendu i go rysuje, zamiast samemu wpisywać nazwę. Każda aplikacja dostaje na razie ekran domyślny z nazwą, więc dla widza nic się nie zmienia, ale od tej chwili backend decyduje, co telewizor pokazuje. To fundament pod Music Box (ADR 0001); spec: `.scratch/music-box/spec.md`.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [x] Endpoint ekranu aplikacji zwraca opis ekranu (drzewo bloków, czas odświeżenia, domyślnie 60 s) dla aplikacji widocznej na danym telewizorze
- [x] 404 dla nieznanego telewizora i dla aplikacji, której telewizor nie widzi w katalogu
- [x] Aplikacja bez własnego ekranu dostaje ekran domyślny z samą nazwą
- [x] Telewizor rysuje bloki: układ (wiersz/kolumna z proporcjami), tekst, przycisk; obsługuje fokus strzałkami i OK, fokus startowy wskazany w opisie
- [x] Telewizor wykonuje akcje „przejdź do ekranu” i „wstecz”; BACK z ekranu pierwszego poziomu wraca do menu, HOME zawsze do menu
- [x] Telewizor co `refresh` sekund pobiera aktualny ekran i przerysowuje go, zachowując fokus
- [x] Opis ekranu może przypisać akcje do CH+/CH−; bez przypisania CH± działają jak dotąd
- [x] Testy API (bez sieci) dla ekranu domyślnego i błędów; ręczna weryfikacja w przeglądarce, że aplikacje wyglądają jak wcześniej
- [x] Wszystkie testy zielone
