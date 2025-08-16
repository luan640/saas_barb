from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from collections import OrderedDict

from .models import Shop, StaffMembership, Product, ProductPrice, Staff, Client

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
        owner = kwargs.pop("owner", None)                # <- tira antes do super()
        self.current_user = kwargs.pop("current_user", None)  # <- opcional p/ quem usar
        super().__init__(*args, **kwargs)
        # injeta o owner ANTES da validação do ModelForm
        if owner and getattr(self.instance, "owner_id", None) is None:
            self.instance.owner = owner

# Formatações
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

class CommaDecimalField(forms.DecimalField):
    def to_python(self, value):
        if isinstance(value, str):
            value = value.replace(".", "").replace(",", ".")
        return super().to_python(value)

# ====== Forms ======
class ShopForm(TenantOwnedForm):
    class Meta:
        model = Shop
        fields = ["name", "phone", "address", "is_active"]

class StaffForm(TenantOwnedForm):
    class Meta:
        model = Staff
        fields = [
            "full_name", "phone", "document", "birth_date",
            "address", "hire_date", "commission_percent", "is_active", "notes"
        ]

    def save(self, commit=True):
        # Se for criação e não tiver user, vincula ao usuário autenticado
        if not self.instance.pk and self.current_user and not self.instance.user_id:
            self.instance.user = self.current_user
        return super().save(commit)

class StaffMembershipForm(TenantOwnedForm):
    """
    Cria/edita vínculo sem pedir 'user':
    - Em create: usa/gera Staff do usuário autenticado.
    - Em update: mantém 'staff' já vinculado.
    """
    class Meta:
        model = StaffMembership
        fields = ["shop", "role", "is_active"]  # sem 'staff' explícito

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        owner = getattr(self.instance, "owner", None)
        if owner:
            self.fields["shop"].queryset = Shop.objects.for_user(owner)

    def clean(self):
        data = super().clean()
        owner = getattr(self.instance, "owner", None)
        shop = data.get("shop")

        # resolve qual Staff será usado
        if self.instance.pk:
            staff = self.instance.staff
        else:
            # pega ou cria Staff do usuário autenticado neste tenant
            staff, _ = Staff.objects.get_or_create(
                owner=owner, user=self.current_user,
                defaults={"full_name": getattr(self.current_user, "get_full_name", lambda: "")() or self.current_user.email}
            )
            self.instance.staff = staff

        # valida duplicidade
        if shop and self.instance.staff_id:
            qs = StaffMembership.objects.filter(owner=owner, shop=shop, staff=self.instance.staff)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Este funcionário já está vinculado a esta loja.")
        return data

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

class StaffAndMembershipForm(TenantOwnedForm):
    """
    Cadastra funcionário (User + Staff por tenant) e cria o vínculo (Membership).
    Deixa o ModelForm mapear shop/role/is_active para a instância,
    e no save injeta self.instance.staff.
    """
    # campos extras (não pertencem ao model)
    email = forms.EmailField(label="E-mail do funcionário")
    full_name = forms.CharField(label="Nome completo", max_length=150)
    phone = forms.CharField(label="Telefone", max_length=32, required=False)

    class Meta:
        model = StaffMembership
        # >>> importante: mapear estes campos no instance ANTES da validação
        fields = ["shop", "role", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # injeta owner/current_user e instance.owner
        owner = getattr(self.instance, "owner", None)
        if owner:
            self.fields["shop"].queryset = Shop.objects.for_user(owner)

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean(self):
        data = super().clean()
        owner = getattr(self.instance, "owner", None)
        shop = data.get("shop")
        email = self.cleaned_data.get("email")

        if not owner:
            raise ValidationError("Owner não definido no formulário.")

        # evita duplicidade futura: se já existir staff desse e-mail nesse tenant + loja
        if shop and email:
            User = get_user_model()
            user = User.objects.filter(email=email).first()
            if user:
                staff = Staff.objects.filter(owner=owner, user=user).first()
                if staff and StaffMembership.objects.filter(owner=owner, shop=shop, staff=staff).exists():
                    raise ValidationError("Este funcionário já está vinculado a esta loja.")

        return data

    def save(self, commit=True):
        owner = getattr(self.instance, "owner")
        email = self.cleaned_data["email"]
        full_name = self.cleaned_data["full_name"]
        phone = self.cleaned_data.get("phone", "")

        User = get_user_model()

        # 1) User
        user, created_user = User.objects.get_or_create(
            email=email,
            defaults={"is_active": True}
        )
        if created_user:
            try:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            except Exception:
                pass

        # 2) Staff (perfil por tenant)
        staff, _ = Staff.objects.get_or_create(
            owner=owner,
            user=user,
            defaults={"full_name": full_name, "phone": phone, "is_active": True},
        )
        # atualiza dados básicos
        if full_name:
            staff.full_name = full_name
        if phone:
            staff.phone = phone
        if commit:
            staff.save()

        # 3) Vincula à instância e salva normalmente
        self.instance.staff = staff
        # shop/role/is_active já estão na instance porque estão em Meta.fields
        return super().save(commit)

class StaffAndMembershipUpdateForm(TenantOwnedForm):
    """
    Edita dados do funcionário (Staff) + vínculo (Membership) no mesmo modal.
    """
    email = forms.EmailField(label="E-mail", required=False)
    full_name = forms.CharField(label="Nome completo", max_length=150, required=False)
    phone = forms.CharField(label="Telefone", max_length=32, required=False)
    staff_is_active = forms.BooleanField(label="Funcionário ativo?", required=False)

    class Meta:
        model = StaffMembership
        fields = ["shop", "role", "is_active"]  # campos do vínculo

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # injeta owner e instance.owner
        owner = getattr(self.instance, "owner", None)
        if owner:
            self.fields["shop"].queryset = Shop.objects.for_user(owner)

        # Preenche iniciais a partir do Staff vinculado
        staff = getattr(self.instance, "staff", None)
        if staff:
            self.fields["email"].initial = getattr(staff.user, "email", "")
            self.fields["full_name"].initial = staff.full_name
            self.fields["phone"].initial = staff.phone
            self.fields["staff_is_active"].initial = staff.is_active

        # Reordenar campos: dados do funcionário primeiro
        ordered = OrderedDict()
        for name in ["email", "full_name", "phone", "staff_is_active", "shop", "role", "is_active"]:
            if name in self.fields:
                ordered[name] = self.fields[name]
        self.fields = ordered

    def clean(self):
        data = super().clean()
        # garantias de tenant já estão nos models.clean(); nada extra aqui
        return data

    def save(self, commit=True):
        # Atualiza Staff
        staff = self.instance.staff
        staff.full_name = self.cleaned_data.get("full_name") or staff.full_name
        staff.phone = self.cleaned_data.get("phone") or staff.phone
        staff.is_active = bool(self.cleaned_data.get("staff_is_active"))
        if commit:
            staff.save()

        # Salva Membership (shop/role/is_active já estão na instance)
        return super().save(commit)

class ClientForm(TenantOwnedForm):
    class Meta:
        model = Client
        fields = ["name", "phone", "is_active", "notes"]

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        # opcional: normalizar só dígitos
        # phone = re.sub(r"\D+", "", phone)
        return phone

    def clean(self):
        data = super().clean()
        # valida duplicidade por (owner, phone) de forma amigável (quando phone preenchido)
        owner = getattr(self.instance, "owner", None)
        phone = data.get("phone")
        if owner and phone:
            qs = Client.objects.filter(owner=owner, phone=phone)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("phone", "Já existe um cliente com este telefone.")
        return data
