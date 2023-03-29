# -*- coding: utf-8 -*-

class JoppdSchema(object):
    """
    Main JOPPD Schema class, common methods
    My vary depending on schema specific parts
    """
    # def __init__(self):
    #     self.naslov = u"Izvješće o primicima, porezu na dohodak i prirezu te doprinosima za obvezna osiguranja"

    def xmldata_strana_B(self):
        sql = """
        SELECT
            B.b1 as P1,
            B.b2 as P2,
            B.b3 as P3,
            B.b4 as P4,
            B.b5 as P5,
            B.b61 as P61,
            B.b62 as P62,
            B.b71 as P71,
            B.b72 as P72,
            B.b8 as P8,
            B.b9 as P9,
            coalesce(B.b10,'0') as P10,
            coalesce(B.b100,'0') as P100,
            B.b101 as P101,
            B.b102 as P102,
            coalesce(B.b11,'0.00') as P11,
            coalesce(B.b12,'0.00') as P12,
            coalesce(B.b121,'0.00') as P121,
            coalesce(B.b122,'0.00') as P122,
            coalesce(B.b123,'0.00') as P123,
            coalesce(B.b124,'0.00') as P124,
            coalesce(B.b125,'0.00') as P125,
            coalesce(B.b126,'0.00') as P126,
            coalesce(B.b127,'0.00') as P127,
            coalesce(B.b128,'0.00') as P128,
            coalesce(B.b129,'0.00') as P129,
            coalesce(B.b131,'0.00') as P131,
            coalesce(B.b132,'0.00') as P132,
            coalesce(B.b133,'0.00') as P133,
            coalesce(B.b134,'0.00') as P134,
            coalesce(B.b135,'0.00') as P135,
            coalesce(B.b141,'0.00') as P141,
            coalesce(B.b142,'0.00') as P142,
            B.b151 as P151,
            coalesce(B.b152,'0.00') as P152,
            B.b161 as P161,
            coalesce(B.b162,'0.00') as P162,
            coalesce(B.b17,'0.00') as P17
        FROM l10n_hr_joppd_b as B
        WHERE joppd_id = %s
        ORDER BY B.b1
        """
        return sql

    def xml_naslov(self):
        return u"Izvješće o primicima, porezu na dohodak i prirezu te doprinosima za obvezna osiguranja"


