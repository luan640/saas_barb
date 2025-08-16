import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import TenantOwnedModel, UUIDModel, TimeStampedModel, TenantQuerySet

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


class Staff(TenantOwnedModel):
    """
    Perfil de funcionário por tenant (owner).
    Um mesmo 'user' pode ter perfis diferentes em tenants diferentes.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff_profiles",
    )
    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    document = models.CharField(max_length=20, blank=True)  # CPF/CNPJ
    birth_date = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)

    hire_date = models.DateField(null=True, blank=True)
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [("owner", "user")]  # 1 perfil por (tenant, user)
        indexes = [models.Index(fields=["owner", "is_active"])]

    def __str__(self):
        return self.full_name or getattr(self.user, "email", str(self.pk))


class StaffMembership(TenantOwnedModel):
    ROLE_OWNER = "owner"
    ROLE_MANAGER = "manager"
    ROLE_STAFF = "staff"
    ROLE_CHOICES = (
        (ROLE_OWNER, "Owner"),
        (ROLE_MANAGER, "Manager"),
        (ROLE_STAFF, "Staff"),
    )

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="memberships")
    shop = models.ForeignKey("cadastros.Shop", on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default=ROLE_STAFF)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("staff", "shop")]
        indexes = [models.Index(fields=["shop", "role", "is_active"])]

    def clean(self):
        super().clean()
        # compare por *_id para não disparar a carga do related quando None
        if self.shop_id and self.owner_id:
            # self.shop é seguro aqui (shop_id existe), mas guardamos mesmo assim
            if getattr(self.shop, "owner_id", None) != self.owner_id:
                raise ValidationError("Membership.owner deve ser o mesmo owner da Shop.")

        if self.staff_id and self.owner_id:
            # idem: só acessa staff se staff_id existir
            if getattr(self.staff, "owner_id", None) != self.owner_id:
                raise ValidationError("Membership.owner deve ser o mesmo owner do Staff.")

    def __str__(self):
        # não force acesso ao related quando o FK ainda não foi setado
        staff_name = ""
        if getattr(self, "staff_id", None):
            try:
                staff_name = self.staff.full_name or self.staff.user.email
            except Exception:
                staff_name = ""
        shop_name = ""
        if getattr(self, "shop_id", None):
            try:
                shop_name = self.shop.name
            except Exception:
                shop_name = ""
        return f"{staff_name} @ {shop_name} ({self.role})"


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


class Client(TenantOwnedModel):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)
        unique_together = [("owner", "phone")]  # evita duplicar telefone dentro do tenant
        indexes = [
            models.Index(fields=["owner", "name"]),
            models.Index(fields=["owner", "phone"]),
        ]

    def __str__(self):
        return self.name
