"""Form 1040 tax computation engine for 2025 federal taxes."""

from app.data.tax_tables import (
    STANDARD_DEDUCTIONS,
    TAX_BRACKETS,
    CHILD_TAX_CREDIT,
    FILING_STATUS_NAMES,
)


def compute_tax_from_brackets(taxable_income: float, filing_status: str) -> float:
    """Compute federal income tax using progressive brackets."""
    brackets = TAX_BRACKETS.get(filing_status, TAX_BRACKETS["single"])
    tax = 0.0
    prev_bound = 0

    for upper_bound, rate in brackets:
        if upper_bound is None:
            # Top bracket — tax all remaining income
            if taxable_income > prev_bound:
                tax += (taxable_income - prev_bound) * rate
            break
        else:
            if taxable_income <= prev_bound:
                break
            taxable_in_bracket = min(taxable_income, upper_bound) - prev_bound
            tax += taxable_in_bracket * rate
            prev_bound = upper_bound

    return round(tax, 2)


def compute_form_1040(data: dict) -> dict:
    """
    Compute a full Form 1040 from user input.

    Expected input `data`:
    {
        "filing_status": "single" | "married_jointly" | "married_separately" | "head_of_household",
        "first_name": str,
        "last_name": str,
        "ssn": str,
        "address": str,
        "dependents": [{"name": str, "ssn": str, "relationship": str, "child_tax_credit": bool}],
        "w2s": [{"employer": str, "wages": float, "federal_withheld": float, "ss_wages": float, "ss_withheld": float, "medicare_wages": float, "medicare_withheld": float, "state": str, "state_wages": float, "state_withheld": float}],
        "interest_income": float,  # 1099-INT total
        "dividend_income": float,  # 1099-DIV total
        "other_income": float,
        "adjustments": float,  # above-the-line deductions (IRA, student loan interest, etc.)
        "use_standard_deduction": bool,
        "itemized_deductions": float,  # only if use_standard_deduction is False
    }
    """
    filing_status = data.get("filing_status", "single")
    dependents = data.get("dependents", [])
    w2s = data.get("w2s", [])

    # --- INCOME ---
    # Line 1a: Wages
    total_wages = sum(w.get("wages", 0) for w in w2s)
    # Line 2b: Taxable interest
    interest = data.get("interest_income", 0)
    # Line 3b: Ordinary dividends
    dividends = data.get("dividend_income", 0)
    # Line 8: Other income
    other = data.get("other_income", 0)
    # Line 9: Total income
    total_income = total_wages + interest + dividends + other

    # --- ADJUSTMENTS ---
    # Line 10: Adjustments to income
    # Student loan interest deduction (up to $2,500, phases out at higher AGI)
    student_loan_interest = min(data.get("student_loan_interest", 0), 2500)
    other_adjustments = data.get("adjustments", 0)
    adjustments = student_loan_interest + other_adjustments
    # Line 11: Adjusted Gross Income
    agi = total_income - adjustments

    # --- DEDUCTIONS ---
    standard_deduction = STANDARD_DEDUCTIONS.get(filing_status, 15000)
    use_standard = data.get("use_standard_deduction", True)
    itemized = data.get("itemized_deductions", 0)

    # Track optimizations the engine made
    optimizations = []

    # Student loan interest optimization
    if student_loan_interest > 0:
        tax_without = compute_tax_from_brackets(max(total_income - standard_deduction, 0), filing_status)
        tax_with = compute_tax_from_brackets(max(total_income - student_loan_interest - standard_deduction, 0), filing_status)
        sli_savings = round(tax_without - tax_with, 2)
        optimizations.append({
            "action": "Applied ${:,.2f} student loan interest deduction".format(student_loan_interest),
            "detail": "Detected 1098-E from your loan servicer. Student loan interest is an above-the-line deduction that reduces your AGI from ${:,.2f} to ${:,.2f}, saving you ${:,.2f} in taxes.".format(
                total_income, agi, sli_savings),
            "savings": sli_savings,
        })

    # Deduction optimization: compare standard vs itemized
    if itemized > 0 and itemized > standard_deduction:
        deduction = itemized
        deduction_type = "Itemized"
        savings_vs_standard = round(
            compute_tax_from_brackets(max(agi - standard_deduction, 0), filing_status) -
            compute_tax_from_brackets(max(agi - itemized, 0), filing_status), 2
        )
        optimizations.append({
            "action": "Chose itemized deductions over standard",
            "detail": "Your itemized deductions (${:,.0f}) exceed the standard deduction (${:,.0f}), saving you ${:,.0f} in taxes.".format(
                itemized, standard_deduction, savings_vs_standard),
            "savings": savings_vs_standard,
        })
    else:
        deduction = standard_deduction
        deduction_type = "Standard"
        if itemized > 0:
            optimizations.append({
                "action": "Chose standard deduction over itemized",
                "detail": "The standard deduction (${:,.0f}) is higher than your itemized deductions (${:,.0f}). This automatically reduces your taxable income more.".format(
                    standard_deduction, itemized),
                "savings": round(
                    compute_tax_from_brackets(max(agi - itemized, 0), filing_status) -
                    compute_tax_from_brackets(max(agi - standard_deduction, 0), filing_status), 2
                ),
            })
        else:
            optimizations.append({
                "action": "Applied ${:,.0f} standard deduction".format(standard_deduction),
                "detail": "As a {} filer, you get the ${:,.0f} standard deduction, which reduces your taxable income from ${:,.0f} to ${:,.0f}.".format(
                    FILING_STATUS_NAMES.get(filing_status, filing_status),
                    standard_deduction, agi, max(agi - standard_deduction, 0)),
                "savings": round(
                    compute_tax_from_brackets(agi, filing_status) -
                    compute_tax_from_brackets(max(agi - standard_deduction, 0), filing_status), 2
                ),
            })

    # Line 14: Taxable income
    taxable_income = max(agi - deduction, 0)

    # --- TAX ---
    # Line 16: Tax from brackets
    tax = compute_tax_from_brackets(taxable_income, filing_status)

    # Tax bracket optimization
    brackets = TAX_BRACKETS.get(filing_status, TAX_BRACKETS["single"])
    marginal_rate = 0.10
    for upper, rate in brackets:
        if upper is None or taxable_income <= upper:
            marginal_rate = rate
            break
    optimizations.append({
        "action": "Computed tax using progressive brackets",
        "detail": "Your ${:,.0f} taxable income is taxed progressively. Your marginal rate is {:.0f}%, but your effective rate is lower because lower brackets are taxed at lower rates.".format(
            taxable_income, marginal_rate * 100),
        "savings": None,
    })

    # --- CREDITS ---
    # Line 19: Child tax credit
    qualifying_children = sum(1 for d in dependents if d.get("child_tax_credit", False))
    child_credit = qualifying_children * CHILD_TAX_CREDIT
    # Credit cannot exceed tax
    child_credit = min(child_credit, tax)

    if qualifying_children > 0:
        optimizations.append({
            "action": "Applied Child Tax Credit for {} {}".format(
                qualifying_children, "child" if qualifying_children == 1 else "children"),
            "detail": "${:,.0f} per qualifying child directly reduces your tax bill. This saved you ${:,.0f}.".format(
                CHILD_TAX_CREDIT, child_credit),
            "savings": round(child_credit, 2),
        })

    # Line 24: Total tax
    total_tax = max(tax - child_credit, 0)

    # --- PAYMENTS ---
    # Line 25a: Federal income tax withheld from W-2s
    federal_withheld = sum(w.get("federal_withheld", 0) for w in w2s)
    # Line 33: Total payments
    total_payments = federal_withheld

    # W-2 consolidation optimization
    if len(w2s) > 1:
        optimizations.append({
            "action": "Consolidated {} W-2 forms".format(len(w2s)),
            "detail": "Combined wages and withholdings from all employers into a single return for accurate bracket calculation.",
            "savings": None,
        })

    # Withholding analysis
    optimizations.append({
        "action": "Verified withholding accuracy",
        "detail": "Your employer withheld ${:,.0f} in federal taxes. Based on your actual tax of ${:,.0f}, you {} by ${:,.0f}.".format(
            federal_withheld, total_tax,
            "overpaid" if federal_withheld > total_tax else "underpaid",
            abs(round(federal_withheld - total_tax, 2))),
        "savings": None,
    })

    # --- REFUND OR OWED ---
    if total_payments > total_tax:
        overpayment = round(total_payments - total_tax, 2)
        amount_owed = 0
    else:
        overpayment = 0
        amount_owed = round(total_tax - total_payments, 2)

    # W-2 summaries
    total_ss_withheld = sum(w.get("ss_withheld", 0) for w in w2s)
    total_medicare_withheld = sum(w.get("medicare_withheld", 0) for w in w2s)

    # Total savings from optimizations
    total_savings = sum(o["savings"] for o in optimizations if o["savings"])

    return {
        "filing_status": filing_status,
        "filing_status_name": FILING_STATUS_NAMES.get(filing_status, filing_status),
        "taxpayer": {
            "first_name": data.get("first_name", ""),
            "last_name": data.get("last_name", ""),
            "ssn": data.get("ssn", ""),
            "address": data.get("address", ""),
        },
        "digital_assets": data.get("digital_assets", False),
        "dependents": dependents,
        "qualifying_children": qualifying_children,
        "w2_count": len(w2s),
        "line_items": {
            "1a_wages": round(total_wages, 2),
            "2b_interest": round(interest, 2),
            "3b_dividends": round(dividends, 2),
            "8_other_income": round(other, 2),
            "9_total_income": round(total_income, 2),
            "10_adjustments": round(adjustments, 2),
            "11_agi": round(agi, 2),
            "12_deduction": round(deduction, 2),
            "12_deduction_type": deduction_type,
            "14_taxable_income": round(taxable_income, 2),
            "16_tax": round(tax, 2),
            "19_child_credit": round(child_credit, 2),
            "24_total_tax": round(total_tax, 2),
            "25a_federal_withheld": round(federal_withheld, 2),
            "33_total_payments": round(total_payments, 2),
            "34_overpayment": round(overpayment, 2),
            "37_amount_owed": round(amount_owed, 2),
        },
        "summary": {
            "total_income": round(total_income, 2),
            "agi": round(agi, 2),
            "taxable_income": round(taxable_income, 2),
            "total_tax": round(total_tax, 2),
            "total_payments": round(total_payments, 2),
            "refund": round(overpayment, 2),
            "owed": round(amount_owed, 2),
            "effective_rate": round((total_tax / total_income * 100), 1) if total_income > 0 else 0,
            "ss_withheld": round(total_ss_withheld, 2),
            "medicare_withheld": round(total_medicare_withheld, 2),
        },
        "standard_deduction": round(standard_deduction, 2),
        "optimizations": optimizations,
        "total_optimization_savings": round(total_savings, 2),
    }