class JoppdSchemaV10(JoppdSchema):
    """
    Methods for schema version 1.0
    """

    def __init__(self):
        super(JoppdSchemaV10, self).__init__()
        self.conforms = 'ObrazacJOPPD-v1-0'
        self.namespace = "http://e-porezna.porezna-uprava.hr/sheme/zahtjevi/ObrazacJOPPD/v1-0"

    def xml_conforms_to(self):
        return 'ObrazacJOPPD-v1-0'

    def xml_namespace(self):
        return "http://e-porezna.porezna-uprava.hr/sheme/zahtjevi/ObrazacJOPPD/v1-0"

    def oznaka_selection(self):
        popis_oznaka_prilog1 =  [
            ("1", "1 - Pravna osoba"),
            ("2", "2 - Fizička osoba koja obavlja samostalnu djelatnost"),
            ("3", "3 - Poslodavci diplomatske misije i konzularni uredi stranih država i međunarodnih organizacija"),
            ("4", "4 - Ostale fizičke osobe"),
            ("5", "5 - Ostali poslovni subjekti"),
            ("6", "6 - Škola ili ustanova za osiguranike"),
            ("7", "7 - HZMO kada je HZMO obveznik podnošenja"),
            ("8", "8 - HZZO kada je HZZO obveznik podnošenja"),
            ("9", "9 - Ostala tijela (izuzev HZMO i HZZO)"),
            ("10", "10 - Platni agent - kada isplaćuje dividendu dioničarima fizičkim osobama "),
            ("11", "11 - Poslodavac u stečaju - u slučaju izravne isplate plaće"),
            ("12", "12 - Osiguranik po osnovi rada kod poslodavca u drugoj državi članici Europske unije"),
            ("13", "13 - Poslodavac u slučaju kada druga osoba umjesto toga poslodavca isplaćuje plaću"),
        ]
        return popis_oznaka_prilog1

    def stavke_strana_A(self):
        return [
            ("V.1", "Ukupan iznos predujma poreza na dohodak i prireza porezu na dohodak po osnovi nesamostalnog rada (1.1.+1.2.)"),
            ("V.1.1", "Ukupan zbroj stupaca 14.1. i 14.2. sa stranice B pod oznakom stjecatelja primitka/osiguranika (plaća)"),
            ("V.1.2", "Ukupan zbroj stupaca 14.1. i 14.2. sa stranice B pod oznakom stjecatelja primitka/osiguranika (mirovina)"),
            ("V.2", "Ukupan iznos predujma poreza na dohodak i prireza porezu na dohodak po osnovi dohotka od kapitala"),
            ("V.3", "Ukupan iznos predujma poreza na dohodak i prireza porezu na dohodak po osnovi dohotka od imovinskih prava"),
            ("V.4", "Ukupan iznos predujma poreza na dohodak i prireza porezu na dohodak po osnovi dohotka od osiguranja"),
            ("V.5", "Ukupan iznos predujma poreza na dohodak i prireza porezu na dohodak po osnovi primitka od kojeg se utvrđuje drugi dohodak"),

            ("VI.1.1", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju generacijske solidarnosti po osnovi radnog odnosa"),
            ("VI.1.2", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju generacijske solidarnosti po osnovi drugog dohotka"),
            ("VI.1.3", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju generacijske solidarnosti po osnovi poduzetničke plaće"),
            ("VI.1.4", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju generacijske solidarnosti za osiguranike za koje se doprinos uplaćuje prema posebnim propisima"),
            ("VI.1.5", "Ukupan iznos posebnog doprinosa za mirovinsko osiguranje na temelju generacijske solidarnosti za osobe osigurane u određenim okolnostima"),
            ("VI.1.6", "Ukupan iznos dodatnog doprinosa za mirovinsko osiguranje na temelju generacijske solidarnosti za staž osiguranja koji se računa s povećanim trajanjem"),

            ("VI.2.1", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju individualne kapitalizirane štednje po osnovi radnog odnosa"),
            ("VI.2.2", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju individualne kapitalizirane štednje po osnovi drugog dohotka"),
            ("VI.2.3", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju individualne kapitalizirane štednje po osnovi poduzetničke plaće"),
            ("VI.2.4", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju individualne kapitalizirane štednje za osiguranike za koje se doprinos uplaćuje prema posebnim propisima"),
            ("VI.2.5", "Ukupan iznos dodatnog doprinosa za mirovinsko osiguranje na temelju individualne kapitalizirane štednje za staž osiguranja koji se računa s povećanim trajanjem"),

            ("VI.3.1", "Ukupan iznos doprinosa za zdravstveno osiguranje po osnovi radnog odnosa"),
            ("VI.3.2", "Ukupan iznos doprinosa za zaštitu zdravlja na radu po osnovi radnog odnosa"),
            ("VI.3.3", "Ukupan iznos doprinosa za zdravstveno osiguranje po osnovi poduzetničke plaće"),
            ("VI.3.4", "Ukupan iznos doprinosa za zaštitu zdravlja na radu po osnovi poduzetničke plaće"),
            ("VI.3.5", "Ukupan iznos doprinosa za zdravstveno osiguranje po osnovi drugog dohotka"),
            ("VI.3.6", "Ukupan iznos posebnog doprinosa za korištenje zdravstvene zaštite u inozemstvu"),
            ("VI.3.7", "Ukupan iznos dodatnog doprinosa za zdravstveno osiguranje – za obveznike po osnovi korisnika mirovina"),
            ("VI.3.8", "Ukupan iznos doprinosa za zdravstveno osiguranje - za osiguranike za koje se doprinos uplaćuje prema posebnim propisima"),
            ("VI.3.9", "Ukupan iznos doprinosa za zaštitu zdravlja na radu - za osiguranike za koje se doprinos uplaćuje prema posebnim propisima"),
            ("VI.3.10", "Ukupan iznos posebnog doprinosa za zaštitu zdravlja na radu - za osobe osigurane u određenim okolnostima"),

            ("VI.4.1", "Ukupan iznos doprinosa za zapošljavanje"),
            ("VI.4.2", "Ukupan iznos posebnog doprinosa za zapošljavanje osoba s invaliditetom"),
            ("VII", "ISPLAĆENI NEOPOREZIVI PRIMICI"),
            ("VIII", "NAPLAĆENA KAMATA ZA DOPRINOSE ZA MIROVINSKO OSIGURANJE NA TEMELJU INDIVIDUALNE KAPITALIZIRANE ŠTEDNJE"),
        ]

    def sql_sum_B_to_A(self):
        sql = """
        SELECT  SUM(v_1) v_1
              , SUM(v_1_1) v_1_1
              , SUM(v_1_2) v_1_2
              , SUM(v_2) v_2
              , SUM(v_3) v_3
              , SUM(v_4) v_4
              , SUM(v_5) v_5
              , SUM(vi_1_1) vi_1_1
              , SUM(vi_1_2) vi_1_2
              , SUM(vi_1_3) vi_1_3
              , SUM(vi_1_4) vi_1_4
              , SUM(vi_1_5) vi_1_5
              , SUM(vi_1_6) vi_1_6
              , SUM(vi_2_1) vi_2_1
              , SUM(vi_2_2) vi_2_2
              , SUM(vi_2_3) vi_2_3
              , SUM(vi_2_4) vi_2_4
              , SUM(vi_2_5) vi_2_5
              , SUM(vi_3_1) vi_3_1
              , SUM(vi_3_2) vi_3_2
              , SUM(vi_3_3) vi_3_3
              , SUM(vi_3_4) vi_3_4
              , SUM(vi_3_5) vi_3_5
              , SUM(vi_3_6) vi_3_6
              , SUM(vi_3_7) vi_3_7
              , SUM(vi_3_8) vi_3_8
              , SUM(vi_3_9) vi_3_9
              , SUM(vi_3_10) vi_3_10
              , SUM(vi_4_1) vi_4_1
              , SUM(vi_4_2) vi_4_2
              , SUM(vii) vii
              , SUM(viii) viii
        from ( SELECT
           /* POREZ V */
           case when b61n between 1 and 39 or
                     b61n between 101 and 119 or
                     b61n in (121,201,5403)
                then sum(SB.b141) + sum(SB.b142) else 0.0 end as V_1,
           case when b61n between 1 and 39 or b61n in (201, 5403)
                then sum(SB.b141) + sum(SB.b142) else 0.0 end as V_1_1,
           case when b61n between 101 and 119 or b61n =121
                then sum(SB.b141) + sum(SB.b142) else 0.0 end as V_1_2,
           case when b61n between 1001 and 1009
                then sum(SB.b141) + sum(SB.b142) else 0.0 end as V_2,
           case when b61n between 2001 and 2009
                then sum(SB.b141) + sum(SB.b142) else 0.0 end as V_3,
           case when b61n between 3001 and 3009
                then sum(SB.b141) + sum(SB.b142) else 0.0 end as V_4,
           case when b61n between 4001 and 4009 or b61n = 5501
                then sum(SB.b141) + sum(SB.b142) else 0.0 end as V_5,

           /* DOPRINOSI MIROVINSKO GENERACIJSKA SOLIDARNOST - VI.1*/
           case when b61n between 1 and 3 or
                     b61n between 5 and 9 or
                     b61n between 21 and 29 or
                     b61n between 5701 and 5799 then sum(SB.b121) else 0.0 end as VI_1_1,
           case when b61n =201 or b61n=4002 then sum(SB.b121) else 0.0 end as VI_1_2,
           case when b61n between 31 and 39 then sum(SB.b121) else 0.0 end as VI_1_3,
           case when b61n between 5401 and 5403 or
                 b61n = 5608 then sum(SB.b121) else 0.0 end as VI_1_4,
           case when b61n in(5302,5501,5604,5606,5607) then sum(SB.b121) else 0.0 end as VI_1_5,
           sum(SB.b126) as VI_1_6,

           /* DOPRINOSI MIROVINSKO INDIVIDUALNA KAPITALIZIRANA ŠTEDNJA - VI.2 */
           case when b61n between 1 and 3 or
                     b61n between 5 and 9 or
                     b61n between 21 and 29 or
                     b61n between 5701 and 5799 then sum(SB.b122) else 0.0 end as VI_2_1,
           case when b61n =201 or b61n=4002 then sum(SB.b122) else 0.0 end as VI_2_2,
           case when b61n between 31 and 39 then sum(SB.b122) else 0.0 end as VI_2_3,
           case when b61n between 5101 and 5103 or
                     b61n between 5201 and 5299 or
                     b61n between 5401 and 5403 or
                     b61n in (5301,5608) then sum(SB.b122) else 0.0 end as VI_2_4,
           sum(SB.b127) as VI_2_5,

           /* DOPRINOS ZA ZDRAVSTVENO OSIGURANJE VI.3 */
           case when b61n in (1,5,8,9) or b61n between 21 and 29 or
                 b61n between 5701 and 5799 then  sum(SB.b123) else 0.0 end as VI_3_1,
           case when b61n in (1,5,8,9) or b61n between 21 and 29 or
                 b61n between 5701 and 5799 then  sum(SB.b124) else 0.0 end as VI_3_2,
           case when b61n between 31 and 39 then sum(SB.b123) else 0.0 end as VI_3_3,
           case when b61n between 31 and 39 then sum(SB.b124) else 0.0 end as VI_3_4,
           case when b61n in (201,4002) then sum(SB.b123) else 0.0 end as VI_3_5,
           case when b61n between 1 and 39 or b61n = 5402 or
                     b61n between 5001 and 5009 then sum(SB.b128) else 0.0 end as VI_3_6,
           case when b61n between 101 and 119 then sum(SB.b123) else 0.0 end as VI_3_7,
           case when b61n in(5401,5403,5601,5602,5603,5605,5608) then sum(SB.b123) else 0.0 end as VI_3_8,
           case when b61n in(5401,5403,5608) then sum(SB.b124) else 0.0 end as VI_3_9,
           case when b61n in(5302,5501,5604,5606,5607) then sum(SB.b124) else 0.0 end as VI_3_10,

           /* DOPRINOS ZA ZAPOŠLJAVANJE VI.4 */
           sum(SB.b125) as VI_4_1,
           sum(SB.b129) as VI_4_2,
           /* ISPLAĆENI NEOPOREZIVI PRIMICI VII  */
           sum(SB.b152) as VII,
           /* naplaćena kamata VIII */
           case when b62n=5721 then sum(SB.b122) else 0.0 end as VIII
        FROM (SELECT
                  to_number(B61, text(9999)) as b61n,
                  to_number(B62, text(9999)) as b62n,
                  coalesce(B.b11,'0.0') as b11,
                  coalesce(B.b12,'0.0') as b12,
                  coalesce(B.b121,'0.0') as b121,
                  coalesce(B.b122,'0.0') as b122,
                  coalesce(B.b123,'0.0') as b123,
                  coalesce(B.b124,'0.0') as b124,
                  coalesce(B.b125,'0.0') as b125,
                  coalesce(B.b126,'0.0') as b126,
                  coalesce(B.b127,'0.0') as b127,
                  coalesce(B.b128,'0.0') as b128,
                  coalesce(B.b129,'0.0') as b129,
                  coalesce(B.b131,'0.0') as b131,
                  coalesce(B.b132,'0.0') as b132,
                  coalesce(B.b133,'0.0') as b133,
                  coalesce(B.b134,'0.0') as b134,
                  coalesce(B.b135,'0.0') as b135,
                  coalesce(B.b141,'0.0') as b141,
                  coalesce(B.b142,'0.0') as b142,
                  coalesce(B.b152,'0.0') as b152,
                  coalesce(B.b162,'0.0') as b162,
                  coalesce(B.b17,'0.0') as b17
            FROM l10n_hr_joppd_b as B
            WHERE joppd_id = %(joppd_id)s ) as SB
            GROUP BY sb.b61n, sb.b62n ) as SUMB """
        return sql

    def xml_generate_primatelj(self, EM, b):
        return EM.P(EM.P1(b['p1']), EM.P2(b['p2'])
            , EM.P3(b['p3']), EM.P4(b['p4'])
            , EM.P5(b['p5'])
            , EM.P61(b['p61']), EM.P62(b['p62'])
            , EM.P71(b['p71']), EM.P72(b['p72'])
            , EM.P8(b['p8']), EM.P9(b['p9'])
            , EM.P10(b['p10'])
            , EM.P101(b['p101']), EM.P102(b['p102'])
            , EM.P11(b['p11']), EM.P12(b['p12'])
            , EM.P121(b['p121']), EM.P122(b['p122'])
            , EM.P123(b['p123']), EM.P124(b['p124'])
            , EM.P125(b['p125']), EM.P126(b['p126'])
            , EM.P127(b['p127']), EM.P128(b['p128'])
            , EM.P129(b['p129']), EM.P131(b['p131'])
            , EM.P132(b['p132']), EM.P133(b['p133'])
            , EM.P134(b['p134']), EM.P135(b['p135'])
            , EM.P141(b['p141']), EM.P142(b['p142'])
            , EM.P151(b['p151']), EM.P152(b['p152'])
            , EM.P161(b['p161']), EM.P162(b['p162'])
            , EM.P17(b['p17']))

    def xml_strana_A(self, EM, Adata):
        xml = EM.StranaA(
            EM.DatumIzvjesca(joppd['datum']),
            EM.OznakaIzvjesca(joppd['oznaka_izvjesca']),
            EM.VrstaIzvjesca(joppd['vrsta']),
            EM.PodnositeljIzvjesca(
                EM.Naziv(joppd['pod_naziv']),
                EM.Adresa(
                    EM.Mjesto(joppd['pod_mjesto']),
                    EM.Ulica(joppd['pod_ulica']),
                    EM.Broj(joppd['pod_kbr'])),
                EM.Email(joppd['email']),
                EM.OIB(joppd['oib']),
                EM.Oznaka(joppd['oznaka'])),
            EM.BrojOsoba(broj['persons']),
            EM.BrojRedaka(broj['rows']),
            EM.PredujamPoreza(
                EM.P1(str_A[0][1]), EM.P11(str_A[1][1]),
                EM.P12(str_A[2][1]), EM.P2(str_A[3][1]),
                EM.P3(str_A[4][1]), EM.P4(str_A[5][1]),
                EM.P5(str_A[6][1]),
                EM.P6(str_A[7][1])  # new 2015
            ),
            EM.Doprinosi(
                EM.GeneracijskaSolidarnost(
                    EM.P1(str_A[8][1]), EM.P2(str_A[9][1]),
                    EM.P3(str_A[10][1]), EM.P4(str_A[11][1]),
                    EM.P5(str_A[12][1]), EM.P6(str_A[13][1]),
                    EM.P7(str_A[14][1])  # new 2015   ! NEMA U XSD SHEMI!
                ),
                EM.KapitaliziranaStednja(
                    EM.P1(str_A[15][1]), EM.P2(str_A[16][1]),
                    EM.P3(str_A[17][1]), EM.P4(str_A[18][1]),
                    EM.P5(str_A[19][1]),
                    EM.P6(str_A[20][1])  # new 2015 ! NEMA U XSD SHEMI!
                ),
                EM.ZdravstvenoOsiguranje(
                    EM.P1(str_A[21][1]), EM.P2(str_A[22][1]),
                    EM.P3(str_A[23][1]), EM.P4(str_A[24][1]),
                    EM.P5(str_A[25][1]), EM.P6(str_A[26][1]),
                    EM.P7(str_A[27][1]), EM.P8(str_A[28][1]),
                    EM.P9(str_A[29][1]), EM.P10(str_A[30][1]),
                    EM.P11(str_A[31][1]), EM.P12(str_A[32][1])  # new 2015 ! NEMA U XSD SHEMI!
                ),
                EM.Zaposljavanje(
                    EM.P1(str_A[33][1]), EM.P2(str_A[34][1]),
                    EM.P3(str_A[35][1]), EM.P4(str_A[36][1]),  # new 2015 ! NEMA U XSD SHEMI!
                )),
            EM.IsplaceniNeoporeziviPrimici(str_A[37][1]),
            EM.KamataMO2(str_A[38][1]),
            EM.UkupniNeoporeziviPrimici(str_A[39][1]),  # IX - Ukupan iznos neoporezivih primitaka nerezidenata
            EM.NaknadaZaposljavanjeInvalida(
                EM.P1(int(str_A[40][1])), EM.P2(str_A[41][1])),  # X.1 - broj osoba sa invaliditetom
            EM.IzvjesceSastavio(
                EM.Ime(joppd['sast_ime']),
                EM.Prezime(joppd['sast_prezime'])))

    def xml_strana_A(self, EM, a):
        xml = EM.StranaA(
            EM.DatumIzvjesca(a['datum_izvjesca']),
            EM.OznakaIzvjesca(a['oznaka_izvjesca']),
            EM.VrstaIzvjesca(a['vrsta_izvjesca']),
            EM.PodnositeljIzvjesca(
                EM.Naziv(a['podnositelj_naziv']),
                EM.Adresa(
                    EM.Mjesto(a['podnositelj_mjesto']),
                    EM.Ulica(a['podnositelj_ulica']),
                    EM.Broj(a['Podnositelj_kbr'])),
                EM.Email(a['podnositelj_email']),
                EM.OIB(a['podnositelj_oib']),
                EM.Oznaka(a['oznaka'])),
            EM.BrojOsoba(a['broj_osoba']),
            EM.BrojRedaka(a['broj_redaka']),
            EM.PredujamPoreza(
                EM.P1(a.get('V.1', 0.00)),
                EM.P11(a.get('V.1.1', 0.00)),
                EM.P12(a.get('V.1.2', 0.00)),
                EM.P2(a.get('V.2', 0.00)),
                EM.P3(a.get('V.3', 0.00)),
                EM.P4(a.get('V.4', 0.00)),
                EM.P5(a.get('V.5', 0.00)),
            ),
            EM.Doprinosi(
                EM.GeneracijskaSolidarnost(
                    EM.P1(a.get('VI.1.1', 0.00)),
                    EM.P2(a.get('VI.1.2', 0.00)),
                    EM.P3(a.get('VI.1.3', 0.00)),
                    EM.P4(a.get('VI.1.4', 0.00)),
                    EM.P5(a.get('VI.1.5', 0.00)),
                    EM.P6(a.get('VI.1.6', 0.00)),
                ),
                EM.KapitaliziranaStednja(
                    EM.P1(a.get('VI.2.1', 0.00)),
                    EM.P2(a.get('VI.2.2', 0.00)),
                    EM.P3(a.get('VI.2.3', 0.00)),
                    EM.P4(a.get('VI.2.4', 0.00)),
                    EM.P5(a.get('VI.2.5', 0.00)),
                ),
                EM.ZdravstvenoOsiguranje(
                    EM.P1(a.get('VI.3.1', 0.00)),
                    EM.P2(a.get('VI.3.2', 0.00)),
                    EM.P3(a.get('VI.3.3', 0.00)),
                    EM.P4(a.get('VI.3.4', 0.00)),
                    EM.P5(a.get('VI.3.5', 0.00)),
                    EM.P6(a.get('VI.3.6', 0.00)),
                    EM.P7(a.get('VI.3.7', 0.00)),
                    EM.P8(a.get('VI.3.8', 0.00)),
                    EM.P9(a.get('VI.3.9', 0.00)),
                    EM.P10(a.get('VI.3.10', 0.00)),
                    EM.P11(a.get('VI.3.11', 0.00)),
                ),
                EM.Zaposljavanje(
                    EM.P1(a.get('VI.4.1', 0.00)),
                    EM.P2(a.get('VI.4.2', 0.00)),
                    EM.P3(a.get('VI.4.3', 0.00)),
                )),
            EM.IsplaceniNeoporeziviPrimici(a.get('VII', 0.00)),
            EM.KamataMO2(a.get('VIII', 0.00)),
            EM.UkupniNeoporeziviPrimici(a.get('IX', 0.00)),  # IX - Ukupan iznos neoporezivih primitaka nerezidenata
            EM.NaknadaZaposljavanjeInvalida(
                EM.P1(a.get('X.1', 0.00)),
                EM.P2(a.get('X.2', 0.00)),
                EM.IzvjesceSastavio(
                    EM.Ime(a['sast_ime']),
                    EM.Prezime(a['sast_prezime']))))
        return xml


class JoppdSchemaV11(JoppdSchema):
    """
    Methods for schema version 1.1
    """
    def __init__(self):
        super(JoppdSchemaV11, self).__init__()
        self.conforms = 'ObrazacJOPPD-v1-1'
        self.namespace = "http://e-porezna.porezna-uprava.hr/sheme/zahtjevi/ObrazacJOPPD/v1-1"

    def xml_conforms_to(self):
        return 'ObrazacJOPPD-v1-1'

    def xml_namespace(self):
        return "http://e-porezna.porezna-uprava.hr/sheme/zahtjevi/ObrazacJOPPD/v1-1"

    def oznaka_selection(self):
        popis_oznaka_prilog1 = [
            ("1", "1 - Pravna osoba"),
            ("2", "2 - Fizička osoba koja obavlja samostalnu djelatnost"),
            ("3", "3 - Poslodavci diplomatske misije i konzularni uredi stranih država i međunarodnih organizacija"),
            ("4", "4 - Ostale fizičke osobe"),
            ("5", "5 - Ostali poslovni subjekti"),
            ("6", "6 - Škola ili ustanova za osiguranike"),
            ("7", "7 - HZMO kada je HZMO obveznik podnošenja"),
            ("8", "8 - HZZO kada je HZZO obveznik podnošenja"),
            ("9", "9 - Ostala tijela (izuzev HZMO i HZZO)"),
            ("10", "10 - Platni agent - kada isplaćuje dividendu dioničarima fizičkim osobama "),
            ("11", "11 - Poslodavac u stečaju - u slučaju izravne isplate plaće"),
            ("12", "12 - Osiguranik po osnovi rada kod poslodavca u drugoj državi članici Europske unije"),
            ("13", "13 - Poslodavac u slučaju kada druga osoba umjesto toga poslodavca isplaćuje plaću"),
            ("14", "14 - Poslodavac u stečaju  - u slučaju izravne isplate plaće"),
        ]
        return popis_oznaka_prilog1

    def stavke_strana_A(self):
        return [
            ("V.1", "Ukupan iznos predujma poreza na dohodak i prireza porezu na dohodak po osnovi nesamostalnog rada (1.1.+1.2.)"),
            ("V.1.1", "Ukupan zbroj stupaca 14.1. i 14.2. sa stranice B pod oznakom stjecatelja primitka/osiguranika (plaća)"),
            ("V.1.2", "Ukupan zbroj stupaca 14.1. i 14.2. sa stranice B pod oznakom stjecatelja primitka/osiguranika (mirovina)"),
            ("V.2", "Ukupan iznos predujma poreza na dohodak i prireza porezu na dohodak po osnovi dohotka od kapitala"),
            ("V.3", "Ukupan iznos predujma poreza na dohodak i prireza porezu na dohodak po osnovi dohotka od imovinskih prava i posebnih vrsta imovine"),
            ("V.4", "Ukupan iznos predujma poreza na dohodak i prireza porezu na dohodak po osnovi dohotka od osiguranja"),
            ("V.5", "Ukupan iznos predujma poreza na dohodak i prireza porezu na dohodak po osnovi primitka od kojeg se utvrđuje drugi dohodak"),
            ("V.6", "Ukupan iznos predujma poreza na dohodak i prireza porezu na dohodak po osnovi dohotka od kamata"),

            ("VI.1.1", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju generacijske solidarnosti po osnovi radnog odnosa"),
            ("VI.1.2", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju generacijske solidarnosti po osnovi drugog dohotka"),
            ("VI.1.3", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju generacijske solidarnosti po osnovi poduzetničke plaće"),
            ("VI.1.4", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju generacijske solidarnosti za osiguranike za koje se doprinos uplaćuje prema posebnim propisima"),
            ("VI.1.5", "Ukupan iznos posebnog doprinosa za mirovinsko osiguranje na temelju generacijske solidarnosti za osobe osigurane u određenim okolnostima"),
            ("VI.1.6", "Ukupan iznos dodatnog doprinosa za mirovinsko osiguranje na temelju generacijske solidarnosti za staž osiguranja koji se računa s povećanim trajanjem"),
            ("VI.1.7", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju generacijske solidarnosti po osnovi obavljanja samostalne djelatnosti za osobe koje su same za sebe obvezne obračunati doprinose"),

            ("VI.2.1", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju individualne kapitalizirane štednje po osnovi radnog odnosa"),
            ("VI.2.2", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju individualne kapitalizirane štednje po osnovi drugog dohotka"),
            ("VI.2.3", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju individualne kapitalizirane štednje po osnovi poduzetničke plaće"),
            ("VI.2.4", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju individualne kapitalizirane štednje za osiguranike za koje se doprinos uplaćuje prema posebnim propisima"),
            ("VI.2.5", "Ukupan iznos dodatnog doprinosa za mirovinsko osiguranje na temelju individualne kapitalizirane štednje za staž osiguranja koji se računa s povećanim trajanjem"),
            ("VI.2.6", "Ukupan iznos doprinosa za mirovinsko osiguranje na temelju individualne kapitalizirane štednje po osnovi obavljanja samostalne djelatnosti za osobe koje su same za sebe obvezne obračunati doprinose"),

            ("VI.3.1", "Ukupan iznos doprinosa za zdravstveno osiguranje po osnovi radnog odnosa"),
            ("VI.3.2", "Ukupan iznos doprinosa za zaštitu zdravlja na radu po osnovi radnog odnosa"),
            ("VI.3.3", "Ukupan iznos doprinosa za zdravstveno osiguranje po osnovi poduzetničke plaće"),
            ("VI.3.4", "Ukupan iznos doprinosa za zaštitu zdravlja na radu po osnovi poduzetničke plaće"),
            ("VI.3.5", "Ukupan iznos doprinosa za zdravstveno osiguranje po osnovi drugog dohotka"),
            ("VI.3.6", "Ukupan iznos posebnog doprinosa za korištenje zdravstvene zaštite u inozemstvu"),
            ("VI.3.7", "Ukupan iznos dodatnog doprinosa za zdravstveno osiguranje – za obveznike po osnovi korisnika mirovina"),
            ("VI.3.8", "Ukupan iznos doprinosa za zdravstveno osiguranje - za osiguranike za koje se doprinos uplaćuje prema posebnim propisima"),
            ("VI.3.9", "Ukupan iznos doprinosa za zaštitu zdravlja na radu - za osiguranike za koje se doprinos uplaćuje prema posebnim propisima"),
            ("VI.3.10", "Ukupan iznos posebnog doprinosa za zaštitu zdravlja na radu - za osobe osigurane u određenim okolnostima"),
            ("VI.3.11", "Ukupan iznos doprinosa za zdravstveno osiguranje po osnovi obavljanja samostalne djelatnosti za osobe koje su same za sebe obvezne obračunati doprinose"),
            ("VI.3.12", "Ukupan iznos doprinosa za zaštitu zdravlja na radu po osnovi obavljanja samostalne djelatnosti za osobe koje su same za sebe obvezne obračunati doprinose"),

            ("VI.4.1", "Ukupan iznos doprinosa za zapošljavanje"),
            ("VI.4.2", "Ukupan iznos posebnog doprinosa za zapošljavanje osoba s invaliditetom"),
            ("VI.4.3", "Ukupan iznos doprinosa za zapošljavanje po osnovi poduzetničke plaće"),
            ("VI.4.4", "Ukupan iznos doprinosa za zapošljavanje po osnovi obavljanja samostalne djelatnosti za osobe koje su same za sebe obvezne obračunati doprinose"),

            ("VII", "ISPLAĆENI NEOPOREZIVI PRIMICI"),
            ("VIII", "NAPLAĆENA KAMATA ZA DOPRINOSE ZA MIROVINSKO OSIGURANJE NA TEMELJU INDIVIDUALNE KAPITALIZIRANE ŠTEDNJE"),
            ("IX", "UKUPAN IZNOS NEOPOREZIVIH PRIMITAKA NEREZIDENATA KOJE ISPLAĆUJU NEPROFITNE ORGANIZACIJE DO PROPISANOG IZNOSA"),
            ("X.1", "Broj osoba s invaliditetom koje je obveznik bio dužan zaposliti"),
            ("X.1", "Iznos obračunane naknade (X.1)"),
        ]

    def sql_sum_B_to_A(self):
        # TODO: move to l10n_hr_joppd_data module, modify for sql_common framework
        """
        SQL za zbrajanje strane B
        Prebaciti u drugi modul čim zavrsim testiranje generiranja XML-a
        """
        sql = """
        SELECT  SUM(v_1) v_1
              , SUM(v_1_1) v_1_1
              , SUM(v_1_2) v_1_2
              , SUM(v_2) v_2
              , SUM(v_3) v_3
              , SUM(v_4) v_4
              , SUM(v_5) v_5
              , 0.00 v_6 -- new2015
              , SUM(vi_1_1) vi_1_1
              , SUM(vi_1_2) vi_1_2
              , SUM(vi_1_3) vi_1_3
              , SUM(vi_1_4) vi_1_4
              , SUM(vi_1_5) vi_1_5
              , SUM(vi_1_6) vi_1_6
              , 0.00 vi_1_7 -- new2015
              , SUM(vi_2_1) vi_2_1
              , SUM(vi_2_2) vi_2_2
              , SUM(vi_2_3) vi_2_3
              , SUM(vi_2_4) vi_2_4
              , SUM(vi_2_5) vi_2_5
              , 0.00 vi_2_6 -- new2015
              , SUM(vi_3_1) vi_3_1
              , SUM(vi_3_2) vi_3_2
              , SUM(vi_3_3) vi_3_3
              , SUM(vi_3_4) vi_3_4
              , SUM(vi_3_5) vi_3_5
              , SUM(vi_3_6) vi_3_6
              , SUM(vi_3_7) vi_3_7
              , SUM(vi_3_8) vi_3_8
              , SUM(vi_3_9) vi_3_9
              , SUM(vi_3_10) vi_3_10
              , 0.00 vi_3_11 -- new2015
              , 0.00 vi_3_12 -- new2015
              , SUM(vi_4_1) vi_4_1
              , SUM(vi_4_2) vi_4_2
              , 0.00 vi_4_3 -- new2015
              , 0.00 vi_4_4 -- new2015
              , SUM(vii) vii
              , SUM(viii) viii
              , 0.00 ix -- new2015
              , 0 x_1 -- new2015 fantomski 1
              , 0 x_2 -- new2015
        from ( SELECT
           /* POREZ V */
           case when b61n between 1 and 39 or
                     b61n between 101 and 119 or
                     b61n in (121,201,5403)
                then sum(SB.b141) + sum(SB.b142) else 0.0 end as V_1,
           case when b61n between 1 and 39 or b61n in (201, 5403)
                then sum(SB.b141) + sum(SB.b142) else 0.0 end as V_1_1,
           case when b61n between 101 and 119 or b61n =121
                then sum(SB.b141) + sum(SB.b142) else 0.0 end as V_1_2,
           case when b61n between 1001 and 1009
                then sum(SB.b141) + sum(SB.b142) else 0.0 end as V_2,
           case when b61n between 2001 and 2009
                then sum(SB.b141) + sum(SB.b142) else 0.0 end as V_3,
           case when b61n between 3001 and 3009
                then sum(SB.b141) + sum(SB.b142) else 0.0 end as V_4,
           case when b61n between 4001 and 4009 or b61n = 5501
                then sum(SB.b141) + sum(SB.b142) else 0.0 end as V_5,

           /* DOPRINOSI MIROVINSKO GENERACIJSKA SOLIDARNOST - VI.1*/
           case when b61n between 1 and 3 or
                     b61n between 5 and 9 or
                     b61n between 21 and 29 or
                     b61n between 5701 and 5799 then sum(SB.b121) else 0.0 end as VI_1_1,
           case when b61n =201 or b61n=4002 then sum(SB.b121) else 0.0 end as VI_1_2,
           case when b61n between 31 and 39 then sum(SB.b121) else 0.0 end as VI_1_3,
           case when b61n between 5401 and 5403 or
                 b61n = 5608 then sum(SB.b121) else 0.0 end as VI_1_4,
           case when b61n in(5302,5501,5604,5606,5607) then sum(SB.b121) else 0.0 end as VI_1_5,
           sum(SB.b126) as VI_1_6,

           /* DOPRINOSI MIROVINSKO INDIVIDUALNA KAPITALIZIRANA ŠTEDNJA - VI.2 */
           case when b61n between 1 and 3 or
                     b61n between 5 and 9 or
                     b61n between 21 and 29 or
                     b61n between 5701 and 5799 then sum(SB.b122) else 0.0 end as VI_2_1,
           case when b61n =201 or b61n=4002 then sum(SB.b122) else 0.0 end as VI_2_2,
           case when b61n between 31 and 39 then sum(SB.b122) else 0.0 end as VI_2_3,
           case when b61n between 5101 and 5103 or
                     b61n between 5201 and 5299 or
                     b61n between 5401 and 5403 or
                     b61n in (5301,5608) then sum(SB.b122) else 0.0 end as VI_2_4,
           sum(SB.b127) as VI_2_5,

           /* DOPRINOS ZA ZDRAVSTVENO OSIGURANJE VI.3 */
           case when b61n in (1,5,8,9) or b61n between 21 and 29 or
                 b61n between 5701 and 5799 then  sum(SB.b123) else 0.0 end as VI_3_1,
           case when b61n in (1,5,8,9) or b61n between 21 and 29 or
                 b61n between 5701 and 5799 then  sum(SB.b124) else 0.0 end as VI_3_2,
           case when b61n between 31 and 39 then sum(SB.b123) else 0.0 end as VI_3_3,
           case when b61n between 31 and 39 then sum(SB.b124) else 0.0 end as VI_3_4,
           case when b61n in (201,4002) then sum(SB.b123) else 0.0 end as VI_3_5,
           case when b61n between 1 and 39 or b61n = 5402 or
                     b61n between 5001 and 5009 then sum(SB.b128) else 0.0 end as VI_3_6,
           case when b61n between 101 and 119 then sum(SB.b123) else 0.0 end as VI_3_7,
           case when b61n in(5401,5403,5601,5602,5603,5605,5608) then sum(SB.b123) else 0.0 end as VI_3_8,
           case when b61n in(5401,5403,5608) then sum(SB.b124) else 0.0 end as VI_3_9,
           case when b61n in(5302,5501,5604,5606,5607) then sum(SB.b124) else 0.0 end as VI_3_10,

           /* DOPRINOS ZA ZAPOŠLJAVANJE VI.4 */
           sum(SB.b125) as VI_4_1,
           sum(SB.b129) as VI_4_2,
           /* ISPLAĆENI NEOPOREZIVI PRIMICI VII  */
           sum(SB.b152) as VII,
           /* naplaćena kamata VIII */
           case when b62n=5721 then sum(SB.b122) else 0.0 end as VIII
        FROM (SELECT
                  to_number(B61, text(9999)) as b61n,
                  to_number(B62, text(9999)) as b62n,
                  coalesce(B.b11,'0.0') as b11,
                  coalesce(B.b12,'0.0') as b12,
                  coalesce(B.b121,'0.0') as b121,
                  coalesce(B.b122,'0.0') as b122,
                  coalesce(B.b123,'0.0') as b123,
                  coalesce(B.b124,'0.0') as b124,
                  coalesce(B.b125,'0.0') as b125,
                  coalesce(B.b126,'0.0') as b126,
                  coalesce(B.b127,'0.0') as b127,
                  coalesce(B.b128,'0.0') as b128,
                  coalesce(B.b129,'0.0') as b129,
                  coalesce(B.b131,'0.0') as b131,
                  coalesce(B.b132,'0.0') as b132,
                  coalesce(B.b133,'0.0') as b133,
                  coalesce(B.b134,'0.0') as b134,
                  coalesce(B.b135,'0.0') as b135,
                  coalesce(B.b141,'0.0') as b141,
                  coalesce(B.b142,'0.0') as b142,
                  coalesce(B.b152,'0.0') as b152,
                  coalesce(B.b162,'0.0') as b162,
                  coalesce(B.b17,'0.0') as b17
            FROM l10n_hr_joppd_b as B
            WHERE joppd_id = %(joppd_id)s ) as SB
            GROUP BY sb.b61n, sb.b62n ) as SUMB """
        return sql

    def xml_generate_primatelj(self, EM, b):
        return EM.P(EM.P1(b['p1']), EM.P2(b['p2'])
                  , EM.P3(b['p3']), EM.P4(b['p4'])
                  , EM.P5(b['p5'])
                  , EM.P61(b['p61']), EM.P62(b['p62'])
                  , EM.P71(b['p71']), EM.P72(b['p72'])
                  , EM.P8(b['p8']), EM.P9(b['p9'])
                  , EM.P10(b['p10']), EM.P100(b['p100'])
                  , EM.P101(b['p101']), EM.P102(b['p102'])
                  , EM.P11(b['p11']), EM.P12(b['p12'])
                  , EM.P121(b['p121']), EM.P122(b['p122'])
                  , EM.P123(b['p123']), EM.P124(b['p124'])
                  , EM.P125(b['p125']), EM.P126(b['p126'])
                  , EM.P127(b['p127']), EM.P128(b['p128'])
                  , EM.P129(b['p129']), EM.P131(b['p131'])
                  , EM.P132(b['p132']), EM.P133(b['p133'])
                  , EM.P134(b['p134']), EM.P135(b['p135'])
                  , EM.P141(b['p141']), EM.P142(b['p142'])
                  , EM.P151(b['p151']), EM.P152(b['p152'])
                  , EM.P161(b['p161']), EM.P162(b['p162'])
                  , EM.P17(b['p17']))

    def xml_strana_A(self, EM, a):
        """
        :param EM: Element Maker object
        :param a: dict, strana A podaci
        :return: objectified XML element
        """
        xml = EM.StranaA(
            EM.DatumIzvjesca(a['datum_izvjesca']),
            EM.OznakaIzvjesca(a['oznaka_izvjesca']),
            EM.VrstaIzvjesca(a['vrsta_izvjesca']),
            EM.PodnositeljIzvjesca(
                EM.Naziv(a['podnositelj_naziv']),
                EM.Adresa(
                    EM.Mjesto(a['podnositelj_mjesto']),
                    EM.Ulica(a['podnositelj_ulica']),
                    EM.Broj(a['podnositelj_kbr'])
                ),
                EM.Email(a['podnositelj_email']),
                EM.OIB(a['podnositelj_oib']),
                EM.Oznaka(a['podnositelj_oznaka'])
            ),
            EM.BrojOsoba(a['broj_osoba']),
            EM.BrojRedaka(a['broj_redaka']),
            EM.PredujamPoreza(
                EM.P1(a.get('V.1', 0.00)),
                EM.P11(a.get('V.1.1', 0.00)),
                EM.P12(a.get('V.1.2', 0.00)),
                EM.P2(a.get('V.2', 0.00)),
                EM.P3(a.get('V.3', 0.00)),
                EM.P4(a.get('V.4', 0.00)),
                EM.P5(a.get('V.5', 0.00)),
                EM.P6(a.get('V.6', 0.00))
            ),
            EM.Doprinosi(
                EM.GeneracijskaSolidarnost(
                    EM.P1(a.get('VI.1.1', 0.00)),
                    EM.P2(a.get('VI.1.2', 0.00)),
                    EM.P3(a.get('VI.1.3', 0.00)),
                    EM.P4(a.get('VI.1.4', 0.00)),
                    EM.P5(a.get('VI.1.5', 0.00)),
                    EM.P6(a.get('VI.1.6', 0.00)),
                    EM.P7(a.get('VI.1.7', 0.00))
                ),
                EM.KapitaliziranaStednja(
                    EM.P1(a.get('VI.2.1', 0.00)),
                    EM.P2(a.get('VI.2.2', 0.00)),
                    EM.P3(a.get('VI.2.3', 0.00)),
                    EM.P4(a.get('VI.2.4', 0.00)),
                    EM.P5(a.get('VI.2.5', 0.00)),
                    EM.P6(a.get('VI.2.6', 0.00))
                ),
                EM.ZdravstvenoOsiguranje(
                    EM.P1(a.get('VI.3.1', 0.00)),
                    EM.P2(a.get('VI.3.2', 0.00)),
                    EM.P3(a.get('VI.3.3', 0.00)),
                    EM.P4(a.get('VI.3.4', 0.00)),
                    EM.P5(a.get('VI.3.5', 0.00)),
                    EM.P6(a.get('VI.3.6', 0.00)),
                    EM.P7(a.get('VI.3.7', 0.00)),
                    EM.P8(a.get('VI.3.8', 0.00)),
                    EM.P9(a.get('VI.3.9', 0.00)),
                    EM.P10(a.get('VI.3.10', 0.00)),
                    EM.P11(a.get('VI.3.11', 0.00)),
                    EM.P12(a.get('VI.3.12', 0.00))
                ),
                EM.Zaposljavanje(
                    EM.P1(a.get('VI.4.1', 0.00)),
                    EM.P2(a.get('VI.4.2', 0.00)),
                    EM.P3(a.get('VI.4.3', 0.00)),
                    EM.P4(a.get('VI.4.4', 0.00)),
                )
            ),
            EM.IsplaceniNeoporeziviPrimici(a.get('VII', 0.00)),
            EM.KamataMO2(a.get('VIII', 0.00)),
            EM.UkupniNeoporeziviPrimici(a.get('IX', 0.00)),  # IX - Ukupan iznos neoporezivih primitaka nerezidenata
            EM.NaknadaZaposljavanjeInvalida(
                EM.P1(int(a.get('X.1', 0))),
                EM.P2(a.get('X.2', 0.00)),
            ),
            EM.IzvjesceSastavio(
                EM.Ime(a['sast_ime']),
                EM.Prezime(a['sast_prezime'])
            )
        )
        return xml
