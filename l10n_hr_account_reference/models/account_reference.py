##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Author: Goran Kliska
#    Copyright (C) 2011 Slobodni programi d.o.o., Zagreb
#                  2025 Ecodica d.o.o., Zagreb
#                  https://www.ecodica.eu
#    Contributions: Mihael Cindori, Ecodica d.o.o.
#    Documentation: https://www.fina.hr/ngsite/content/download/8558/152088/1
#    Note: Methods for computing all Croatian payment reference models are
#          implemented in this module. However, only a few of them are
#          allowed to use (HR00, HR01, HR02, HR03, HR06). The rest of them
#          may be implemented on demand if needed.
#
##############################################################################

import re

"""
    Validates Croatian payment reference based on model (1-3 parts).
    - Parts: 1 to 3, separated by '-'
    - Content: Digits only
    - Part Length: 1-12 digits per part
    - Total Length: Max 22 characters (including hyphens)
"""
REGEX_PATTERNS = {
    "HR00": r"^(?=.{1,22}$)\d{1,12}(?:-\d{1,12}){0,3}$",
    "HR01": r"^(?=.{1,22}$)\d{1,12}(?:-\d{1,12}){0,3}$",
    "HR02": r"^(?=.{1,22}$)\d{1,12}(?:-\d{1,12}){0,3}$",
    "HR03": r"^(?=.{1,22}$)\d{1,12}(?:-\d{1,12}){0,3}$",
    "HR04": r"^(?=.{1,22}$)\d{1,12}(?:-\d{1,12}){0,3}$",
    "HR06": r"^(?=.{1,22}$)\d{1,12}(?:-\d{1,12}){0,3}$",
}
# 1.   = V-variable length, mandatory
#      = v-variable length, optional
#      = F-fixed length, mandatory
#      = f-fixed length, optional
# 2-3. = max length
# 4.   = K - control number
#      = k - control number if right one does not exists
#      = n - No control number
# e.g. v12K - optional variable with maximum 12 digits in length and control number at the end
#      V12n - mandatory variable with maximum 12 digits in length and no control number at the end
MODELS_LENGTH = {
    "HR00": ("V12n", "v12n", "v12n", "n00n"),
    "HR01": ("V12k", "v12k", "v12K", "n00n"),
    "HR02": ("V12n", "v12K", "v12K", "n00n"),
    "HR03": ("V12K", "v12K", "v12K", "n00n"),
    "HR04": ("V12K", "V12n", "v12K", "n00n"),
    "HR06": ("V12n", "V12k", "v12K", "n00n"),
}


def mod11ini(value):
    """
        Compute mod11ini
    """
    length = len(value)
    sum = 0
    for i in range(0, length):
        sum += int(value[length - i - 1]) * (i + 2)
    res = sum % 11
    if res > 1:
        res = 11 - res
    else:
        res = 0
    return str(res)

def iso7064(value):
    """
        Compute ISO 7064, Mod 11,10
    """
    t = 10
    for i in value:
        c = int(i)
        t = (2 * ((t + c) % 10 or 10)) % 11
    return str((11 - t) % 10)


def mod11p7(value):
    length = len(value)
    sum = 0
    for i in range(0, length):
        sum += int(value[length - i - 1]) * ((i % 6) + 2)
    res = sum % 11
    if res == 0:
        return "5"
    elif res == 1:
        return "0"
    else:
        return str(11 - res)

def mod10zb(value):
    l = len(value)
    res = 0
    for i in range(0, l):
        res += int(value[l - i - 1]) * (i % 2 + 1)
    return str(res % 10)


def mod10(value):
    l = len(value)
    res = 0
    for i in range(0, l):
        num = int(value[l - i - 1]) * (((i + 1) % 2) + 1)
        res += num / 10 + num % 10
    res = res % 10
    if res == 0:
        return "0"
    else:
        return str(10 - res)

def mod11(value):
    l = len(value)
    res = 0
    for i in range(0, l):
        res += int(value[l - i - 1]) * (i % 6 + 2)
    res = res % 11
    if res > 1:
        return str(11 - res)
    else:
        return "0"

