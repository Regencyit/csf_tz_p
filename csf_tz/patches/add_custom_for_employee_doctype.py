import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    fields = {
        "Employee":[
            dict(
                fieldname= "bank_account_name",
                fieldtype="Data",
                label="Bank Account Name",         
                translatable= 1,
            ),
            dict(
                fieldname= "employee_country_code",
                fieldtype="Link",
                options="Country",
                label="Employee Country",
            ),
            dict(
                fieldname= "employee_country",
                fieldtype="Data",
                fetch_from="employee_country.code",
                label="Employee Country",         
                translatable= 1,
            ),
            dict(
                fieldname= "bank_country",
                fieldtype="Link",
                options="country",
                label="Bank Country",
                insert_after="bank_code",
            ),
            dict(
                fieldname= "bank_country_code",
                fieldtype="Data",
                options="country",                
                fetch_from="bank_country.code",
                label="Bank Country Code",
                read_only= 1,         
                translatable= 1,
            ),
        ]
    }
    create_custom_fields(fields, update=True) 
