# -*- coding: utf-8 -*-
# Copyright (c) 2020, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _
import requests
from requests.exceptions import Timeout
from bs4 import BeautifulSoup
from csf_tz.custom_api import print_out
import re


class VehicleFineRecord(Document):
    pass


def check_fine_all_vehicles():
    plate_list = frappe.get_all("Vehicle")
    all_fine_list = []
    for vehicle in plate_list:
        fine_list = get_fine(number_plate=vehicle["name"])
        if fine_list and len(fine_list) > 0:
            all_fine_list.extend(fine_list)
    reference_list = frappe.get_all(
        "Vehicle Fine Record",
        filters={"status": ["!=", "PAID"], "reference": ["not in", all_fine_list]},
    )
    for reference in reference_list:
        get_fine(reference=reference["name"])


def get_fine(number_plate=None, reference=None):
    if not number_plate and not reference:
        print_out(
            _("Please provide either number plate or reference"),
            alert=True,
            add_traceback=True,
            to_error_log=True,
        )
        return
    # check if the number plate is less than 7 characters
    if number_plate and len(number_plate) < 7:
        print_out(
            f"Please provide a valid number plate for {number_plate}",
            alert=True,
            add_traceback=True,
            to_error_log=True,
        )
        return
    fine_list = []
    token = ""
    url = "https://tms.tpf.go.tz/"

    session = requests.Session()
    try:
        response = session.get(url=url, timeout=30)
    except Timeout:
        frappe.msgprint(_("Error"))
        print("Timeout")
    else:
        print(response.status_code)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # Find the script tag that contains the AJAX call
            script_tag = soup.find(
                "script", string=re.compile(r"\$\.ajax\({.*_token.*}\);", re.DOTALL)
            )
            token = ""
            if script_tag:
                # Extract the value of _token using a regular expression
                match = re.search(r"_token\s*:\s*'(.*)'", script_tag.string)
                if match:
                    token = match.group(1)
                    print(token or "No token")
                else:
                    print("CSRF token not found in the script.")
            if not token:
                print_out(
                    "CSRF token not found in the script.",
                    alert=True,
                    add_traceback=True,
                    to_error_log=True,
                )
                return

            payload = {
                "_token": token,
            }
            if number_plate:
                payload["option"] = "VEHICLE"
                payload["searchable"] = number_plate
            elif reference:
                payload["option"] = "REFERENCE"
                payload["searchable"] = reference
            # send the payload to the server as a POST request as form data
            response2 = session.post(url=url + "results", data=payload, timeout=5)
            if response2.status_code == 200:
                if response2.json:
                    data = response2.json().get("dataFromTms")
                    for key, value in data.items():
                        if value.get(reference):
                            fine_list.append(value["reference"])
                            if frappe.db.exists(
                                "Vehicle Fine Record", value["reference"]
                            ):
                                doc = frappe.get_doc(
                                    "Vehicle Fine Record", value["reference"]
                                )
                                doc.update(value)
                                doc.save()
                            else:
                                fine_doc = frappe.get_doc(
                                    {"doctype": "Vehicle Fine Record", **value}
                                )
                                fine_doc.insert()

                    frappe.db.commit()
            else:
                print_out(
                    response2,
                    alert=True,
                    add_traceback=True,
                    to_error_log=True,
                )

        else:
            print_out(response)
    return fine_list