def reference_number_get(model=None, p1="", p2="", p3="", p4=""):
    if not model:
        model = ""
    if model in MODELS_LENGTH.keys():
        validate_p_lengths(model, p1, p2, p3, p4)
    if model == "HR01":
        res = "-".join((p1, p2, p3 + mod11ini(p1 + p2 + p3)))
    elif model == "HR02":
        res = "-".join((p1, p2 + mod11ini(p2), p3 + mod11ini(p3)))
    elif model == "HR03":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2), p3 + mod11ini(p3)))
    elif model == "HR04":
        res = "-".join((p1 + mod11ini(p1), p2, p3 + mod11ini(p3)))
    elif model == "HR05":
        res = "-".join((p1 + mod11ini(p1), p2, p3))
    elif model == "HR06":
        res = "-".join((p1, p2, p3 + mod11ini(p2 + p3)))
    elif model == "HR07":
        res = "-".join((p1, p2 + mod11ini(p2), p3))
    elif model == "HR08":
        res = "-".join((p1, p2 + mod11ini(p1 + p2), p3 + mod11ini(p3)))
    elif model == "HR09":
        res = "-".join((p1, p2 + mod11ini(p1 + p2), p3))
    elif model == "HR10":
        res = "-".join((p1 + mod11ini(p1), p2, p3 + mod11ini(p2 + p3)))
    elif model == "HR11":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2), p3))
    elif model == "HR13":
        res = "-".join((p1 + mod11p7(p1), p2, p3))
    elif model == "HR14":
        res = "-".join((p1 + mod10zb(p1), p2, p3))
    elif model == "HR15":
        res = "-".join((p1 + mod10(p1), p2 + mod10(p2)))
    elif model == "HR16":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2), p3))
    elif model == "HR17":
        res = "-".join((p1 + iso7064(p1), p2, p3))
    elif model == "HR18":
        res = "-".join((p1 + mod11p7(p1), p2, p3))
    elif model == "HR21":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2), p3))
    elif model == "HR23":
        res = "-".join((p1 + mod11ini(p1), p2, p3, p4))
    elif model == "HR24":
        res = "-".join((p1 + mod11ini(p1), p2, p3, p4))
    elif model == "HR26":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2), p3 + mod11ini(p3), p4))
    elif model == "HR27":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2)))
    elif model == "HR28":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2), p3 + mod11ini(p3), p4))
    elif model == "HR29":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2), p3 + mod11ini(p3)))
    elif model == "HR31":
        res = "-".join((p1 + iso7064(p1), p2, p3, p4))
    elif model == "HR33":
        res = "-".join((p1 + iso7064(p1), p2 + iso7064(p2), p3))
    elif model == "HR34":
        res = "-".join((p1 + iso7064(p1), p2 + iso7064(p2), p3 + iso7064(p3)))
    elif model == "HR40":
        res = "-".join((p1 + mod10(p1), p2, p3))
    elif model == "HR43":
        res = "-".join((p1, p2 + mod11ini(p2), p3, p4))
    elif model == "HR55":
        res = "-".join((p1 + mod11ini(p1), p2, p3))
    elif model == "HR62":
        res = "-".join((p1 + mod11ini(p1), p2 + iso7064(p2), p3 + mod11ini(p3), p4))
    elif model == "HR63":
        res = "-".join((p1 + mod11ini(p1), p2 + iso7064(p2), p3 + mod11ini(p3)))
    elif model == "HR64":
        res = "-".join((p1 + mod11ini(p1), p2 + iso7064(p2), p3, p4))
    elif model == "HR65":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2), p3 + iso7064(p3), p4))
    elif model == "HR66":
        res = "-".join((p1, p2[:7] + mod11ini(p2[:7]) + p2[7:], p3))
    elif model == "HR83":
        res = "-".join((p1 + mod11ini(p1), p2, p3))
    elif model == "HR84":
        if len(p2) == 4:
            res = "-".join((p1 + mod11ini(p1), p2, p3))
        else:
            res = "-".join((p1 + mod11ini(p1), p2))
    else:
        res = p1 + "-" + p2 + "-" + p3 + "-" + p4

    res.strip("-")
    res = res.strip("-").replace("---", "-").replace("--", "-")
    
    # Validating only those payment references generated for models that are 
    # currently implemented
    if model in REGEX_PATTERNS.keys():
        if not is_valid(model, res):
            return ""

    return res

def get_only_numeric_chars(ref):
    # take out non numeric chars!
    return (ref and "".join([r for r in ref if r.isdigit()]) or "") 
    
def validate_p_lengths(model, *ps):
    """
        Validate length of payment reference parts.
        - model: Payment reference model
        - ps: Parts of the payment reference
    """
    i = 0
    if len(ps) > 4:
        ps = ps[:4]
    for p in ps:
        model_rules = MODELS_LENGTH.get(model)
        if not model_rules:
            break
        if model_rules[i][0] in ('f', 'F') and \
            model_rules[i][-1] in ('k', 'K'):
            if len(p) != int(model_rules[i][1:3]) - 1:
                max_trim = int(model_rules[i][1:3]) - 1
                p = p[:max_trim]
        elif model_rules[i][0] in ('f', 'F') and \
            model_rules[i][-1] not in ('k', 'K'):
            if len(p) != int(model_rules[i][1:3]):
                max_trim = int(model_rules[i][1:3])
                p = p[:max_trim]
        elif model_rules[i][0] in ('v', 'V') and \
            model_rules[i][-1] in ('k', 'K'):
            if len(p) > int(model_rules[i][1:3]) - 1:
                max_trim = int(model_rules[i][1:3]) - 1
                p = p[:max_trim]
        elif model_rules[i][0] in ('v', 'V') and \
            model_rules[i][-1] not in ('k', 'K'):
            if len(p) > int(model_rules[i][1:3]):
                p = p[:int(model_rules[i][1:3])]
        i += 1

def is_valid(model, ref_string):
    """
        Check if generated payment reference is valid.
    """
    pattern = REGEX_PATTERNS.get(model) or ""
    match = re.match(pattern, ref_string)
    
    if match:
        return True
    
    return False
