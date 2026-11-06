This module adds support for the ISO 20022 credit transfer schemes used in Croatia
(SEPA or not SEPA):

* *scthr:pain.001.001.03*
* *scthr:pain.001.001.09*
* *sctinsthr:pain.001.001.09* - SEPA Instant Credit Transfer (SCT Inst), executed in
  real time 24/7/365. It is a separate scheme with its own XML namespace, not a
  variant of *scthr:pain.001.001.09*: every payment group is flagged with
  ``SvcLvl/Cd = SEPA`` and ``LclInstrm/Cd = INST``.
