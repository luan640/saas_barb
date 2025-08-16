from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from cadastros.models import Shop, Product, ProductPrice, Staff, Client
from core.models import TenantOwnedModel, UUIDModel, TimeStampedModel, TenantQuerySet


class ServiceOrder(TenantOwnedModel):
    STATUS_SCHEDULED = "scheduled"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_DONE = "done"
    STATUS_CANCELED = "canceled"
    STATUS_CHOICES = (
        (STATUS_SCHEDULED, "Agendado"),
        (STATUS_IN_PROGRESS, "Em andamento"),
        (STATUS_DONE, "Concluído"),
        (STATUS_CANCELED, "Cancelado"),
    )

    PAY_CASH = "cash"
    PAY_CARD = "card"
    PAY_PIX = "pix"
    PAY_TRANSFER = "transfer"
    PAY_OTHER = "other"
    PAYMENT_CHOICES = (
        (PAY_CASH, "Dinheiro"),
        (PAY_CARD, "Cartão"),
        (PAY_PIX, "PIX"),
        (PAY_TRANSFER, "Transferência"),
        (PAY_OTHER, "Outro"),
    )

    shop = models.ForeignKey(Shop, on_delete=models.PROTECT, related_name="service_orders")

    client = models.ForeignKey(Client, null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="orders")

    staff = models.ForeignKey(Staff, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders")

    scheduled_for = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS)
    payment_method = models.CharField(max_length=16, choices=PAYMENT_CHOICES, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["shop", "status", "scheduled_for"])]

    def clean(self):
        super().clean()
        if self.shop_id and self.owner_id and self.shop.owner_id != self.owner_id:
            raise ValidationError("A ordem deve pertencer ao mesmo owner da loja.")
        if self.discount_amount and self.discount_amount < 0:
            raise ValidationError("Desconto inválido.")
        if self.amount_paid and self.amount_paid < 0:
            raise ValidationError("Valor pago inválido.")

    def recalc_totals(self):
        items = self.items.all()
        self.subtotal = sum((it.qty * it.unit_price for it in items), Decimal("0.00"))
        self.total_amount = max(self.subtotal - (self.discount_amount or 0), Decimal("0.00"))

    def __str__(self):
        return f"{self.get_status_display()} - {self.customer_name or 'Cliente s/ nome'}"


class ServiceItem(TenantOwnedModel):
    order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="+")
    qty = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        indexes = [models.Index(fields=["order"])]

    def clean(self):
        super().clean()
        # valida tenant chain
        if self.order_id and self.owner_id and self.order.owner_id != self.owner_id:
            raise ValidationError("Item e Ordem devem pertencer ao mesmo owner.")
        if self.product_id and self.owner_id and self.product.owner_id != self.owner_id:
            raise ValidationError("Produto deve pertencer ao mesmo owner.")
        if self.qty <= 0:
            raise ValidationError("Quantidade deve ser positiva.")

    def autofill_price_if_needed(self):
        """Se unit_price for 0, tenta precificar a partir do ProductPrice da loja, senão default."""
        if self.unit_price and self.unit_price > 0:
            return
        shop = self.order.shop
        # tenta override
        pp = ProductPrice.objects.filter(owner=self.owner, product=self.product, shop=shop).first()
        self.unit_price = (pp.price if pp else self.product.default_price) or Decimal("0.00")

    def save(self, *args, **kwargs):
        creating = self._state.adding
        self.autofill_price_if_needed()
        super().save(*args, **kwargs)
        # Recalcula totais da ordem
        if self.order_id:
            self.order.recalc_totals()
            ServiceOrder.objects.filter(pk=self.order_id).update(
                subtotal=self.order.subtotal,
                total_amount=self.order.total_amount
            )
