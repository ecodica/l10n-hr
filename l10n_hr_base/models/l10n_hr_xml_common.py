import os
import uuid
from lxml import etree, objectify

from odoo import _, models
from odoo.exceptions import ValidationError


class L10nHrCroatiaXMLMixin(models.AbstractModel):
    _name = "l10n_hr.xml.mixin"
    _description = "Abstract class for handling XML in Croatia"
    """
        Abstract model containing common xml methods for all sorts of XML reports,
        so no need to import etree, objectify and such modules everywhere.
    """

    def l10n_hr_check_valid_phone(self, phone):
        """
            For the VAT form (PDV obrazac):
            The phone number must start with a '+' sign, followed by 8 to 13 
            digits (e.g., +38514445555).
        """
        if not phone:
            return False
        for r in [" ", "/", ".", ",", "(", ")"]:
            phone = phone.replace(r, "")
        if phone.startswith("00"):
            phone = "+" + phone[2:]
        if not phone.startswith("+") and phone.startswith("385"):
            phone = "+" + phone
        if 14 < len(phone) < 7 or not phone.startswith("+385"):
            raise ValidationError(_('Phone %s not valid! Phone should start with "+385".') % phone)
        return phone

    def l10n_hr_get_company_data(self):
        if not self._fields.get("company_id"):
            raise ValidationError(
                _("The model does not have a company_id field.")
            )
        company = self.company_id
        err = ""
        if not company.partner_id.city:
            err += "The city is missing in the entry.\n"
        if not company.partner_id.street:
            err += "The street is missing in the address.\n"
        if not company.partner_id.company_registry:  
            err += "Missing VAT number (OIB).\n"
        if err != "":
            raise ValidationError(err)

    def l10n_hr_get_xml_metadata(self, xml_naslov, xml_autor, xml_conforms):
        """
            Used n : JOPPD, ...
            :return: XML common metadata object for all xml-s defined by Institutions
        """
        MD = self._l10n_hr_get_elementmaker(
            namespace="http://e-porezna.porezna-uprava.hr/sheme/Metapodaci/v2-0")
        identifier = uuid.uuid4()
        date_time = self.company_id.get_l10n_hr_time_formatted()["datum_meta"]
        meta = MD.Metapodaci(
            MD.Naslov(xml_naslov, dc="http://purl.org/dc/elements/1.1/title"),
            MD.Autor(xml_autor, dc="http://purl.org/dc/elements/1.1/creator"),
            MD.Datum(date_time, dc="http://purl.org/dc/elements/1.1/date"),
            MD.Format("text/xml", dc="http://purl.org/dc/elements/1.1/format"),
            MD.Jezik("hr-HR", dc="http://purl.org/dc/elements/1.1/language"),
            MD.Identifikator(
                identifier, dc="http://purl.org/dc/elements/1.1/identifier"
            ),
            MD.Uskladjenost(xml_conforms, dc="http://purl.org/dc/terms/conformsTo"),
            MD.Tip("Elektronički obrazac", dc="http://purl.org/dc/elements/1.1/type"),
            MD.Adresant("Ministarstvo Financija, Porezna uprava, Zagreb"),
        )
        return meta, identifier

    def _l10n_hr_get_elementmaker(self, annotate=False, namespace=False):
        """
            :param annotate:
            :param namespace:
            :return: simply remove annotations from xml object
        """
        return objectify.ElementMaker(annotate=annotate, namespace=namespace)

    def l10n_hr_get_xml_string(self, xml_object, deannotate=False, pretty=False, 
                       encoding="unicode", replace=False):
        """
            :param xml_object: etree xml object
            :param deannotate: True to remove annotations
            :param pretty: pretty_print
            :param encoding:
            :param replace: list of tuples to replace in xlm string
            :return: xml string
        """
        if deannotate:
            objectify.deannotate(xml_object)
        string = etree.tostring(xml_object, pretty_print=pretty, encoding=encoding)
        if replace:
            for r1, r2 in replace:
                string = string.replace(r1, r2)
        return string

    def l10n_hr_validate_xml(self, xml_string, xsd_path, xsd_file):
        """
            :param xml_string:
            :param xsd_path: absolute path to schema folder (put schema folders in module)
            :param xsd_file: xsd file name for validating
            :return: False or Error description if error occurs
        """
        os.chdir(xsd_path)
        xml_schema = etree.XMLSchema(etree.parse(os.path.join(xsd_path, xsd_file)))
        try:
            xml_schema.validate(etree.XML(xml_string))
        except AssertionError as E:
            return E[0]
        except Exception as E:
            return E
        return False
