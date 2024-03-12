# Copyright (c) 2023, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import CombineDatetime
from frappe.utils import flt
from erpnext.stock.utils import is_reposting_item_valuation_in_progress
from itertools import groupby
from operator import itemgetter
import math

def execute(filters=None):
    is_reposting_item_valuation_in_progress()
    columns = get_columns(filters)
    items = get_items(filters)
    sl_entries = get_stock_ledger_entries(filters, items)
    item_details = get_item_details(items, sl_entries)

    opening_balance_item_wise = []
    for row in sl_entries:
        item_detail = item_details[row.item_code]
        row.update(item_detail)
    
        row["opening_qty"] = row["opening_value"] = row["reconciliation_qty"] = row[
            "reconciliation_value"
        ] = row["purchase_qty"] = row["purchase_value"] = row["sold_qty"] = row[
            "sold_value"
        ] = row[
            "adjustment_qty"
        ] = row[
            "adjustment_value"
        ] = 0

        if not any(record["item_code"] == row.item_code and record["warehouse"] == row.warehouse for record in opening_balance_item_wise):
            opening_balance_item_wise.append({
                "item_code":  row.item_code,
                "warehouse":  row.warehouse
            })
            opening_row = get_opening_balance(
                filters, row.item_code, row.warehouse, sl_entries
            )

            if opening_row:
                row["opening_qty"] = opening_row["qty_after_transaction"]
                row["opening_value"] = (
                    flt(row["opening_qty"]) * opening_row["valuation_rate"]
                )

        if row.voucher_type == "Stock Reconciliation":
            row["reconciliation_qty"] = math.floor(row.stock_value_difference / row.valuation_rate)
            row["reconciliation_value"] = row["reconciliation_qty"] * row.valuation_rate

        if (
            row.voucher_type == "Purchase Receipt"
            or row.voucher_type == "Purchase Invoice"
        ):
            row["purchase_qty"] = row.actual_qty
            row["purchase_value"] = row["purchase_qty"] * row.valuation_rate

        if row.voucher_type == "Delivery Note" or row.voucher_type == "Sales Invoice":
            row["sold_qty"] = row.actual_qty
            row["sold_value"] = row["sold_qty"] * row.valuation_rate

        if row.voucher_type == "Stock Entry":
            row["adjustment_qty"] = row.actual_qty
            row["adjustment_value"] = row["adjustment_qty"] * row.valuation_rate

        row["closing_qty"] = ((row.opening_qty or 0) + (row.purchase_qty or 0)) - (
            (row.sold_qty or 0)
            + (row.adjustment_qty or 0)
            + (row.reconciliation_qty or 0)
        )
        row["closing_value"] = (
            (row.opening_value or 0) + (row.purchase_value or 0)
        ) - (
            (row.sold_value or 0)
            + (row.adjustment_value or 0)
            + (row.reconciliation_value or 0)
        )

    prepared_data = prepare_data(sl_entries)

    return columns, prepared_data


def prepare_data(data):
    sorted_data = sorted(data, key=itemgetter("item_code"))

    grouped_data = {
        key: list(group)
        for key, group in groupby(sorted_data, key=itemgetter("item_code"))
    }
    result = []
    for item_code, group in grouped_data.items():
        result.append(
            {
                "date": group[0]["date"],
                "item_code": item_code,
                "stock_uom": group[0]["stock_uom"],
                "opening_qty": sum(entry["opening_qty"] for entry in group),
                "opening_value": sum(entry["opening_value"] for entry in group),
                "purchase_qty": sum(entry["purchase_qty"] for entry in group),
                "purchase_value": sum(entry["purchase_value"] for entry in group),
                "sold_qty": sum(entry["sold_qty"] for entry in group),
                "sold_value": sum(entry["sold_value"] for entry in group),
                "adjustment_qty": sum(entry["adjustment_qty"] for entry in group),
                "adjustment_value": sum(entry["adjustment_value"] for entry in group),
                "reconciliation_qty": sum(
                    entry["reconciliation_qty"] for entry in group
                ),
                "reconciliation_value": sum(
                    entry["reconciliation_value"] for entry in group
                ),
                "closing_qty": sum(entry["closing_qty"] for entry in group),
                "closing_value": sum(entry["closing_value"] for entry in group),
            }
        )
    return result


