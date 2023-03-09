===================================
Croatia - Fiscalisation of invoices
===================================

This module provides feture of legaly required fiscalisation process for invoicess
Additional modules will be required for other types of documents.
Available official documentation is available here:
[Fiskalizacija](https://www.porezna-uprava.hr/HR_Fiskalizacija/Stranice/FiskalizacijaNovo.aspx)

Configuration
=============

1. Add fiskal certificate

menuitem : Invoicing >> Configuration >> Croatia specific settings >> Fiskal certificates
Create new certificate, upload the certificate file obtained from FINA in pfx format.
Provide password for certificate and click on "Covert certificate" button.
If all is well, you should see the data obtained from certificate.
YOu may check the data - WSDL schema to be used is also autodetected,
but in futute if more schema will be present, you might want to select a specific one.

2. Activate certificate

In order to use it, certificate should be activated, and set as default certificate on company.
Activatinf the first certificate, will set it as default on your comapny settigns, but it is
recomended to double check the data on company page.

3. Activating fiscalisation process on PoS device.

Only after enabling fiscalisation on PoS device you will be allowed to confirm invoices
with payment meas that are legaly required to be fiskalized (G,C,K,O)

4. Taxes setup

If invoice is to be fiscalized, the taxes applied on lines must have assigned Croatia fiskal tax type.
In order to set it go to taxes settings, and set desired values on sale type taxex, under Advanced options tab.

4. Users setup

Users confirming the invoices, must have OIB entered (enter VAT with HR prefix!)
It is legaly required part of fiskal message and needs to be entered.


Usage
=====

Regular invoices will be fiskalized in the posting process automaticly.
However, if for any reason, the fiscalistion mesage is not sent , or is sent and received and error,
Late fiskalisation is possible from Croatia specific page on ivoice form
Using the buttin FISKALIZE.

If you created an ivoice on Paragon blok. You may enter all invoice data,
including the paragon blok number, and set correct dates, then confirm the invoice.
The check box Late delivery should be marked!

If you want to check the fiskalisation data on already fiskalized invoice, (containing JIR and ZKI data)
you can press FISKALIZE button and send a check-invoice type message (visible in message logs)


Obtain client certificates from FINA
====================================

Which certificates you need depends on whether you're developing and testing
integration (a "DEMO certificate"), or need it to go live and connect to
the service in production ("production certificate").

Production certificate can't be used for integration testing, so if you're
doing everything in-house (developing for own use and need to test the
integration), you'll need to sign up for both DEMO and production cert.

The certificates must be obtained from [FINA](https://www.fina.hr/fiskalizacija).

1. DEMO certificates

    Fill in the request form
    [Zahtjev za izdavanje Demo certifikata za fiskalizaciju](https://www.fina.hr/documents/52450/155573/7+Zahtjev+za+RDC_fiskalizacija+-+Demo_06092018.pdf/8c70682a-bd32-c32f-84f0-ce0441dba8ca)
    (PDF). You can send the request form  via email (alongside scans of your
    identity card), or file the request in person at any FINA office.

    The DEMO certificate is free.

2. Production certificates

    If you haven't already, you'll first need to register your company in FINA's
    PKI database. This will cost you about €10 (one-time fee) and you'll need to show
    [a few company registration documents](https://www.fina.hr/fiskalizacija#kako-do-certifikata).

    You'll also need to fill in
    [Zahtjev za izdavanje produkcijskog certifikata za fiskalizaciju](https://www.fina.hr/documents/52450/155573/ZahtjevCertFiskal.pdf/5a1b5509-378c-fb1f-ff7e-c95091dd2863?t=1600774713433) (one copy) and
    [Ugovor o obavljanju usluga certificiranja](https://rdc.fina.hr/obrasci/RDC-ugovor1.pdf)
    (two copies).

    The production certificate costs around €40 and is valid for 5 years.


FINA CERTIFICATES
=================


This module has the following certificates included, and used automaticly

Fina Server demo certifikati: https://www.fina.hr/fina-demo-ca-certifikati

- DEMO ROOT CA - https://demo-pki.fina.hr/certifikati/demo2014_root_ca.pem
- DEMO 2014 - https://demo-pki.fina.hr/certifikati/demo2014_sub_ca.pem
- DEMO 2020 - https://demo-pki.fina.hr/certifikati/demo2020_sub_ca.pem

Fina PROD certifikati: https://www.fina.hr/ca-fina-root-certifikati

- Root CA - https://rdc.fina.hr/Root/FinaRootCA.pem
- RDC 2020 - https://rdc.fina.hr/RDC2020/FinaRDCCA2020.pem
- RDC 2015 - https://rdc.fina.hr/RDC2015/FinaRDCCA2015.pem

- FINA - https://www.porezna-uprava.hr/HR_Fiskalizacija/Aktualnosti%20dokumenti/Certifikati/FinaRoot.zip
- PU-2022-09-23 - https://www.porezna-uprava.hr/HR_Fiskalizacija/Aktualnosti%20dokumenti/Certifikati/fiskalcis_23_09_2022.zip
- PU-2022-04-07 -  https://www.porezna-uprava.hr/HR_Fiskalizacija/Aktualnosti%20dokumenti/Certifikati/cis.porezna-uprava.hr_2022.zip
- PU-2020-10-01 - https://www.porezna-uprava.hr/HR_Fiskalizacija/Documents/Fiskalcis2020_10_1.zip
