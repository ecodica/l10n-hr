In the menu *Accounting > Configuration > Management > Payment Methods*,
select the payment method that has the code *sepa_credit_transfer_hr* and
set the *PAIN Version* to *scthr:pain.001.001.03 (credit transfer in Croatia)*.

To use SEPA Instant Credit Transfer (SCT Inst):

#. In *Accounting > Configuration > Journals*, open your bank journal and add
   *SEPA Instant Credit Transfer to suppliers v09HR* on the *Outgoing Payments* tab.
#. In *Accounting > Configuration > Management > Payment Modes*, create a mode for
   that payment method and set *Payment Execution Date* to *Now* - an instant transfer
   must not carry a future ``ReqdExctnDt``.

The debtor needs a Croatian IBAN, a city and a country (the scheme mandates a
structured postal address) and an OIB in the company's *Company ID* field.
