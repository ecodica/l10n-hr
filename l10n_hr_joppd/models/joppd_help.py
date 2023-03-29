# coding=utf-8

"""
Only help texts and descriptions
so main file can stay clean of extra notes and texts
"""

###########################################################################
# A1
oznaka_help = """
Upisuje se oznaka izvješća u obliku GG001 do GG365(366),
a sastoji se od kombinacije oznake zadnje dvije znamenke godine
i rednog broja dana u godini na koji je izvršena isplata primitka
ili na koji su obračunani i uplaćeni doprinosi, odnosno na koji je
podnesen Obrazac.
Svaki dan u godini ima svoju oznaku te se oznaka izvješća ne može ponavljati.
"""
############################################################################
# A2
vrsta_help = """
Upisuje se oznaka :
1 kada se podnosi prvo (izvorno) izvješće,
2 kada se podnosi ispravak već podnesenog izvješća koje je zaprimljeno od nadležne ispostave Porezne uprave,
3 kada se dopunjuju podaci iskazani na izvornom izvješću.

Oznaka 1 pod vrstom izvješća može se upisati samo jednom za istu oznaku izvješća,
istog podnositelja izvješća i istog obveznika plaćanja.
"""

b71_help = """
Obveza dodatnog doprinosa za mirovinsko osiguranje
za staž osiguranja s povećanim trajanjem – upisuje se:

0 – ukoliko podnositelj po osnovi isplaćenog primitka/obračunane naknade ili
    osnovice za obračun doprinosa nema obvezu obračuna dodatnog doprinosa za
    mirovinsko osiguranje za staž osiguranja s povećanim trajanjem,

1 – ukoliko podnositelj po osnovi isplaćenog primitka/osnovice za obračun doprinosa
    ima obvezu obračuna dodatnog doprinosa za mirovinsko osiguranje za
    staž osiguranja s povećanim trajanjem kada se 12 mjeseci računa kao 14 mjeseci,

2 – ukoliko podnositelj po osnovi isplaćenog primitka/osnovice za obračun doprinosa
    ima obvezu obračuna dodatnog doprinosa za mirovinsko osiguranje za
    staž osiguranja s povećanim trajanjem kada se 12 mjeseci računa kao 15 mjeseci,

3 – ukoliko podnositelj po osnovi isplaćenog primitka/osnovice za obračun doprinosa
    ima obvezu obračuna dodatnog doprinosa za mirovinsko osiguranje za
    staž osiguranja s povećanim trajanjem kada se 12 mjeseci računa kao 16 mjeseci,

4 – ukoliko podnositelj po osnovi isplaćenog primitka/osnovice za obračun doprinosa
    ima obvezu obračuna dodatnog doprinosa za mirovinsko osiguranje za
    staž osiguranja s povećanim trajanjem kada se 12 mjeseci računa kao 18 mjeseci.
"""

b72_help = """
Obveza posebnog doprinosa za poticanje zapošljavanja osoba s invaliditetom – upisuje se:

0 – ukoliko podnositelj nije obveznik posebnog doprinosa
    za poticanje zapošljavanja osoba s invaliditetom,

1 – ukoliko je podnositelj obveznik posebnog doprinosa
    za poticanje zapošljavanja osoba s invaliditetom, po stopi od 0,1%

2 – ukoliko je podnositelj obveznik posebnog doprinosa
    za poticanje zapošljavanja osoba s invaliditetom, po stopi od 0,2%,
"""

b8_help = """
Oznaka prvog/zadnjeg mjeseca u obveznom osiguranju po istoj osnovi – upisuje se:

0 – ukoliko po osnovi isplaćenog primitka/obračunane naknade ili osnovice za obračun
    doprinosa ne postoji obveza prethodnog obveznog osiguranja ili utvrđivanja prava
    po toj osnovi,

1 – ukoliko je to prvi mjesec obveznog osiguranja/korištenja prava po osnovi
    za koju je izvršen obračun,

2 – ukoliko je to zadnji mjesec obveznog osiguranja/korištenja prava po osnovi
    za koju je izvršen obračun,

3 – ukoliko su to ostali mjeseci unutar obveznog osiguranja/korištenja prava po osnovi
    za koju je izvršen obračun,

4 – ukoliko obvezno osiguranje/korištenje prava po osnovi za koju je izvršen obračun
    počinje i završava unutar jednog (izvještajnog) mjeseca,

5 – ukoliko je obveza doprinosa nastala nakon prestanka obveznog osiguranja i
    ne odnosi se na određeni mjesec proveden u tom osiguranju.

Oznake od 1 do 5 unose se za sve skupine stjecatelja primitka/osiguranika za koje se
pod razdoblje za koje se obračunava obveza doprinosa i/ili razdoblje za koje se
primitak isplaćuje (pod 10.1. i 10.2.) upisuje mjesec dana ili kraće od mjesec dana,
odnosno više od mjesec dana ako se isplaćuju zaostale plaće i mirovine,
te za ostale primitke od nesamostalnog rada iz članka 22. stavka 3. Zakona o doprinosima
"""

