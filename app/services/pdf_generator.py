"""Fill the official IRS Form 1040 PDF with computed tax data."""

from pathlib import Path

FORM_PATH = Path(__file__).parent.parent / "data" / "f1040.pdf"

# Field name prefix helpers
P1 = "topmostSubform[0].Page1[0]."
P1A = "topmostSubform[0].Page1[0].Address_ReadOrder[0]."
P1C = "topmostSubform[0].Page1[0].Checkbox_ReadOrder[0]."
P2 = "topmostSubform[0].Page2[0]."

# Filing status -> radio button value for c1_8 group
FILING_STATUS_VALUES = {
    "single": "/1",
    "married_jointly": "/2",
    "married_separately": "/3",
    "head_of_household": "/4",
    "qualifying_surviving_spouse": "/5",
}


def _fmt(n):
    """Format number for IRS form fields."""
    if n == 0:
        return ""
    if n == int(n):
        return "{:,.0f}".format(n)
    return "{:,.2f}".format(n)


def generate_form_1040_pdf(data: dict) -> bytes:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject
    from io import BytesIO

    tp = data["taxpayer"]
    li = data["line_items"]
    filing_status = data["filing_status"]

    reader = PdfReader(str(FORM_PATH))
    writer = PdfWriter()
    writer.append(reader)

    # --- Page 1 form fields ---
    page1 = {
        # Personal info
        P1 + "f1_14[0]": tp["first_name"],
        P1 + "f1_15[0]": tp["last_name"],
        P1 + "f1_16[0]": tp["ssn"].replace("-", "").replace("*", ""),

        # Filing status checkbox (radio button group c1_8)
        P1C + "c1_8[0]": FILING_STATUS_VALUES.get(filing_status, "/1"),
    }

    # Address fields (nested under Address_ReadOrder)
    addr = tp.get("address", "")
    if ", " in addr:
        parts = addr.split(", ")
        if len(parts) >= 3:
            page1[P1A + "f1_20[0]"] = parts[0]          # Street
            page1[P1A + "f1_22[0]"] = parts[1]          # City
            state_zip = parts[2].split(" ", 1)
            if len(state_zip) == 2:
                page1[P1A + "f1_23[0]"] = state_zip[0]  # State
                page1[P1A + "f1_24[0]"] = state_zip[1]  # ZIP
        elif len(parts) == 2:
            page1[P1A + "f1_20[0]"] = parts[0]
            page1[P1A + "f1_22[0]"] = parts[1]
    else:
        page1[P1A + "f1_20[0]"] = addr

    # Income lines (Page 1)
    page1[P1 + "f1_47[0]"] = _fmt(li["1a_wages"])        # Line 1a - Wages
    page1[P1 + "f1_56[0]"] = _fmt(li["1a_wages"])        # Line 1z - Sum of 1a-1h
    page1[P1 + "f1_59[0]"] = _fmt(li["2b_interest"])     # Line 2b - Taxable interest
    page1[P1 + "f1_61[0]"] = _fmt(li["3b_dividends"])    # Line 3b - Ordinary dividends
    page1[P1 + "f1_73[0]"] = _fmt(li["9_total_income"])  # Line 9 - Total income
    page1[P1 + "f1_74[0]"] = _fmt(li["10_adjustments"])  # Line 10 - Adjustments
    page1[P1 + "f1_75[0]"] = _fmt(li["11_agi"])          # Line 11a - AGI

    writer.update_page_form_field_values(writer.pages[0], page1)

    # Digital Assets checkbox — requires direct annotation manipulation
    # c1_10[0] = Yes (/1), c1_10[1] = No (/2)
    digital_assets = data.get("digital_assets", False)
    da_target = 'c1_10[0]' if digital_assets else 'c1_10[1]'
    da_value = '/1' if digital_assets else '/2'
    page = writer.pages[0]
    for annot_ref in page['/Annots']:
        annot = annot_ref.get_object()
        t = str(annot.get('/T', ''))
        if t == da_target:
            annot[NameObject('/AS')] = NameObject(da_value)

    # --- Page 2 form fields ---
    page2 = {
        # Tax and Credits
        P2 + "f2_01[0]": _fmt(li["11_agi"]),                # Line 11b - AGI
        P2 + "f2_02[0]": _fmt(li["12_deduction"]),          # Line 12e - Deduction
        P2 + "f2_05[0]": _fmt(li["12_deduction"]),          # Line 14
        P2 + "f2_06[0]": _fmt(li["14_taxable_income"]),     # Line 15 - Taxable income
        P2 + "f2_08[0]": _fmt(li["16_tax"]),                # Line 16 - Tax
        P2 + "f2_10[0]": _fmt(li["16_tax"]),                # Line 18
        P2 + "f2_11[0]": _fmt(li["19_child_credit"]),       # Line 19 - Child tax credit
        P2 + "f2_13[0]": _fmt(li["19_child_credit"]),       # Line 21
        P2 + "f2_14[0]": _fmt(max(li["16_tax"] - li["19_child_credit"], 0)),  # Line 22
        P2 + "f2_16[0]": _fmt(li["24_total_tax"]),          # Line 24 - Total tax

        # Payments
        P2 + "f2_17[0]": _fmt(li["25a_federal_withheld"]),  # Line 25a - W-2 withholding
        P2 + "f2_20[0]": _fmt(li["25a_federal_withheld"]),  # Line 25d
        P2 + "f2_29[0]": _fmt(li["33_total_payments"]),     # Line 33 - Total payments
    }

    # Refund or amount owed
    if li["34_overpayment"] > 0:
        page2[P2 + "f2_30[0]"] = _fmt(li["34_overpayment"])   # Line 34 - Overpaid
        page2[P2 + "f2_31[0]"] = _fmt(li["34_overpayment"])   # Line 35a - Refunded
    if li["37_amount_owed"] > 0:
        page2[P2 + "f2_35[0]"] = _fmt(li["37_amount_owed"])   # Line 37 - Amount owed

    writer.update_page_form_field_values(writer.pages[1], page2)

    output = BytesIO()
    writer.write(output)
    return output.getvalue()
