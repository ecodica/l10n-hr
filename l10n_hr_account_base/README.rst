===============================
Croatia accounting localisation
===============================

.. |badge1| image:: https://img.shields.io/badge/licence-LGPL--3-blue.png
    :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3

|badge1|

This module is base accounting localisation for Croatia
Primary target is to adjust odoo journals to Croatia out invoice fiskal rules
according to : https://www.zakon.hr/z/548/Zakon-o-fiskalizaciji-u-prometu-gotovinom
This module manages Invoicing related data: Journals and Invoice sequence
automaticly according to localisation needs
All out invoices in Croatia has strictly defined out invoice fiscal number structure/forming rules.

All croatia legaly required fields are added to standard printout for report invoice.

Important rules:

- Invoice number consists of 3 parts:

  - AA - invoice number - strictly NO preceeding zeroes
  - BB - Business premisse code - alphanumerical chars
  - CC - PoS device code - strictly integer

Configuration
=============

Company settings (menuitem: Settings -> Users and Companies -> Companies ):

  * Select taxation model

   - R1 - taxation based on invoice (default)
   - R2 - taxation based on payment
   - R0 - not subject to taxation

  * Choose fiskal invoice separator

   - only "/" and "-" are allowed, "/" is default


Accounting settings (menuitem : Invoicing >> Configuration >> Croatia specific settings >> Business premises):

  * Create business premisse
    The code of premise should be the middle part of your invoices,
    and should match your internal document defining it.
    Field 'Mjesto izdavanja' can be populated on PoS device level, or on the Business premisse level.
    It is legally required info, and will be printed as such on invoices, respecting the order Pos-Premise.
    Should contain something.

  * Define invoice sequencing for premise

    Based on premise or based on PoS device level. Each premise may have different settings.

  * Add Pos Device

    Name of device if informational, and may be set free, but code should be strictly numeric.


Activate PoS device and Business premise:

    Activating and deactivating Business premise and/or PoS device is automated with
    related journals and sequences create/modify. It is not required to select any values in
    journal or sequence fields before activating object, as they will be automaticly populated.
    Also, if you know what you are doing it is possible to connect multiple journals to
    one pos device (different journals for cash, card or transfer acc, using one pos device ž
    and related invoice sequence)
    If no journal is assigned for PoS device, one will be created on activating.

    In order to confirm invoice, PoS device and Business premise must be present,
    setup and activated.
