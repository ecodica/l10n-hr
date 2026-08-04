===================================
Croatia - Fiscalization of invoices
===================================

This module provides feature of legally required fiscalization process for invoices
Additional modules will be required for other types of documents.
Available official documentation is available here:
[Fiskalizacija](https://www.porezna-uprava.hr/HR_Fiskalizacija/Stranice/FiskalizacijaNovo.aspx)

Configuration
=============

1. Add fiscal certificate

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

5. Users setup

    Users confirming the invoices, must have OIB entered
    It is legaly required part of fiskal message and needs to be entered.

6. Fiscalize Invoice On Confirmation

    menuitem : Settings >> Users & Companies >> Companies >> Croatia Settings >> Fiscalize Invoice On Confirmation
    If checked, then the fiscalization service is called upon invoice confirmation. Uncheck if fiscalization should
    be called manually or with some other function/process (with CRON jobs, for example).

7. Cancel Fiscalized Invoices

    menuitem : Settings >> Users & Companies >> Companies >> Croatia Settings >> Cancel Fiscalized Invoices
    If unchecked, then users cannot cancel posted invoices or return them to draft.

8. Skip Bank Transfer Fiscalization

    menuitem : Settings >> Users & Companies >> Companies >> Croatia Settings >> Skip Bank Transfer Fiscalization
    If checked, then invoices with Bank Transfer type are not fiscalized (they won't get ZKI and JIR numbers).

9. Fiscalizaion Error Logging

    menuitem : Settings >> Users & Companies >> Companies >> Croatia Settings >> Silent Error Logging
    If checked, then Fiscalization errors are not raised, but they are written in the fiscalization log on the invoice.
    The purpose of this feature is to enable Users to create Invoices even if fiscalization doesn't work for some reason
    (for example, if users have Internet connection issues).


Usage
=====

Regular invoices will be fiskalized in the posting process automaticly (this is option on company settings, True by default).
However, if for any reason, the fiscalistion mesage is not sent , or is sent and received and error,
Late fiskalisation is possible from Croatia specific page on ivvoice form
Using the buttin FISKALIZE.

If you created an ivoice on Paragon blok. You may enter all invoice data,
including the paragon blok number, and set correct dates, then confirm the invoice.
The check box Late delivery should be marked!

If you want to check the fiskalisation data on already fiskalized invoice, (containing JIR and ZKI data)
you can press Verify fiskalization button and send a check-invoice type message (visible in message logs)


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


Unit Tests
==========

Run the whole suite with::

    odoo-bin -d <database> --test-enable --test-tags /l10n_hr_account_fiscal --stop-after-init

The tests are tagged ``post_install`` and ``-at_install``, so they need the
module installed first. ``test_systray.py`` is an ``HttpCase`` and needs a
running browser (Chromium); if the server config pins a ``dbfilter``, pass
``--db-filter=<database>`` as well or the browser lands on the database
selector instead of the web client.

tests/test_fiscal_tax_values.py
-------------------------------

Sign, currency and consistency of the amounts in the Fiskalizacija 1.0
message. The single invariant behind most of them is::

    ZKI payload amount == IznosUkupno == QR 'izn'
    sum(Pdv.Osnovica) + sum(Pdv.Iznos) + sum(Pnp.Iznos) == IznosUkupno

Sign of the taxable base (``Osnovica``)

- ``test_osnovica_positive_on_out_invoice`` - an ordinary customer invoice
  reports a positive base and tax. ``tax_base_amount`` is already signed by
  ``direction_sign``, so the base used to go out negative on every invoice.
- ``test_osnovica_negative_on_out_refund`` - a credit note keeps base, tax and
  total all negative.
- ``test_osnovica_plus_iznos_equals_iznos_ukupno`` - the breakdown adds up to
  the total, for an invoice and for a credit note.
- ``test_exempt_base_is_reported_separately`` - a 0% exempt line lands in
  ``IznosOslobPdv`` and stays out of the ``Pdv`` breakdown, while still
  counting towards the total.

One canonical amount for ZKI, ``IznosUkupno`` and the QR

- ``test_zki_amount_equals_iznos_ukupno`` - the ZKI is signed over exactly the
  amount that is submitted.
- ``test_zki_amount_is_negative_on_a_credit_note`` - the ZKI used to sign
  ``+1250.00`` while ``IznosUkupno`` went out as ``-1250.00``.
- ``test_zki_amount_is_in_company_currency`` - a foreign-currency invoice signed
  its *invoice* currency total; the amount must be the company-currency one
  that ``IznosUkupno`` has always carried.
- ``test_iznos_ukupno_matches_the_payment_term_lines`` - regression guard
  for the switch to ``amount_total_signed``: the value must not change for an
  ordinary document, in company or foreign currency.
- ``test_qr_url_carries_the_company_currency_amount`` - the verification URL's
  ``izn`` is the company-currency amount, not the invoice-currency one.
- ``test_qr_url_amount_is_signed_for_a_credit_note`` - a storno must advertise
  the negative amount it actually fiscalized. Seen in production on POS refund
  ``pos.order`` 345 / ``account.move`` 528: ZKI and ``IznosUkupno`` were both
  ``-10.13``, but the QR carried ``izn=1013``.
- ``test_qr_url_amount_matches_the_zki_and_iznos_ukupno`` - asserts all three
  amounts against each other, on the URL rather than the field, so a future
  formatting change to ``izn`` has to keep them in step.

Pre-send validation guard

- ``test_validator_accepts_consistent_invoice`` / ``..._consistent_refund`` -
  a correct payload passes in both directions.
- ``test_validator_rejects_inverted_osnovica`` - the exact payload the old sign
  bug produced must not leave the system. It matched the XSD pattern, so CIS
  accepted it silently.
- ``test_validator_rejects_understated_osnovica`` - a base that does not match
  Odoo's untaxed amount is caught. This is the shape produced when two tax
  lines share a rate and only the first base is kept.
- ``test_validator_rejects_mismatched_tax_amount`` - a tax amount that does not
  follow from the base is caught.
- ``test_validator_accepts_a_foreign_currency_invoice`` - the validator
  compared company-currency figures against invoice-currency
  ``amount_untaxed``, so it raised on every foreign-currency invoice even
  though the message was correct.
- ``test_validator_accepts_exempt_base`` - ``IznosOslobPdv`` counts towards the
  base and must not false-trigger the guard.

Endpoint configuration

- ``test_every_prod_wsdl_points_at_the_production_endpoint`` - walks every
  bundled WSDL and asserts that a ``PROD_*`` schema carries the production
  address and a test schema the test address. FINA shipped ``PROD_v1.8`` with
  the ``cistest.apis-it.hr`` address, which silently sent production traffic
  to the test service.

Fiscalization outcome and batching

- ``test_fiscalize_returns_falsy_when_not_needed`` - ``fiscalize()`` reports its
  outcome, so callers can tell "done" from "nothing to do".
- ``test_batch_fiscalize_counts_untouched_moves_as_skipped`` - the batch
  counters reflect that return value instead of swallowing it.
- ``test_batch_fiscalize_isolates_a_failing_record`` - a DB error on one record
  must not poison the rest of the batch. Without the per-record savepoint the
  aborted cursor makes every following record fail with "current transaction is
  aborted", giving counters of ``(1, 0, 2)`` instead of ``(2, 0, 1)``. Also
  asserts the swallowed exception is logged with its traceback.

Systray counter endpoint

- ``test_counter_is_scoped_to_the_enabled_companies`` -
  ``search_not_fiscalized_invoice_count`` is publicly callable via ``call_kw``,
  so it must not trust the client. It used to ``sudo()`` and filter on whatever
  ``company_id`` the browser sent, letting any user read another company's
  unfiscalized-invoice count; it now takes no arguments and derives the scope
  from ``env.companies``.

tests/test_systray.py
---------------------

Browser test for the not-fiscalized-invoices systray. These failures are all
client-side and none of them can be caught by a Python test, so the test
renders the actual web client.

- ``test_systray_badge_renders_and_menu_opens`` - creates one posted invoice
  with a ZKI and no JIR, then asserts the systray icon renders, the red badge
  next to it reads ``1``, and clicking it opens a dropdown containing the
  "Not Fiscalized Invoices" item. This covers the component guarding on
  ``this.isAlive`` (which does not exist in OWL 2, so the counter fetch always
  returned early and the badge stayed at 0) and the template using the Odoo
  <=16 ``toggler`` slot (Odoo 19's ``Dropdown`` has ``{default, content}``
  only, so the icon never rendered and ``Dropdown`` raised "Could not find a
  valid dropdown toggler").
