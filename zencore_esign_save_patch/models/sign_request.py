# -*- coding: utf-8 -*-

import base64
import binascii
import io
import logging

from odoo import fields, models
from odoo.tools.pdf import (
    BooleanObject,
    NameObject,
    PdfFileReader,
    PdfFileWriter,
    createStringObject,
)

_logger = logging.getLogger(__name__)


class SignRequest(models.Model):
    _inherit = "sign.request"

    x_zencore_pdf_form_values = fields.Json(copy=False, readonly=True)
    x_zencore_pdf_form_filled_pdf = fields.Binary(
        copy=False,
        readonly=True,
        attachment=True,
    )

    def _generate_completed_document(self, password=""):
        self.ensure_one()
        result = super()._generate_completed_document(password=password)

        # Odoo's Sign generator builds a fresh PDF for the completed document.
        # That process drops the original AcroForm tree, even when the input PDF
        # contains values saved by PDF.js. Keep the saved native PDF as the base
        # layer and merge Odoo's signature/text overlay onto it instead.
        if not self._zencore_merge_native_form_into_completed_document():
            self._zencore_apply_pdf_form_values_to_completed_document()
        return result

    def _zencore_merge_native_form_into_completed_document(self):
        self.ensure_one()
        native_pdf = self.x_zencore_pdf_form_filled_pdf
        if not native_pdf or not self.completed_document:
            return False

        try:
            native_reader = PdfFileReader(
                io.BytesIO(base64.b64decode(native_pdf)),
                strict=False,
            )
            completed_reader = PdfFileReader(
                io.BytesIO(base64.b64decode(self.completed_document)),
                strict=False,
            )
            if native_reader.getNumPages() != completed_reader.getNumPages():
                _logger.warning(
                    "Cannot merge native PDF form data for Sign request %s: page counts differ.",
                    self.id,
                )
                return False

            writer = PdfFileWriter()
            writer.cloneDocumentFromReader(native_reader)
            for page_index in range(writer.getNumPages()):
                writer.getPage(page_index).mergePage(completed_reader.getPage(page_index))
            # Some PDF readers do not paint an existing comb-field appearance
            # when it contains a single character. Ask the reader to regenerate
            # appearances from the preserved AcroForm values.
            self._zencore_set_need_appearances(writer)

            with io.BytesIO() as output:
                writer.write(output)
                self._zencore_replace_completed_document(base64.b64encode(output.getvalue()))
            return True
        except Exception:
            _logger.exception(
                "Could not preserve native PDF form data in the completed Sign document."
            )
            return False

    def _zencore_replace_completed_document(self, document):
        self.ensure_one()
        self.completed_document = document
        document_attachment = self.completed_document_attachment_ids.filtered(
            lambda attachment: not attachment.name.startswith("Certificate of completion")
        )[:1]
        if document_attachment:
            document_attachment.sudo().write({"datas": document})

    def _zencore_apply_pdf_form_values_to_completed_document(self):
        self.ensure_one()
        values = (self.x_zencore_pdf_form_values or {}).get("fields") or []
        if not self.completed_document or not values:
            return

        try:
            patched_document = self._zencore_fill_pdf_form_fields(self.completed_document, values)
        except Exception:
            _logger.exception("Could not apply native PDF form values to completed Sign document.")
            return

        if not patched_document or patched_document == self.completed_document:
            return

        self._zencore_replace_completed_document(patched_document)

    def _zencore_fill_pdf_form_fields(self, pdf_document, fields_payload):
        form_values = self._zencore_pdf_form_mapping(fields_payload)
        if not form_values:
            return pdf_document

        reader = PdfFileReader(io.BytesIO(base64.b64decode(pdf_document)), strict=False)
        writer = PdfFileWriter()
        for page_index in range(reader.getNumPages()):
            writer.addPage(reader.getPage(page_index))

        self._zencore_set_need_appearances(writer)
        for page_index in range(writer.getNumPages()):
            page = writer.getPage(page_index)
            for annotation_ref in page.get("/Annots", []):
                annotation = annotation_ref.getObject()
                field_name = self._zencore_pdf_field_name(annotation)
                if not field_name or field_name not in form_values:
                    continue
                field_type = self._zencore_pdf_inherited_value(annotation, "/FT")
                value = form_values[field_name]
                if field_type == "/Btn":
                    self._zencore_update_button_field(annotation, value)
                else:
                    self._zencore_update_text_field(annotation, value)

        with io.BytesIO() as output:
            writer.write(output)
            return base64.b64encode(output.getvalue())

    def _zencore_pdf_form_mapping(self, fields_payload):
        form_values = {}
        for field in fields_payload:
            name = str(field.get("name") or "").strip()
            if not name:
                continue

            field_type = str(field.get("type") or "").lower()
            if field_type in {"checkbox", "radio"}:
                if field.get("checked"):
                    form_values[name] = field.get("exportValue") or field.get("value") or "Yes"
                elif name not in form_values:
                    form_values[name] = "Off"
                continue

            value = field.get("value")
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value if item not in (None, False))
            if value not in (None, False, ""):
                form_values[name] = value
        return form_values

    def _zencore_set_need_appearances(self, writer):
        if hasattr(writer, "set_need_appearances_writer"):
            writer.set_need_appearances_writer()
            return
        catalog = writer._root_object
        if "/AcroForm" in catalog:
            catalog["/AcroForm"][NameObject("/NeedAppearances")] = BooleanObject(True)

    def _zencore_pdf_field_name(self, annotation):
        value = self._zencore_pdf_inherited_value(annotation, "/T")
        return str(value) if value else False

    def _zencore_pdf_inherited_value(self, annotation, key):
        current = annotation
        while current:
            if key in current:
                return current.get(key)
            parent = current.get("/Parent")
            current = parent.getObject() if parent else False
        return False

    def _zencore_update_button_field(self, annotation, value):
        value_name = str(value or "Off")
        if value_name != "Off" and not value_name.startswith("/"):
            value_name = f"/{value_name}"
        if value_name == "/Off":
            value_name = "Off"
        pdf_name = NameObject("/Off" if value_name == "Off" else value_name)
        annotation.update({
            NameObject("/V"): pdf_name,
            NameObject("/AS"): pdf_name,
        })
        parent = annotation.get("/Parent")
        if parent:
            parent.getObject().update({NameObject("/V"): pdf_name})

    def _zencore_update_text_field(self, annotation, value):
        pdf_value = createStringObject(str(value))
        annotation.update({NameObject("/V"): pdf_value})
        parent = annotation.get("/Parent")
        if parent:
            parent.getObject().update({NameObject("/V"): pdf_value})


