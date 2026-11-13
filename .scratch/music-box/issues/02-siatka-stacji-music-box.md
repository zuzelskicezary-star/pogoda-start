# 02 — Siatka stacji Music Box

**What to build:** Po otwarciu Music Box widz widzi siatkę 20 najpopularniejszych działających polskich stacji z Radio Browser: kafelki z logo i nazwą, a gdy logo brak lub się nie ładuje, kolorowy kafelek z nazwą. Ta sama lista na każdym telewizorze. Backend pobiera stacje w tle i serwuje je z pamięci. Spec: `.scratch/music-box/spec.md`.

**Blocked by:** 01 — Ekrany aplikacji z backendu

**Status:** ready-for-agent

- [ ] Źródło stacji z wąskim interfejsem „aktualna lista stacji”, wstrzykiwane do API (testy podstawiają atrapę)
- [ ] Pobieranie z Radio Browser: PL, bez zepsutych, po głosach malejąco, limit 20; ogólny User-Agent; liczba i kraj to ustawienia backendu
- [ ] Odświeżanie w tle (np. co 15 min); żądania telewizorów nigdy nie wywołują Radio Browser
- [ ] Ekran Music Box to siatka kafelków; kafelek ma akcję „przejdź do ekranu” odtwarzacza tej stacji (sam odtwarzacz w 04)
- [ ] Kolor zapasowy kafelka wyliczany deterministycznie z nazwy stacji
- [ ] Pusta lista daje tekst „Brak dostępnych stacji, spróbuj później”
- [ ] Telewizor rysuje bloki siatka, kafelek i obraz z zapasowym kolorem (także przy błędzie ładowania logo)
- [ ] Testy API z atrapą źródła: kształt siatki, kolejność, ta sama lista dla NA/EU/APAC, pusta lista; ręczna weryfikacja na TV-006
- [ ] Wszystkie testy zielone