def get_columns(filters):
    columns = [
        {
            "label": _("Date"),
            "fieldname": "date",
            "fieldtype": "Datetime",
            "width": 150,
        },
        {
            "label": _("Item"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 100,
        },
        {
            "label": _("Stock UOM"),
            "fieldname": "voucher_type",
            "fieldtype": "Link",
            "options": "UOM",
            "width": 90,
        },
        {
            "label": _("Stock UOM"),
            "fieldname": "voucher_no",
            "fieldtype": "Link",
            "options": "UOM",
            "width": 90,
        },
        {
            "label": _("Stock UOM"),
            "fieldname": "stock_uom",
            "fieldtype": "Link",
            "options": "UOM",
            "width": 90,
        },
        {
            "label": _("Opening Qty"),
            "fieldname": "opening_qty",
            "fieldtype": "Float",
            "width": 150,
            "convertible": "qty",
        },
        {
            "label": _("Opening Value"),
            "fieldname": "opening_value",
            "fieldtype": "Float",
            "width": 150,
            "convertible": "qty",
        },
        {
            "label": _("Purchase Qty"),
            "fieldname": "purchase_qty",
            "fieldtype": "Float",
            "width": 150,
            "convertible": "qty",
        },
        {
            "label": _("Purchase Value"),
            "fieldname": "purchase_value",
            "fieldtype": "Float",
            "width": 150,
            "convertible": "qty",
        },
        {
            "label": _("Sold Qty"),
            "fieldname": "sold_qty",
            "fieldtype": "Float",
            "width": 150,
            "convertible": "qty",
        },
        {
            "label": _("Sold Value"),
            "fieldname": "sold_value",
            "fieldtype": "Float",
            "width": 150,
            "convertible": "qty",
        },
        {
            "label": _("Adjustment Qty"),
            "fieldname": "adjustment_qty",
            "fieldtype": "Float",
            "width": 150,
            "convertible": "qty",
        },
        {
            "label": _("Adjustment Value"),
            "fieldname": "adjustment_value",
            "fieldtype": "Float",
            "width": 150,
            "convertible": "qty",
        },
        {
            "label": _("Reconciliation Qty"),
            "fieldname": "reconciliation_qty",
            "fieldtype": "Float",
            "width": 150,
            "convertible": "qty",
        },
        {
            "label": _("Reconciliation Value"),
            "fieldname": "reconciliation_value",
            "fieldtype": "Float",
            "width": 150,
            "convertible": "qty",
        },
        {
            "label": _("Closing Qty"),
            "fieldname": "closing_qty",
            "fieldtype": "Float",
            "width": 150,
            "convertible": "qty",
        },
        {
            "label": _("Closing Value"),
            "fieldname": "closing_value",
            "fieldtype": "Float",
            "width": 150,
            "convertible": "qty",
        },
    ]

    return columns


def get_stock_ledger_entries(filters, items):
    sle = frappe.qb.DocType("Stock Ledger Entry")
    query = (
        frappe.qb.from_(sle)
        .select(
            sle.item_code,
            CombineDatetime(sle.posting_date, sle.posting_time).as_("date"),
            sle.warehouse,
            sle.posting_date,
            sle.posting_time,
            sle.actual_qty,
            sle.valuation_rate,
            sle.valuation_rate,
            sle.company,
            sle.voucher_type,
            sle.qty_after_transaction,
            sle.stock_value_difference,
            sle.voucher_no,
            sle.stock_value,
            sle.batch_no,
            sle.serial_no,
            sle.project,
        )
        .where(
            (sle.docstatus < 2)
            & (sle.is_cancelled == 0)
            & (sle.posting_date[filters.from_date : filters.to_date])
        )
        .orderby(CombineDatetime(sle.posting_date, sle.posting_time))
        .orderby(sle.creation)
    )
    if filters.warehouse:
        query = query.where(sle.warehouse == filters.get("warehouse"))  
    if filters.item_code:
        query = query.where(sle.item_code == filters.get("item_code"))	

    return query.run(as_dict=True)

def get_items(filters):
    item = frappe.qb.DocType("Item")
    query = frappe.qb.from_(item).select(item.name)
    conditions = []

    if item_code := filters.get("item_code"):
        conditions.append(item.name == item_code)
    else:
        if item_group := filters.get("item_group"):
            if condition := get_item_group_condition(item_group, item):
                conditions.append(condition)

    items = []
    if conditions:
        for condition in conditions:
            query = query.where(condition)
        items = [r[0] for r in query.run()]

    return items


def get_item_details(items, sl_entries):
    item_details = {}
    if not items:
        items = list(set(d.item_code for d in sl_entries))

    if not items:
        return item_details

    item = frappe.qb.DocType("Item")
    query = (
        frappe.qb.from_(item)
        .select(
            item.name,
            item.item_name,
            item.description,
            item.item_group,
            item.brand,
            item.stock_uom,
        )
        .where(item.name.isin(items))
    )

    res = query.run(as_dict=True)

    for item in res:
        item_details.setdefault(item.name, item)

    return item_details


def get_opening_balance(filters, item_code, warehouse, sl_entries):
    if not filters.from_date:
        return

    from erpnext.stock.stock_ledger import get_previous_sle

    last_entry = get_previous_sle(
        {
            "item_code": item_code,
            "warehouse_condition": get_warehouse_condition(warehouse),
            "posting_date": filters.from_date,
            "posting_time": "00:00:00",
        }
    )

    # check if any SLEs are actually Opening Stock Reconciliation
    for sle in list(sl_entries):
        if (
            sle.get("voucher_type") == "Stock Reconciliation"
            and sle.posting_date == filters.from_date
            and frappe.db.get_value("Stock Reconciliation", sle.voucher_no, "purpose")
            == "Opening Stock"
        ):
            last_entry = sle
            sl_entries.remove(sle)

    row = {
        "item_code": item_code,
        "qty_after_transaction": last_entry.get("qty_after_transaction", 0),
        "valuation_rate": last_entry.get("valuation_rate", 0),
        "stock_value": last_entry.get("stock_value", 0),
    }

    return row


def get_warehouse_condition(warehouse):
    warehouse_details = frappe.db.get_value(
        "Warehouse", warehouse, ["lft", "rgt"], as_dict=1
    )
    if warehouse_details:
        return (
            " exists (select name from `tabWarehouse` wh \
			where wh.lft >= %s and wh.rgt <= %s and warehouse = wh.name)"
            % (warehouse_details.lft, warehouse_details.rgt)
        )

    return ""


def get_item_group_condition(item_group, item_table=None):
    item_group_details = frappe.db.get_value(
        "Item Group", item_group, ["lft", "rgt"], as_dict=1
    )
    if item_group_details:
        if item_table:
            ig = frappe.qb.DocType("Item Group")
            return item_table.item_group.isin(
                (
                    frappe.qb.from_(ig)
                    .select(ig.name)
                    .where(
                        (ig.lft >= item_group_details.lft)
                        & (ig.rgt <= item_group_details.rgt)
                        & (item_table.item_group == ig.name)
                    )
                )
            )
        else:
            return (
                "item.item_group in (select ig.name from `tabItem Group` ig \
				where ig.lft >= %s and ig.rgt <= %s and item.item_group = ig.name)"
                % (item_group_details.lft, item_group_details.rgt)
            )

