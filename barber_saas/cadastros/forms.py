from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from .models import Shop, StaffMembership, Product, ProductPrice

# ====== Base: aplica Bootstrap e marca campos inválidos ======
class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, f in self.fields.items():
            base = f.widget.attrs.get("class", "")
            f.widget.attrs["class"] = (base + " form-control").strip()
        # checkbox/boolean
        for name, f in self.fields.items():
            if isinstance(f.widget, (forms.CheckboxInput,)):
                f.widget.attrs["class"] = "form-check-input"

        # marca campos com erro
        for name in self.errors:
            if name in self.fields and not isinstance(self.fields[name].widget, forms.CheckboxInput):
                cls = self.fields[name].widget.attrs.get("class", "")
                self.fields[name].widget.attrs["class"] = (cls + " is-invalid").strip()

# NOVO: base para forms que “pertencem” ao tenant
class TenantOwnedForm(BootstrapModelForm):
    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        # injeta o owner ANTES da validação do ModelForm
        if owner and getattr(self.instance, "owner_id", None) is None:
            self.instance.owner = owner

# ====== Forms ======
class ShopForm(TenantOwnedForm):
    class Meta:
        model = Shop
        fields = ["name", "phone", "address", "is_active"]


class StaffMembershipForm(TenantOwnedForm):
    """
    Exige 'owner' no __init__ para filtrar shops do dono.
    """
    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        if owner:
            self.fields["shop"].queryset = Shop.objects.for_user(owner)

    class Meta:
        model = StaffMembership
        fields = ["user", "shop", "role", "is_active"]

    def clean(self):
        data = super().clean()
        shop = data.get("shop")
        owner = getattr(self.instance, "owner", None) or self.initial.get("owner")
        # Se estiver criando, o owner virá da view no form_valid; aqui validamos se já existir
        if owner and shop and shop.owner_id != owner.id:
            raise ValidationError("A loja selecionada não pertence a este dono.")
        return data

class CommaDecimalField(forms.DecimalField):
    def to_python(self, value):
        if isinstance(value, str):
            value = value.replace(".", "").replace(",", ".")
        return super().to_python(value)

class ProductForm(TenantOwnedForm):
    default_price = CommaDecimalField(min_value=0)

    class Meta:
        model = Product
        fields = ["name", "type", "description", "default_price", "share_across_shops", "is_active"]

    def clean_default_price(self):
        v = self.cleaned_data["default_price"]
        if v is None or v < 0:
            raise ValidationError("Preço deve ser zero ou positivo.")
        return v


class ProductPriceForm(TenantOwnedForm):
    """
    Exige 'owner' no __init__ para filtrar product/shop do dono.
    """
    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        if owner:
            self.fields["product"].queryset = Product.objects.for_user(owner)
            self.fields["shop"].queryset = Shop.objects.for_user(owner)

    class Meta:
        model = ProductPrice
        fields = ["product", "shop", "price"]

    def clean_price(self):
        v = self.cleaned_data["price"]
        if v is None or v < 0:
            raise ValidationError("Preço deve ser zero ou positivo.")
        return v

    def clean(self):
        data = super().clean()
        product, shop = data.get("product"), data.get("shop")
        # valida coerência de tenant (extra, além do models.clean)
        if product and shop and product.owner_id != shop.owner_id:
            raise ValidationError("Produto e Loja devem pertencer ao mesmo dono.")
        return data
