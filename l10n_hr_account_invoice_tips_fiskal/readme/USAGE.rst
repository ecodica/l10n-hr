In the tab for Invoice tips will also be a button to Fiskalize invoice tip.
To be able to fiskalize invoice, the following conditions must be set: Invoice must have ZKI set, the Tip Amount must be set, and Tip Payment Method should be set. Note that Bank transfers are not fiskalized if not otherwise defined by the company.
Also, new field, Tip Is Fiskalized is visible. If true, then the invoice is successfully fiskalized and the button to Fiskalize the tip will be invisible. When Tip is fiskalized, Tip amount and Tip Payment Method cannot be changed.
Under Tip fields is added a list of Fiskalization messages and their status.

.. image:: ./l10n_hr_account_invoice_tips_fiskal/static/description/2.png
   :width: 1000px
   :align: center

When Tip is fiskalized, button Fiskalize Refund will be visible. If the user clicks on the button, it will call Tip fiskalization with a negative Tip Amount.
Also, when an invoice refund is created and the tip on the refund is fiskalized, it will be fiskalized with a negative amount.
After refund fiskalization, Tip Refund Is Fiskalized will be set to true, and it will be visible under the field Tip Is Fiskalized.
When Tip is refunded and then the user creates a credit note of invoice, Tip Amount on credit note will be 0.0.

.. image:: ./l10n_hr_account_invoice_tips_fiskal/static/description/3.png
   :width: 1000px
   :align: center

The module also extends the Tips Report. It adds new fields to the report wizard: Only Fiscalized Tips (default 'False') and Only Fiscalized Invoices (default 'True').
Only Fiscalized Tips filters only invoices that have fiscalized tips.
Only Fiscalized Invoices shows only invoices that have ZKI set (are fiscalized).
It also adds a new column to the report: ZKI.

.. image:: ./l10n_hr_account_invoice_tips_fiskal/static/description/4.png
   :width: 1000px
   :align: center
