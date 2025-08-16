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
