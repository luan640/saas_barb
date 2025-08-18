from django import forms
from django.forms import inlineformset_factory
from cadastros.models import Shop, Product, Staff
from .models import ServiceOrder, ServiceItem, Client
from cadastros.forms import (
    TenantOwnedForm,
    CommaDecimalField,
)  # sua base que injeta owner/current_user
from django.forms.models import BaseInlineFormSet  # <- importante

class ServiceOrderForm(TenantOwnedForm):
    amount_paid = CommaDecimalField(required=False)
    discount_amount = CommaDecimalField(required=False)
    class Meta:
        model = ServiceOrder
        fields = [
            "shop", "client",
            "staff", "scheduled_for", "status",
            "discount_amount", "payment_method", "amount_paid", "notes",
        ]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        owner = getattr(self.instance, "owner", None)
        if owner:
            self.fields["shop"].queryset = Shop.objects.for_user(owner)
            self.fields["staff"].queryset = Staff.objects.filter(owner=owner, is_active=True)
            self.fields["client"].queryset = Client.objects.filter(owner=owner, is_active=True).order_by("name")
        if not self.instance.pk:
            self.fields["status"].initial = ServiceOrder.STATUS_IN_PROGRESS

        for name in ("amount_paid", "discount_amount"):
            val = self.initial.get(name)
            if val not in (None, ""):
                self.initial[name] = str(val).replace(".", ",")

    def save(self, commit=True):
        obj = super().save(commit=False)
        # sempre sincroniza nome/telefone do cliente selecionado
        obj.sync_customer_from_client()
        if commit:
            obj.save()
        return obj

class ServiceItemForm(TenantOwnedForm):
    unit_price = CommaDecimalField(required=False)


    class Meta:
        model = ServiceItem
        fields = ["product", "qty", "unit_price"]

    def __init__(self, *args, owner=None, current_user=None, **kwargs):
        """
        owner/current_user chegam do OwnerInlineFormSet.
        Mesmo quando instance.owner ainda não existe (linhas novas),
        usamos o 'owner' passado para filtrar os produtos.
        """
        # guarda antes do super()
        self._owner_override = owner
        super().__init__(*args, owner=owner, current_user=current_user, **kwargs)

        # tenta pegar do instance (quando edição) ou do override (quando criação)
        owner_obj = getattr(self.instance, "owner", None) or self._owner_override

        # Se você tem um manager .for_user, use; senão filtre por owner/is_active
        if owner_obj:
            try:
                qs = Product.objects.for_user(owner_obj).filter(is_active=True)
            except AttributeError:
                qs = Product.objects.filter(owner=owner_obj, is_active=True)
        else:
            qs = Product.objects.none()

        self.fields["product"].queryset = qs

        val = self.initial.get("unit_price")
        if val not in (None, ""):
            self.initial["unit_price"] = str(val).replace(".", ",")

class OwnerInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, owner=None, current_user=None, **kwargs):
        self._owner = owner
        self._current_user = current_user
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs.setdefault("owner", self._owner)
        kwargs.setdefault("current_user", self._current_user)
        return super()._construct_form(i, **kwargs)

ServiceItemFormSet = inlineformset_factory(
    ServiceOrder, ServiceItem,
    form=ServiceItemForm,
    formset=OwnerInlineFormSet,   # <- usa o formset custom
    extra=3, can_delete=True, min_num=1, validate_min=True
)
