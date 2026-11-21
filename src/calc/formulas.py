from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


def _decimal(value: Decimal | int | float | str) -> Decimal:
    try:
        result = Decimal(str(value).replace(",", "").strip())
    except (ArithmeticError, ValueError) as exc:
        raise ValueError(f"Invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise ValueError("Calculator inputs must be finite numbers.")
    return result


def _money(value: Decimal, rounding_decimals: int) -> Decimal:
    quantum = Decimal("1").scaleb(-rounding_decimals)
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def _positive(name: str, value: Decimal, *, allow_zero: bool = False) -> None:
    if value < ZERO or (not allow_zero and value == ZERO):
        requirement = "non-negative" if allow_zero else "greater than zero"
        raise ValueError(f"{name} must be {requirement}.")


def _result(
    result: Any,
    formula_name: str,
    steps: list[str],
    assumptions: list[str],
    currency: str | None,
) -> dict[str, Any]:
    return {
        "result": result,
        "currency": currency,
        "formula_name": formula_name,
        "steps": steps,
        "assumptions": assumptions,
    }


def emi(
    principal: Decimal | int | float | str,
    annual_rate_pct: Decimal | int | float | str,
    months: int,
    currency: str | None = None,
    rounding_decimals: int = 2,
) -> dict[str, Any]:
    p = _decimal(principal)
    annual = _decimal(annual_rate_pct)
    _positive("principal", p)
    _positive("annual_rate_pct", annual, allow_zero=True)
    if months <= 0:
        raise ValueError("months must be greater than zero.")
    rate = annual / Decimal("12") / HUNDRED
    if rate == ZERO:
        payment = p / Decimal(months)
        name = "zero_rate_principal_divided_by_months"
        steps = ["Monthly payment = principal / number of months."]
    else:
        factor = (ONE + rate) ** months
        payment = p * rate * factor / (factor - ONE)
        name = "reducing_balance_emi"
        steps = [
            "Monthly rate = annual rate / 12 / 100.",
            "EMI = principal * monthly_rate * (1 + monthly_rate)^months / ((1 + monthly_rate)^months - 1).",
        ]
    return _result(
        _money(payment, rounding_decimals),
        name,
        steps,
        ["Fixed annual rate and equal monthly payments are assumed.", f"Amounts are rounded to {rounding_decimals} decimal places."],
        currency,
    )


def amortization_schedule(
    principal: Decimal | int | float | str,
    annual_rate_pct: Decimal | int | float | str,
    months: int,
    currency: str | None = None,
    rounding_decimals: int = 2,
) -> dict[str, Any]:
    p = _decimal(principal)
    annual = _decimal(annual_rate_pct)
    _positive("principal", p)
    _positive("annual_rate_pct", annual, allow_zero=True)
    if months <= 0:
        raise ValueError("months must be greater than zero.")
    regular_payment = emi(p, annual, months, currency, rounding_decimals)["result"]
    monthly_rate = annual / Decimal("12") / HUNDRED
    balance = _money(p, rounding_decimals)
    rows: list[dict[str, Any]] = []
    for month in range(1, months + 1):
        interest = _money(balance * monthly_rate, rounding_decimals)
        principal_paid = _money(regular_payment - interest, rounding_decimals)
        payment = regular_payment
        if month == months or principal_paid >= balance:
            principal_paid = balance
            payment = _money(principal_paid + interest, rounding_decimals)
        balance = _money(balance - principal_paid, rounding_decimals)
        if balance < ZERO:
            balance = ZERO
        rows.append({
            "month": month,
            "payment": payment,
            "interest": interest,
            "principal": principal_paid,
            "balance": balance,
            "currency": currency,
        })
    return _result(
        rows,
        "monthly_amortization_schedule",
        [
            "Monthly interest = opening balance * (annual rate / 12 / 100).",
            "Principal paid = payment - monthly interest.",
            "The final payment is adjusted to clear the remaining balance exactly.",
        ],
        ["Monthly interest, payment, principal, and balance are rounded to the configured decimal places.", "No fees, taxes, rate resets, or payment-date variations are included."],
        currency,
    )


def total_interest(
    principal: Decimal | int | float | str,
    annual_rate_pct: Decimal | int | float | str,
    months: int,
    currency: str | None = None,
    rounding_decimals: int = 2,
) -> dict[str, Any]:
    schedule = amortization_schedule(principal, annual_rate_pct, months, currency, rounding_decimals)
    interest_sum = sum((row["interest"] for row in schedule["result"]), ZERO)
    return _result(
        _money(interest_sum, rounding_decimals),
        "sum_of_amortization_schedule_interest",
        ["Build the monthly amortization schedule.", "Add each month's rounded interest amount."],
        schedule["assumptions"],
        currency,
    )


def total_payment(
    principal: Decimal | int | float | str,
    annual_rate_pct: Decimal | int | float | str,
    months: int,
    currency: str | None = None,
    rounding_decimals: int = 2,
) -> dict[str, Any]:
    schedule = amortization_schedule(principal, annual_rate_pct, months, currency, rounding_decimals)
    payments = sum((row["payment"] for row in schedule["result"]), ZERO)
    return _result(
        _money(payments, rounding_decimals),
        "sum_of_amortization_schedule_payments",
        ["Build the monthly amortization schedule.", "Add each monthly payment, including the adjusted final payment."],
        schedule["assumptions"],
        currency,
    )


def outstanding_after(
    k_payments: int,
    principal: Decimal | int | float | str,
    annual_rate_pct: Decimal | int | float | str,
    months: int,
    currency: str | None = None,
    rounding_decimals: int = 2,
) -> dict[str, Any]:
    if k_payments < 0 or k_payments > months:
        raise ValueError("k_payments must be between zero and the total number of months.")
    schedule = amortization_schedule(principal, annual_rate_pct, months, currency, rounding_decimals)
    balance = _money(_decimal(principal), rounding_decimals) if k_payments == 0 else schedule["result"][k_payments - 1]["balance"]
    return _result(
        balance,
        "amortization_balance_after_k_payments",
        ["Build the monthly amortization schedule.", "Select the balance after the requested number of payments."],
        schedule["assumptions"],
        currency,
    )


def prepayment_cost(
    prepaid_amount: Decimal | int | float | str,
    charge_pct: Decimal | int | float | str,
    minimum_charge: Decimal | int | float | str = ZERO,
    currency: str | None = None,
    rounding_decimals: int = 2,
) -> dict[str, Any]:
    amount = _decimal(prepaid_amount)
    rate = _decimal(charge_pct)
    minimum = _decimal(minimum_charge)
    _positive("prepaid_amount", amount, allow_zero=True)
    _positive("charge_pct", rate, allow_zero=True)
    _positive("minimum_charge", minimum, allow_zero=True)
    percent_charge = amount * rate / HUNDRED
    charge = _money(max(percent_charge, minimum), rounding_decimals)
    return _result(
        charge,
        "maximum_of_percentage_charge_and_minimum",
        ["Percentage charge = prepaid amount * charge percentage / 100.", "Charge = maximum of percentage charge and minimum charge."],
        [f"Amounts are rounded to {rounding_decimals} decimal places.", "Any taxes or additional lender fees are excluded."],
        currency,
    )


def penal_charge(
    overdue_amount: Decimal | int | float | str,
    annual_penal_rate_pct: Decimal | int | float | str = ZERO,
    days: int = 0,
    day_count: int = 365,
    flat_penal_fee: Decimal | int | float | str = ZERO,
    currency: str | None = None,
    rounding_decimals: int = 2,
) -> dict[str, Any]:
    amount = _decimal(overdue_amount)
    annual_rate = _decimal(annual_penal_rate_pct)
    flat_fee = _decimal(flat_penal_fee)
    _positive("overdue_amount", amount, allow_zero=True)
    _positive("annual_penal_rate_pct", annual_rate, allow_zero=True)
    _positive("flat_penal_fee", flat_fee, allow_zero=True)
    if days < 0:
        raise ValueError("days must be non-negative.")
    if day_count <= 0:
        raise ValueError("day_count must be greater than zero.")
    interest = amount * annual_rate / HUNDRED * Decimal(days) / Decimal(day_count)
    interest = _money(interest, rounding_decimals)
    fee = _money(flat_fee, rounding_decimals)
    return _result(
        _money(interest + fee, rounding_decimals),
        "simple_penal_interest_plus_flat_fee",
        [
            "Simple penal interest = overdue amount * annual penal rate / 100 * days / day-count basis.",
            "Total penal charge = rounded simple interest + flat penal fee.",
        ],
        [f"Day-count basis is {day_count} days per year.", "No compounding or partial payment is assumed.", f"Amounts are rounded to {rounding_decimals} decimal places."],
        currency,
    )


def interest_only_monthly(
    principal: Decimal | int | float | str,
    annual_rate_pct: Decimal | int | float | str,
    currency: str | None = None,
    rounding_decimals: int = 2,
) -> dict[str, Any]:
    p = _decimal(principal)
    annual = _decimal(annual_rate_pct)
    _positive("principal", p)
    _positive("annual_rate_pct", annual, allow_zero=True)
    monthly_interest = _money(p * annual / HUNDRED / Decimal("12"), rounding_decimals)
    return _result(
        monthly_interest,
        "interest_only_monthly",
        ["Monthly interest = principal * annual rate / 100 / 12."],
        ["The principal is not amortized by the monthly interest payment.", f"Amounts are rounded to {rounding_decimals} decimal places."],
        currency,
    )


def flat_rate_total_interest(
    principal: Decimal | int | float | str,
    flat_rate_pct: Decimal | int | float | str,
    years: Decimal | int | float | str,
    currency: str | None = None,
    rounding_decimals: int = 2,
) -> dict[str, Any]:
    p = _decimal(principal)
    rate = _decimal(flat_rate_pct)
    term = _decimal(years)
    _positive("principal", p)
    _positive("flat_rate_pct", rate, allow_zero=True)
    _positive("years", term)
    interest = _money(p * rate / HUNDRED * term, rounding_decimals)
    return _result(
        interest,
        "flat_rate_simple_total_interest",
        ["Total flat-rate interest = principal * flat rate / 100 * years."],
        ["The flat rate is applied to the original principal for the full term.", "This is NOT comparable to a reducing-balance rate.", f"Amounts are rounded to {rounding_decimals} decimal places."],
        currency,
    )
