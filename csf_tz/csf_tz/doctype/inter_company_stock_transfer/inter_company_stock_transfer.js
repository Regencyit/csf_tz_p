// Copyright (c) 2023, Aakvatech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inter Company Stock Transfer', {
    refresh: function (frm) {
        frm.set_query('default_from_warehouse', () => {
            return {
                filters: {
                    company: frm.doc.from_company
                }
            };
        });
        frm.set_query('default_to_warehouse', () => {
            return {
                filters: {
                    company: frm.doc.to_company
                }
            };
        });
    }
});

