# Lumio TV

Backend i klient telewizorów Lumio: rejestr urządzeń, aktualizacje firmware'u, katalog aplikacji i ekrany aplikacji wyświetlane na telewizorze.

## Telewizor i aplikacje

**Telewizor**:
Jedno urządzenie Lumio z rejestru, identyfikowane przez `id` (np. `TV-001`), z modelem, regionem i firmware'em. Kod klienta telewizora po pierwszym wdrożeniu jest niezmienny.
_Avoid_: TV client, urządzenie (gdy chodzi o konkretny telewizor)

**Aplikacja**:
Pozycja katalogu widoczna jako kafelek w menu głównym telewizora.
_Avoid_: app tile, program

**Ekran aplikacji**:
To, co telewizor pokazuje po otwarciu aplikacji, w całości opisane przez backend i złożone z bloków znanych telewizorowi.
_Avoid_: widok, strona aplikacji

**Blok**:
Element ekranu aplikacji z zamkniętego słownika, który telewizor umie narysować (układ, tekst, obraz, kafelek, siatka, lista, przycisk).
_Avoid_: widget, komponent

**Akcja**:
Czynność z zamkniętego słownika, którą telewizor wykonuje po wybraniu bloku (np. przejście do innego ekranu, odtworzenie strumienia, pauza, głośność, powrót).
_Avoid_: komenda, handler

## Music Box

**Music Box**:
Aplikacja odtwarzająca polskie stacje radiowe online. Jedyna aplikacja radiowa w zakresie; RadioWave to osobna, niezmieniana aplikacja.
_Avoid_: radio app, RadioWave

**Stacja**:
Polska stacja radiowa nadająca online, pochodząca z Radio Browser, z nazwą, logo i adresem strumienia.
_Avoid_: kanał (to pojęcie telewizji linearnej, przyciski CH±), radio

**Lista stacji**:
20 najpopularniejszych działających polskich stacji, ta sama dla każdego telewizora niezależnie od regionu.
_Avoid_: playlista, katalog stacji

**Siatka stacji**:
Ekran Music Box po otwarciu: lista stacji jako kafelki z logo i nazwą.
_Avoid_: menu stacji, home radia

**Odtwarzacz**:
Ekran Music Box po wybraniu stacji: grająca stacja, przyciski nawigujące i po prawej pozostałe stacje z listy.
_Avoid_: player, ekran stacji

**Ulubione**:
Stacje oznaczone gwiazdką przez widza na danym telewizorze; kolejność listy stacji się nie zmienia.
_Avoid_: zakładki, playlista

