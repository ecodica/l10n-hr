SCHEMA_HELP = """
verzija: 1.3 Datum verzije: 04.07.2016.
- u WSDL-u dodana nova metoda "provjera"
- u schemi dodani novi elementi "ProvjeraZahtjev" i "ProvjeraOdgovor"

verzija: 1.4 Datum verzije: 27.04.2017.
- u WSDL-u izbačena metoda "poslovniProstor"
-u schemi izbačeni elementi "PoslovniProstorZahtjev",
   "PoslovniProstorOdgovor"i ostalo vezano za prijavu poslovnih prostora

verzija: 1.5 Datum verzije: 20.12.2019.
- u WSDL-u dodane dvije metode "prateciDokumenti" i "racuniPD"
- u schemi dodani elementi "PrateciDokumentiZahtjev",
   "PrateciDokumentiOdgovor", "RacunPDZahtjev",
   "RacunPDOdgovor" i ostalo vezano za nove elemente.

verzija: 1.7 Datum verzije: 11.10.2023.
- u WSDL-u dodana nova metoda 'napojnica'
- u schemi dodani elementi "NapojnicaZahtjev",
  "NapojnicaOdgovor" i ostalo vezano za nove elemente.

verzija: 1.8 Datum verzije: 18.06.2025.
- izbačena metoda i sve pripadne elemente za prateće dokumente (PrateciDokumentiZahtjev, PrateciDokumentiOdgovor)
- izbačena metoda i sve pripadne elemente za račune koji se odnose na prateće dokumente (RacunPDZahtjev, RacunPDOdgovor)
- izbačeni elementi koji se odnose na prateće dokumente iz metode za promjenu načina plaćanja (PromijeniNacPlacZahtjev)
                JirPD, ZastKodPD
- izbačeni elementi koji se odnose na prateće dokumente iz metode za prijavu napojnice (NapojnicaZahtjev)
                JirPD, ZastKodPD
- izbačeni elementi za provjeru računa (ProvjeraZahtjev, ProvjeraOdgovor) dio vezan za provjeru računa koji se odnosi na prateće dokumente

verzija: 1.9 Datum verzije: 24.06.2025.
- nova metoda promijeniPodatkeRacuna
- nove metode za radno vrijeme:
- prijaviRadnoVrijeme
- obrisiRadnoVrijeme
- dohvatiRadnoVrijeme

verzija: 1.10 Datum verzije: 24.11.2025.
- nove metode za radno vrijeme:
- prijaviRadnoVrijemeZaPoslovnice
"""
