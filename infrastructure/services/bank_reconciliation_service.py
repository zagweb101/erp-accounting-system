"""
Bank Reconciliation Service — خدمة التسوية البنكية

تطابق بين كشوف الحسابات البنكية والمعاملات المسجلة في النظام.
Skeleton جاهز للتكامل مع API البنوك السعودية في v3.0+.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class BankTransaction:
    """معاملة بنكية من كشف الحساب."""
    date: datetime
    description: str
    amount: Decimal  # موجب = وارد، سالب = صادر
    balance_after: Decimal
    reference: str = ""
    matched: bool = False
    matched_invoice_no: str = ""


@dataclass
class ReconciliationResult:
    """نتيجة التسوية البنكية."""
    matched_transactions: list[dict] = field(default_factory=list)
    unmatched_bank: list[BankTransaction] = field(default_factory=list)
    unmatched_system: list[dict] = field(default_factory=list)
    bank_balance: Decimal = field(default_factory=lambda: Decimal("0"))
    system_balance: Decimal = field(default_factory=lambda: Decimal("0"))
    difference: Decimal = field(default_factory=lambda: Decimal("0"))
    reconciliation_date: datetime = field(default_factory=datetime.now)


class BankReconciliationService:
    """خدمة التسوية البنكية.

    تطابق المعاملات البنكية مع فواتير/مدفوعات النظام.
    Uses fuzzy matching on amount + date proximity.
    """

    def __init__(self, amount_tolerance: float = 0.01, date_tolerance_days: int = 3) -> None:
        self._amount_tolerance = Decimal(str(amount_tolerance))
        self._date_tolerance = date_tolerance_days

    def reconcile(
        self,
        bank_transactions: list[BankTransaction],
        system_payments: list[dict],
    ) -> ReconciliationResult:
        """تسوية بنكية.

        Args:
            bank_transactions: معاملات من كشف الحساب البنكي.
            system_payments: مدفوعات مسجلة في النظام.
                Each dict: {date, amount, invoice_no, description}

        Returns: ReconciliationResult with matched/unmatched.
        """
        result = ReconciliationResult()

        for bt in bank_transactions:
            match = self._find_match(bt, system_payments)
            if match:
                bt.matched = True
                bt.matched_invoice_no = match.get("invoice_no", "")
                result.matched_transactions.append({
                    "bank_transaction": {
                        "date": bt.date.isoformat(),
                        "description": bt.description,
                        "amount": str(bt.amount),
                    },
                    "system_payment": match,
                })
            else:
                result.unmatched_bank.append(bt)

        # Find unmatched system payments
        matched_invoice_nos = {m["system_payment"].get("invoice_no") for m in result.matched_transactions}
        for payment in system_payments:
            if payment.get("invoice_no") not in matched_invoice_nos:
                result.unmatched_system.append(payment)

        # Calculate balances
        result.bank_balance = bank_transactions[-1].balance_after if bank_transactions else Decimal("0")
        result.system_balance = sum(
            Decimal(str(p.get("amount", 0))) for p in system_payments
        )
        result.difference = result.bank_balance - result.system_balance

        return result

    def _find_match(
        self,
        bank_tx: BankTransaction,
        system_payments: list[dict],
    ) -> Optional[dict]:
        """البحث عن مطابقة لمعاملة بنكية في مدفوعات النظام."""
        for payment in system_payments:
            if payment.get("matched"):
                continue

            # Amount match (with tolerance)
            payment_amount = Decimal(str(abs(payment.get("amount", 0))))
            bank_amount = abs(bank_tx.amount)

            if abs(payment_amount - bank_amount) <= self._amount_tolerance:
                # Date proximity
                payment_date = payment.get("date")
                if isinstance(payment_date, str):
                    try:
                        payment_date = datetime.fromisoformat(payment_date)
                    except Exception:
                        payment_date = None

                if payment_date:
                    date_diff = abs((bank_tx.date - payment_date).days)
                    if date_diff <= self._date_tolerance:
                        payment["matched"] = True
                        return payment
                else:
                    # No date — match on amount only
                    payment["matched"] = True
                    return payment

        return None

    def parse_bank_statement_csv(self, filepath: str) -> list[BankTransaction]:
        """تحليل كشف حساب بنكي بصيغة CSV.

        Expected columns: date, description, amount, balance
        """
        import csv

        transactions = []
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    tx = BankTransaction(
                        date=datetime.strptime(row["date"], "%Y-%m-%d"),
                        description=row.get("description", ""),
                        amount=Decimal(row["amount"]),
                        balance_after=Decimal(row.get("balance", "0")),
                        reference=row.get("reference", ""),
                    )
                    transactions.append(tx)
                except (KeyError, ValueError):
                    continue

        return transactions

    def generate_reconciliation_report(self, result: ReconciliationResult) -> str:
        """توليد تقرير التسوية كنص."""
        report = [
            "═══════════════════════════════════════",
            "       تقرير التسوية البنكية",
            "═══════════════════════════════════════",
            f"التاريخ: {result.reconciliation_date.strftime('%Y-%m-%d %H:%M')}",
            "",
            f"✅ معاملات مطابقة: {len(result.matched_transactions)}",
            f"❌ معاملات بنكية غير مطابقة: {len(result.unmatched_bank)}",
            f"❌ مدفوعات نظام غير مطابقة: {len(result.unmatched_system)}",
            "",
            "─── الأرصدة ───",
            f"رصيد البنك:    {result.bank_balance:,.2f} ر.س",
            f"رصيد النظام:   {result.system_balance:,.2f} ر.س",
            f"الفرق:         {result.difference:,.2f} ر.س",
            "",
        ]

        if result.unmatched_bank:
            report.append("─── معاملات بنكية غير مطابقة ───")
            for tx in result.unmatched_bank[:10]:
                report.append(f"  {tx.date.strftime('%Y-%m-%d')} | {tx.amount:>10,.2f} | {tx.description[:40]}")

        if result.unmatched_system:
            report.append("\n─── مدفوعات نظام غير مطابقة ───")
            for p in result.unmatched_system[:10]:
                report.append(f"  {p.get('date', '?')} | {p.get('amount', 0):>10,.2f} | {p.get('invoice_no', '?')}")

        report.append("═══════════════════════════════════════")
        return "\n".join(report)
