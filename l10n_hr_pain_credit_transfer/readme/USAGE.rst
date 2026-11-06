This module doesn't modify the standard usage of the modules
*account_payment_order* and *account_banking_sepa_credit_transfer*.

One exception: with the SEPA Instant payment method the *Local Instrument* field on
the payment lines is ignored and forced to *INST*, because the instant scheme applies
to the whole file rather than to individual payment groups.
