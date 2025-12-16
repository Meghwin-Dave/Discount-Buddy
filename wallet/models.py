from decimal import Decimal

from django.db import models, transaction

from core.models import TimeStampedModel
from users.models import User


class Wallet(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self) -> str:
        return f"{self.user.email} Wallet"

    @transaction.atomic
    def credit(self, amount: Decimal, reason: str = ""):
        self.balance = self.balance + amount
        self.save(update_fields=["balance"])
        WalletTransaction.objects.create(
            wallet=self, amount=amount, transaction_type=WalletTransaction.CREDIT, reason=reason
        )

    @transaction.atomic
    def debit(self, amount: Decimal, reason: str = ""):
        if self.balance < amount:
            raise ValueError("Insufficient balance")
        self.balance = self.balance - amount
        self.save(update_fields=["balance"])
        WalletTransaction.objects.create(
            wallet=self, amount=amount, transaction_type=WalletTransaction.DEBIT, reason=reason
        )


class WalletTransaction(TimeStampedModel):
    CREDIT = "credit"
    DEBIT = "debit"
    TYPE_CHOICES = [(CREDIT, "Credit"), (DEBIT, "Debit")]

    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name="transactions"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.wallet.user.email} - {self.transaction_type} {self.amount}"


