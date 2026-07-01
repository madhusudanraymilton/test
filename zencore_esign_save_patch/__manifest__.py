{
    "name": "Sign Native PDF Form Save Patch",
    "version": "18.0.1.0.4",
    "category": "Productivity/Sign",
    "summary": "Save native PDF form data when validating an Odoo Sign document",
    "depends": ["sign"],
    "data": [
        "views/sign_request_templates.xml",
    ],
    "assets": {
        "sign.assets_pdf_iframe": [
            "zencore_esign_save_patch/static/src/css/pdf_form_comb.css",
        ],
        "sign.assets_public_sign": [
            "zencore_esign_save_patch/static/src/js/signable_pdf_iframe_patch.js",
        ],
        "web.assets_backend": [
            "zencore_esign_save_patch/static/src/js/signable_pdf_iframe_patch.js",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
