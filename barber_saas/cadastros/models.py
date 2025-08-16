import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# ===== Mixins base =====
class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    class Meta:
        abstract = True

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class TenantQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(owner=user)

class TenantOwnedModel(UUIDModel, TimeStampedModel):
    """
    Todo registro pertence a um 'owner' (usuário/tenant).
    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="%(class)ss",
    )

    objects = TenantQuerySet.as_manager()

    class Meta:
        abstract = True
        indexes = [models.Index(fields=["owner"])]

    def clean(self):
        super().clean()
        if not self.owner_id:
            raise ValidationError("Defina 'owner' (tenant) no objeto.")


# ===== Domínio =====
class Shop(TenantOwnedModel):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32, blank=True)
    address = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("owner", "name")]
        indexes = [models.Index(fields=["owner", "is_active"])]

    def __str__(self):
        return f"{self.name}"


class StaffMembership(TenantOwnedModel):
    ROLE_OWNER = "owner"
    ROLE_MANAGER = "manager"
    ROLE_STAFF = "staff"
    ROLE_CHOICES = (
        (ROLE_OWNER, "Owner"),
        (ROLE_MANAGER, "Manager"),
        (ROLE_STAFF, "Staff"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default=ROLE_STAFF)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("user", "shop")]
        indexes = [models.Index(fields=["shop", "role", "is_active"])]

    def clean(self):
        super().clean()
        # Garante que o membership pertence ao mesmo owner da loja
        if self.shop and self.owner_id and self.shop.owner_id != self.owner_id:
            raise ValidationError("Membership.owner deve ser o mesmo owner da Shop.")

    def __str__(self):
        return f"{self.user} @ {self.shop} ({self.role})"


class Product(TenantOwnedModel):
    TYPE_SERVICE = "service"
    TYPE_RETAIL = "retail"
    TYPE_CHOICES = (
        (TYPE_SERVICE, "Serviço"),
        (TYPE_RETAIL, "Produto"),
    )

    name = models.CharField(max_length=140)
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_SERVICE)
    description = models.TextField(blank=True)
    default_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    # se False, espera-se override por loja em ProductPrice
    share_across_shops = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("owner", "name")]
        indexes = [
            models.Index(fields=["owner", "is_active"]),
            models.Index(fields=["owner", "type"]),
        ]

    def __str__(self):
        return self.name


class ProductPrice(TenantOwnedModel):
    """
    Override de preço por loja.
    Se existir para (product, shop), usar este preço; senão usar default_price do Product.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="shop_prices")
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="product_prices")
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = [("product", "shop")]
        indexes = [models.Index(fields=["shop"]), models.Index(fields=["product"])]

    def clean(self):
        super().clean()
        if self.product and self.owner_id and self.product.owner_id != self.owner_id:
            raise ValidationError("ProductPrice.owner deve ser o mesmo owner do Product.")
        if self.shop and self.owner_id and self.shop.owner_id != self.owner_id:
            raise ValidationError("ProductPrice.owner deve ser o mesmo owner da Shop.")

    def __str__(self):
        return f"{self.product} @ {self.shop}: {self.price}"