class SignRequestItem(models.Model):
    _inherit = "sign.request.item"

    def _fill(self, signature, **kwargs):
        result = super()._fill(signature, **kwargs)
        self._zencore_save_pdf_form_payload(kwargs)
        return result

    def _zencore_save_pdf_form_payload(self, kwargs):
        fields_payload = self._zencore_normalize_pdf_form_fields(kwargs.get("pdf_form_values"))
        filled_pdf = self._zencore_validate_pdf_payload(kwargs.get("pdf_form_filled_pdf"))
        if not fields_payload and not filled_pdf:
            return

        sign_request = self.sign_request_id.sudo()
        values = {}
        if fields_payload:
            values["x_zencore_pdf_form_values"] = {
                "fields": self._zencore_merge_pdf_form_fields(
                    (sign_request.x_zencore_pdf_form_values or {}).get("fields") or [],
                    fields_payload,
                )
            }
        if filled_pdf:
            values["x_zencore_pdf_form_filled_pdf"] = filled_pdf
        sign_request.write(values)

    def _zencore_normalize_pdf_form_fields(self, fields_payload):
        if not isinstance(fields_payload, list):
            return []
        normalized = []
        for field in fields_payload:
            if not isinstance(field, dict):
                continue
            name = str(field.get("name") or "").strip()
            if not name:
                continue
            field_type = str(field.get("type") or "").strip().lower()
            value = field.get("value")
            if isinstance(value, list):
                value = [str(item) for item in value if item not in (None, False)]
            elif value not in (None, False):
                value = str(value)
            normalized.append({
                "id": str(field.get("id") or ""),
                "name": name,
                "type": field_type,
                "value": value,
                "checked": bool(field.get("checked")),
                "exportValue": str(field.get("exportValue") or ""),
            })
        return normalized

    def _zencore_merge_pdf_form_fields(self, existing_fields, new_fields):
        merged = {}
        for field in existing_fields + new_fields:
            key = field.get("id") or "%s:%s" % (field.get("name"), field.get("type"))
            if not key:
                continue
            value = field.get("value")
            has_value = value not in (None, False, "", [])
            if field.get("type") in {"checkbox", "radio"}:
                has_value = field.get("checked") or field.get("value") == "Off"
            if has_value or key not in merged:
                merged[key] = field
        return list(merged.values())

    def _zencore_validate_pdf_payload(self, pdf_payload):
        if not pdf_payload:
            return False
        try:
            pdf_bytes = base64.b64decode(pdf_payload, validate=True)
        except (binascii.Error, ValueError):
            return False
        if not pdf_bytes.startswith(b"%PDF"):
            return False
        return base64.b64encode(pdf_bytes)
