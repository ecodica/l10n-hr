##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Author: Goran Kliska
#    Copyright (C) 2011- Slobodni programi d.o.o., Zagreb
#                http://www.slobodni-programi.hr
#    Contributions:
#    Documentation: http://www.fina.hr/Default.aspx?sec=1266
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

# import logging


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
    ### if 1.st digit differs from three - ERROR
    # if not return_check_digit and int(value[0]) != 3:
    #    return False
    sum = 0
    for i in xrange(0, length):
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
    for i in xrange(0, l):
        res += int(value[l - i - 1]) * (i % 2 + 1)
    return str(res % 10)


def mod10(value):
    l = len(value)
    res = 0
    for i in xrange(0, l):
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
    for i in xrange(0, l):
        res += int(value[l - i - 1]) * (i % 6 + 2)
    res = res % 11
    if res > 1:
        return str(11 - res)
    else:
        return "0"


"""
# Test
mod11p7('3456789012') # res = '2'
mod10zb('223344556') #res='8'
mod7064('234000') #res='9'
mod11ini('33444555666') #res=9
mod10('54370395') #res=7
mod11('54370395') #res=8
"""


def reference_number_get(model=None, p1="", p2="", p3="", p4=""):

    if not model:
        model = ""  # or '99'?
    if model == "01":
        res = "-".join((p1, p2, p3 + mod11ini(p1 + p2 + p3)))
    elif model == "02":
        res = "-".join((p1, p2 + mod11ini(p2), p3 + mod11ini(p3)))
    elif model == "03":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2), p3 + mod11ini(p3)))
    elif model == "04":
        res = "-".join((p1 + mod11ini(p1), p2, p3 + mod11ini(p3)))
    elif model == "05":
        res = "-".join((p1 + mod11ini(p1), p2, p3))
    elif model == "06":
        res = "-".join((p1, p2, p3 + mod11ini(p2 + p3)))
    elif model == "07":
        res = "-".join((p1, p2 + mod11ini(p2), p3))
    elif model == "08":
        res = "-".join((p1, p2 + mod11ini(p1 + p2), p3 + mod11ini(p3)))
    elif model == "09":
        res = "-".join((p1, p2 + mod11ini(p1 + p2), p3))
    elif model == "10":
        res = "-".join((p1 + mod11ini(p1), p2, p3 + mod11ini(p2 + p3)))
    elif model == "11":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2), p3))
    elif model == "13":
        res = "-".join((p1 + mod11p7(p1), p2, p3))
    elif model == "14":
        res = "-".join((p1 + mod10zb(p1), p2, p3))
    elif model == "15":
        res = "-".join((p1 + mod10(p1), p2 + mod10(p2)))
    elif model == "16":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2), p3))
    elif model == "17":
        res = "-".join((p1 + iso7064(p1), p2, p3))
    elif model == "18":
        res = "-".join((p1 + mod11p7(p1), p2, p3))
    elif model == "21":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2), p3))
    elif model == "23":
        res = "-".join((p1 + mod11ini(p1), p2, p3, p4))
    elif model == "24":
        res = "-".join((p1 + mod11ini(p1), p2, p3, p4))
    elif model == "26":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2), p3 + mod11ini(p3), p4))
    elif model == "27":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2)))
    elif model == "28":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2), p3 + mod11ini(p3), p4))
    elif model == "29":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2), p3 + mod11ini(p3)))
    elif model == "31":
        res = "-".join((p1 + iso7064(p1), p2, p3, p4))
    elif model == "33":
        res = "-".join((p1 + iso7064(p1), p2 + iso7064(p2), p3))
    elif model == "34":
        res = "-".join((p1 + iso7064(p1), p2 + iso7064(p2), p3 + iso7064(p3)))
    elif model == "40":
        res = "-".join((p1 + mod10(p1), p2, p3))
    elif model == "43":
        res = "-".join((p1, p2 + mod11ini(p2), p3, p4))
    elif model == "55":
        res = "-".join((p1 + mod11ini(p1), p2, p3))
    elif model == "62":
        res = "-".join((p1 + mod11ini(p1), p2 + iso7064(p2), p3 + mod11ini(p3), p4))
    elif model == "63":
        res = "-".join((p1 + mod11ini(p1), p2 + iso7064(p2), p3 + mod11ini(p3)))
    elif model == "64":
        res = "-".join((p1 + mod11ini(p1), p2 + iso7064(p2), p3, p4))
    elif model == "65":
        res = "-".join((p1 + mod11ini(p1), p2 + mod11ini(p2), p3 + iso7064(p3), p4))
    elif model == "66":
        res = "-".join((p1, p2[:7] + mod11ini(p2[:7]) + p2[7:], p3))
    elif model == "83":
        res = "-".join((p1 + mod11ini(p1), p2, p3))
    elif model == "84":
        if len(p2) == 4:
            res = "-".join((p1 + mod11ini(p1), p2, p3))
        else:
            res = "-".join((p1 + mod11ini(p1), p2))
    else:  # model in ('','00',"99")
        res = p1 + "-" + p2 + "-" + p3 + "-" + p4

    res.strip("-")
    res = res.strip("-").replace("---", "-").replace("--", "-")

    return res


# 1.   = V-variable,mandatory
#      = v-variable,optional
#      = F-fixed lenght,mandatory
#      = f-fixed lenght,optional
# 2-3. =max lenght
# 4.   = K - control num
#      = k - control num if right one does not exists ???
#      = n - NO control num

MODELS_LENGHT = {
    "01": ("V12k", "v12k", "v12K", "n00n"),
    "02": ("V12n", "v12K", "v12K", "n00n"),
    "03": ("V12K", "v12K", "v12K", "n00n"),
    "12": ("F13K", "v12n", "v12n", "n00n"),
}


def get_only_numeric_chars(ref):
    return (
        ref and "".join([r for r in ref if r.isdigit()]) or ""
    )  # take out non numeric chars!


# TODO
def validate_lenghts(model, value):
    # 22 znaka , uključivo max 2 crtice, + 4 zanka za HR + model
    # max 26 znakova ! regex?
    return True


# TODO
def reference_number_valid(model="", P=""):
    # possibly validate references manualy entered on vendor bills?
    return True