b9_help = """
Oznaka punog, nepunog radnog vremena ili rada s polovicom radnog vremena  – upisuje se:
0 – ukoliko ne postoji radno vrijeme,
1 – ukoliko je osiguranik prijavljen na puno radno vrijeme,
2 – ukoliko je osiguranik prijavljen na nepuno radno vrijeme,
3 – za osobe koje rade s polovicom punog radnog vremena radi njege djeteta s teškoćama u razvoju.

Oznake od 1 do 3 unose se za sljedeće skupine oznaka stjecatelja primitka/osiguranika iz Priloga 2.
Stjecatelj primitka/osiguranik: 0001-0019; 0021-0029; 0031-0039; 5701-5799,
a oznaka 0 za sve ostale skupine oznaka stjecatelja primitka/osiguranika
"""

b10_help = """
Upisuje se broj obračunanih sati rada za isplatu plaće, za slijedeće skupine
oznaka stjecatelja primitka/osiguranika iz Priloga 2.
Stjecatelj primitka/osiguranik: 0001-0019, 0021-0029, 0031-0039, 5701-5799,
a kada izvješće o korištenju prava iz obveznih osiguranja podnosi poslodavac,
odnosno osoba koja je obveznik doprinosa, te obveznik obračunavanja i obveznik
plaćanja doprinosa sukladno članku 182. stavku 3. Zakona o doprinosima upisuje se
broj obračunanih sati rada za vrijeme korištenja prava.

Oznaka 0 upisuje se za sve ostale skupine oznaka stjecatelja primitka/osiguranika.

Kod isplate zaostale plaće ne upisuje se broj sati rada za mjesece za koje se
plaća isplaćuje ako je isti iskazan u ranijim razdobljima kod podnošenja
izvješća za obračunane doprinose za obvezna osiguranja po osnovi plaće.

Obračunani sati rada za pojedini mjesec iskazuju se samo jednom, kod isplate
redovne plaće odnosno obračuna obveznih doprinosa, a kod svih ostalih isplata
u tijeku jednog mjeseca (za ostale primitke koji se isplaćuju uz plaću,
za isplatu određenog primitka u naravi i drugo)
ne upisuje se broj sati rada. odnosno upisuje se 0.
"""

b_101_102_help = """
Razdoblje za koje se obračunava obveza doprinosa i/ili razdoblje za koje se
primitak isplaćuje odnosno u kojem se isplaćuje.
Razdoblje može biti:
1 - mjesec dana ili kraće od mjesec dana ako u jednom mjesecu počinje i/ili završava
    razdoblje osiguranja prema istoj osnovi osiguranja, što se upisuje
    u formatu od DD.MM.GGGG. do DD.MM.GGGG
2 - više mjeseci, a manje od godinu dana (kalendarske godine),
    što se upisuje u formatu od DD.MM.GGGG. do DD.MM.
3 - te kalendarska godina što se upisuje u formatu od 01.01.GGGG. do 31.12.GGGG.
"""

b12_help = """
Osnovica za obračun doprinosa (pod 12.). Kada je osnovica viša od najviše mjesečne ili
najviše godišnje osnovice za obračun doprinosa za obvezno mirovinsko osiguranje,
upisuje se stvarni iznos osnovice (ne upisuje se iznos najviše mjesečne ili godišnje osnovice).
"""

b121_help = """
Iznos obračunanih doprinosa za mirovinsko osiguranje na temelju generacijske solidarnosti
primjenom propisane stope na osnovicu za obračun doprinosa.
"""