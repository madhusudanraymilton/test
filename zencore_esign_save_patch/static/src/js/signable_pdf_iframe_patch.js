/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PDFIframe } from "@sign/components/sign_request/PDF_iframe";
import { SignablePDFIframe } from "@sign/components/sign_request/signable_PDF_iframe";

patch(PDFIframe.prototype, {
    postRender() {
        super.postRender(...arguments);
        this._zencoreRenderCombBoxes();

        const viewer = this.root.querySelector("#viewer");
        if (!viewer) {
            return;
        }
        const observer = new MutationObserver(() => this._zencoreRenderCombBoxes());
        observer.observe(viewer, { childList: true, subtree: true });
        this.cleanupFns.push(() => observer.disconnect());
    },

    /**
     * PDF.js renders comb fields as a single HTML input. Its letter spacing is
     * correct, but it omits the individual character-cell dividers found in the
     * original PDF appearance. Add the cell count as a CSS variable so the
     * iframe stylesheet can restore those dividers.
     */
    _zencoreRenderCombBoxes() {
        this.root.querySelectorAll(".annotationLayer input.comb").forEach((element) => {
            if (element.maxLength > 0) {
                element.classList.add("zencore-comb-boxes");
                element.style.setProperty("--zencore-comb-length", element.maxLength);
            }
        });
    },
});

patch(SignablePDFIframe.prototype, {
    async _sign() {
        this.zencorePDFFormPayload = await this._zencoreGetPDFFormPayload();
        return super._sign(...arguments);
    },

    _getRouteAndParams() {
        const [route, params] = super._getRouteAndParams(...arguments);
        const payload = this.zencorePDFFormPayload;
        if (payload?.fields?.length) {
            params.pdf_form_values = payload.fields;
        }
        if (payload?.filledPDF) {
            params.pdf_form_filled_pdf = payload.filledPDF;
        }
        return [route, params];
    },

    async _zencoreGetPDFFormPayload() {
        const fields = await this._zencoreCollectPDFFormFields();
        const filledPDF = await this._zencoreSavePDFFormDocument();
        return { fields, filledPDF };
    },

    async _zencoreCollectPDFFormFields() {
        const pdfDocument = this.root.defaultView?.PDFViewerApplication?.pdfDocument;
        if (pdfDocument?.getFieldObjects) {
            try {
                const fields = await this._zencoreCollectPDFJSFormFields(pdfDocument);
                if (fields.length) {
                    return fields;
                }
            } catch {
                // A malformed AcroForm must not prevent the signer from submitting.
            }
        }
        return this._zencoreCollectRenderedPDFFormFields(pdfDocument);
    },

    /**
     * Reads every AcroForm field, including controls on PDF.js pages that are not
     * currently rendered. Values changed by the signer live in annotationStorage,
     * rather than necessarily in a DOM input element.
     */
    async _zencoreCollectPDFJSFormFields(pdfDocument) {
        const fieldObjects = await pdfDocument.getFieldObjects();
        const annotationStorage = pdfDocument.annotationStorage;
        const fields = [];

        for (const [name, widgets] of Object.entries(fieldObjects || {})) {
            for (const widget of widgets) {
                if (!widget?.id || !name || !annotationStorage?.has(widget.id)) {
                    continue;
                }
                const type = this._zencorePDFJSFieldType(widget);
                const storedValue = annotationStorage.get(widget.id)?.value;
                const checked = type === "checkbox" || type === "radio"
                    ? Boolean(storedValue)
                    : false;
                fields.push({
                    id: widget.id,
                    name,
                    type,
                    value: this._zencorePDFJSFieldValue(storedValue, type, widget),
                    checked,
                    exportValue: widget.exportValues || "",
                });
            }
        }
        return fields;
    },

    _zencorePDFJSFieldType(widget) {
        if (widget.type === "radiobutton") {
            return "radio";
        }
        if (widget.type === "checkbox") {
            return "checkbox";
        }
        if (widget.type === "listbox" && widget.multipleSelection) {
            return "select-multiple";
        }
        if (widget.type === "listbox" || widget.type === "combobox") {
            return "select-one";
        }
        return widget.multiline ? "textarea" : "text";
    },

    _zencorePDFJSFieldValue(value, type, widget) {
        if (type === "checkbox" || type === "radio") {
            return value ? widget.exportValues || "Yes" : "Off";
        }
        return value ?? "";
    },

    _zencoreCollectRenderedPDFFormFields(pdfDocument) {
        const annotationStorage = pdfDocument?.annotationStorage;
        const elements = this.root.querySelectorAll("[data-element-id]");
        return [...elements]
            .filter((element) => {
                const id = element.getAttribute("data-element-id");
                return element.name && (!annotationStorage || annotationStorage.has(id));
            })
            .map((element) => {
                const type = this._zencorePDFFormElementType(element);
                return {
                    id: element.getAttribute("data-element-id") || "",
                    name: element.name,
                    type,
                    value: this._zencorePDFFormElementValue(element, type),
                    checked: Boolean(element.checked),
                    exportValue: element.getAttribute("exportValue") || element.value || "",
                };
            });
    },

    _zencorePDFFormElementType(element) {
        if (element.tagName === "TEXTAREA") {
            return "textarea";
        }
        if (element.tagName === "SELECT") {
            return element.multiple ? "select-multiple" : "select-one";
        }
        return element.type || "text";
    },

    _zencorePDFFormElementValue(element, type) {
        if (type === "checkbox" || type === "radio") {
            return element.checked ? element.getAttribute("exportValue") || element.value || "Yes" : "Off";
        }
        if (type === "select-multiple") {
            return [...element.selectedOptions].map((option) => option.value);
        }
        return element.value || "";
    },

    async _zencoreSavePDFFormDocument() {
        const pdfApplication = this.root.defaultView?.PDFViewerApplication;
        const pdfDocument = pdfApplication?.pdfDocument;
        if (!pdfDocument?.annotationStorage?.size || !pdfDocument.saveDocument) {
            return false;
        }
        try {
            const data = await pdfDocument.saveDocument();
            return this._zencoreUint8ArrayToBase64(data);
        } catch {
            return false;
        }
    },

    _zencoreUint8ArrayToBase64(data) {
        const chunkSize = 0x8000;
        let binary = "";
        for (let index = 0; index < data.length; index += chunkSize) {
            binary += String.fromCharCode(...data.subarray(index, index + chunkSize));
        }
        return btoa(binary);
    },
});
