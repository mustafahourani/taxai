"""2025 Federal Tax Tables."""

# Standard deductions by filing status
STANDARD_DEDUCTIONS = {
    "single": 15750,
    "married_jointly": 31500,
    "married_separately": 15750,
    "head_of_household": 23625,
}

# 2025 Federal income tax brackets
# Each entry: (upper_bound, rate)  — upper_bound is inclusive, None means no limit
TAX_BRACKETS = {
    "single": [
        (11925, 0.10),
        (48475, 0.12),
        (103350, 0.22),
        (197300, 0.24),
        (250525, 0.32),
        (626350, 0.35),
        (None, 0.37),
    ],
    "married_jointly": [
        (23850, 0.10),
        (96950, 0.12),
        (206700, 0.22),
        (394600, 0.24),
        (501050, 0.32),
        (751600, 0.35),
        (None, 0.37),
    ],
    "married_separately": [
        (11925, 0.10),
        (48475, 0.12),
        (103350, 0.22),
        (197300, 0.24),
        (250525, 0.32),
        (375800, 0.35),
        (None, 0.37),
    ],
    "head_of_household": [
        (17000, 0.10),
        (64850, 0.12),
        (103350, 0.22),
        (197300, 0.24),
        (250500, 0.32),
        (626350, 0.35),
        (None, 0.37),
    ],
}

# Social Security tax rate (employee share)
SS_TAX_RATE = 0.062
SS_WAGE_LIMIT = 176100  # 2025

# Medicare tax rate (employee share)
MEDICARE_TAX_RATE = 0.0145

# Child Tax Credit
CHILD_TAX_CREDIT = 2000  # per qualifying child under 17

# Filing status display names
FILING_STATUS_NAMES = {
    "single": "Single",
    "married_jointly": "Married Filing Jointly",
    "married_separately": "Married Filing Separately",
    "head_of_household": "Head of Household",
}
