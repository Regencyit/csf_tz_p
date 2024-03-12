import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    fields = {
        "Stock Entry":[
            dict(
                fieldname= "csf_tz_specifics",
                fieldtype="Section Break",
                label="CSF TZ Specifics",
            ),
            dict(
                fieldname= "transfer_goods_between_company",
                fieldtype="Link",
                label="Inter Company Stock Transfer",
                options="Inter Company Stock Transfer"
            ),
        ]
    }
    create_custom_fields(fields, update=True) 