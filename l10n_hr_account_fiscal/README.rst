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

Naknade (fees reported alongside the taxes)

- ``test_naknada_carries_its_values`` - a tax of fiscal type ``Naknade`` reports
  its own name and amount. ``_prepare_fisc_taxes`` unpacked the dict as a
  2-tuple (``naziv, iznos = nak``), which yields its *keys*, so every such fee
  went out as the literal strings ``NazivN``/``IznosN``. Only bites where a fee
  tax is configured - a packaging fee, say - which is plausible in retail.

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

tests/test_fiscal_mixin_hooks.py
--------------------------------

The seams that let a second model inherit ``l10n_hr.fiscal.v1.mixin``.

The mixin had exactly one consumer, ``account.move``, and about half of it read
``account.move`` fields directly - ``line_ids``, ``display_type``,
``amount_untaxed_signed``, ``invoice_user_id``. Those bodies moved down onto
``account.move`` so ``pos.order`` can become the second consumer; the mixin kept
hooks in their place. These tests pin the seams, not the message - what the
message contains is ``test_fiscal_tax_values.py``, which did not change.

- ``test_tax_values_hook_is_required`` - ``_get_fisc_tax_values()`` raises
  ``NotImplementedError`` on the bare mixin. There is no sane default: an
  invoice reads its ``display_type == 'tax'`` journal items, a POS order
  computes the breakdown from its lines. Returning an empty breakdown instead
  would produce a message FINA accepts and an inspection rejects.
- ``test_account_move_still_answers_the_tax_hook`` - the moved body is reachable
  on ``account.move`` and is not the mixin's raising stub.
- ``test_validate_hook_defaults_to_a_no_op`` - unlike the tax hook,
  ``_validate_fiscal_invoice()`` has a safe default. Its checks compare the
  message against the document's own tax lines, which not every model has; a
  model without them is unchecked, not wrong.
- ``test_default_fiscal_user_prefers_the_salesperson`` /
  ``..._falls_back_to_the_acting_user`` - ``OibOper`` must identify the natural
  person who issued the document. ``account.move`` answers ``invoice_user_id``,
  falling back to the acting user, which is what ``fiscalize()`` hard-coded
  before the hook existed.
- ``test_dead_date_time_helper_is_gone`` - ``_prepare_fiscal_date_time()`` read
  ``l10n_hr_vrijeme_izdavanja``, a field that no longer exists anywhere. It was
  never called, so it could not fail loudly; the guard stops it coming back.

tests/test_fiscal_timezone.py
-----------------------------

Fiscal timestamps belong to the business premise, not to the logged-in user.

- ``test_fiscal_time_ignores_the_user_timezone`` - two users in different
  timezones must stamp the same instant identically.
  ``get_l10n_hr_time_formatted()`` followed ``self.env.tz``, so ``DatVrijeme``
  - and therefore the ZKI signed over it - moved with whoever was logged in. An
  inspection recomputes the ZKI from the printed document, so a shifted
  timestamp can never be reproduced. Now pinned to ``Europe/Zagreb``, which is
  what the note at the top of ``account_move.py`` always said it should be.

tests/test_fiscal_response_verification.py
------------------------------------------

The FINA response verifier reports its verdict, and never raises.

Verification was a no-op in three separate places: ``Verifier.verify_document``
swallowed every exception, ``BinaryVerifier.verify_document`` returned a verdict
nobody read, and the zeep plugin's ``ingress`` caught what was left and printed
it. Nothing could fail - which is why both bundled service certificates expired
in 2024 without anyone noticing. Until this was fixed, TLS was the only
integrity control on an inbound JIR.

- ``test_expired_pin_is_reported`` - an expired pinned service certificate is
  logged as an error. xmlsec verifies against the key it is handed and will not
  mention that the certificate behind it lapsed, so a stale pin quietly stops
  meaning anything. The certificate is generated in the test rather than read
  from ``fina_cert/``: the bundled ones are meant to be refreshed, and a test
  that fails when somebody does the right thing trains people to ignore it.
- ``test_a_current_pin_is_not_reported`` - the other half, and the one that
  keeps the check honest: a valid pin must stay silent, or the warning becomes
  noise nobody reads. Runs against the bundled demo certificate.
- ``test_unparseable_pin_is_reported_but_tolerated`` - a certificate that will
  not parse is a warning, not a crash.
- ``test_missing_signature_returns_false_instead_of_raising`` - an unsigned or
  malformed response is a failed verification, not an exception. Raising would
  abort a transaction in which FINA has already issued a JIR, losing a document
  the tax authority considers issued. This caught a real defect in the fix:
  ``register_id()`` raises "missing attribute" on a payload without an ``Id``,
  before the signature check was reached, so the method could still throw.
- ``test_plugin_records_the_verdict`` - the outcome survives the call on
  ``EnvelopedSignaturePlugin.last_verification_ok``, where
  ``res.company._get_log_vals`` picks it up. Without this the verdict reaches
  only the server log, and a failed verification never appears next to the
  message it belongs to in ``l10n_hr.fiscal.log``.
- ``test_plugin_survives_a_verifier_that_raises`` - defence in depth: if
  ``verify_document`` ever does raise, the response is still unverified and the
  transaction must still survive.

``TestFiscalLogProcessTime`` - the duration recorded next to each message has to
be a real duration. It is the only continuous measurement of the FINA
round-trip, so it decides whether a synchronous call is viable at POS volumes.

- ``test_sub_millisecond_is_not_overstated`` - ``timedelta.microseconds`` is not
  zero-padded, so 112 us was stored as ``"0.112 s"`` and read as 112 ms, a
  thousandfold overstatement.
- ``test_a_normal_call_round_trips`` - 2.5 s in, 2.5 s out.
- ``test_a_negative_interval_does_not_wrap`` - ``timedelta.seconds`` excludes
  ``.days``, so -2.237 s was stored as ``"86397.763 s"``. ``total_seconds()``
  has neither problem.

``TestFiscalLogVerificationWarning`` - a failed verification has to reach
``l10n_hr.fiscal.log``, not only the server log.

- ``test_warning_survives_a_failed_response`` /
  ``..._a_delayed_response`` - the warning used to be written into
  ``error_msg`` *before* the response branching, and the error and delay
  branches overwrote it wholesale, so it survived only when the response was
  otherwise a success. That is backwards: an unverified signature matters most
  when the response was also an error, which is exactly when a forged or
  corrupted reply is most plausible. Both assert the original message and the
  warning end up in ``error_msg``.
- ``test_no_warning_when_verification_passed`` - counter-test; a passing
  verification must add nothing.

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
