# 03 — Odporność listy stacji na awarie Radio Browser

**What to build:** Music Box ma stacje, nawet gdy Radio Browser nie odpowiada: backend przełącza się na inny serwer-lustro, przy porażce zostawia ostatnią dobrą listę, a każdą udaną listę zapisuje w stanie runtime, więc po restarcie w czasie awarii startuje z kopii. Spec: `.scratch/music-box/spec.md`.

**Blocked by:** 02 — Siatka stacji Music Box

**Status:** ready-for-agent

- [x] Lista serwerów Radio Browser; błąd lub timeout jednego powoduje próbę następnego
- [x] Nieudane odświeżenie (wszystkie serwery) nie czyści listy, tylko zostawia ostatnią dobrą
- [x] Każda udana lista zapisywana w data/; przy starcie backend wczytuje ją, zanim zrobi pierwsze pobranie
- [x] Testy z atrapą transportu HTTP (bez sieci): przełączenie luster, zachowanie listy przy błędzie, start z kopii na dysku, pusta lista przy pierwszym starcie bez sieci
- [x] Wszystkie testy zielone

## Comments

- Decyzja przy implementacji: pusta odpowiedź lustra liczy się jak błąd (próba następnego, zostaje ostatnia dobra lista). Skutek: komunikat „Brak dostępnych stacji” pojawia się tylko przy pierwszym starcie bez kopii; jeśli operator zmieni kraj na taki bez stacji, zostanie stara lista. Uszkodzona kopia w data/ jest pomijana (start z pustą listą), a `--reset` nie kasuje kopii listy stacji.
