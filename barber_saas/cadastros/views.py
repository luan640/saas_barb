import json
from decimal import Decimal, InvalidOperation

from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.shortcuts import render, redirect
from django.contrib import messages
from django.template.response import TemplateResponse
from django.template.loader import render_to_string
from django.db.models import Q
from django.http import HttpResponse

from .mixins import OwnerQuerysetMixin, OwnerCreateMixin, HtmxCrudMixin, is_htmx, OwnerUpdateMixin, CurrentShopMixin
from .models import Shop, Product, StaffMembership, ProductPrice, Staff, Client
from .forms import ShopForm, ProductForm, StaffMembershipForm, ProductPriceForm, StaffForm, StaffAndMembershipForm, StaffAndMembershipUpdateForm, ClientForm

# =============== SHOPS ===============
class ShopListView(OwnerQuerysetMixin, ListView):
    model = Shop
    template_name = "cadastros/shops/list.html"
    context_object_name = "shops"

    def get(self, request, *args, **kwargs):
        """
        Se for HTMX e pedir apenas a tabela, devolve só o fragmento.
        (útil quando recarregamos a lista após salvar/apagar)
        """
        response = super().get(request, *args, **kwargs)
        if is_htmx(request) and request.GET.get("fragment") == "table":
            return render(request, "cadastros/shops/_table.html", {"shops": self.object_list})
        return response


class ShopCreateView(OwnerCreateMixin, OwnerQuerysetMixin, HtmxCrudMixin, CreateView):
    model = Shop
    form_class = ShopForm
    template_name = "shared/_modal_form.html"   # <<<<<<<<<<
    modal_title = "Nova loja"
    list_partial_template = "cadastros/shops/_table.html"
    list_context_name = "shops"
    table_dom_id = "#shops-table"
    refresh_event = "refreshShopsTable"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user        # <<<<<< importante
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if is_htmx(self.request):
            ctx.update({
                "title": self.modal_title,
                "table_dom_id": self.table_dom_id,
                "refresh_event": self.refresh_event,
            })
        return ctx


class ShopUpdateView(OwnerUpdateMixin, OwnerQuerysetMixin, HtmxCrudMixin, UpdateView):
    model = Shop
    form_class = ShopForm
    template_name = "shared/_modal_form.html"   # <<<<<<<<<<
    modal_title = "Editar loja"
    list_partial_template = "cadastros/shops/_table.html"
    list_context_name = "shops"
    table_dom_id = "#shops-table"
    refresh_event = "refreshShopsTable"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user        # opcional, mas ok
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if is_htmx(self.request):
            ctx.update({
                "title": self.modal_title,
                "table_dom_id": self.table_dom_id,
                "refresh_event": self.refresh_event,
            })
        return ctx


class ShopDeleteView(OwnerQuerysetMixin, DeleteView):
    model = Shop
    success_url = reverse_lazy("cadastros:shop_list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return TemplateResponse(request, "shared/_confirm_delete.html", {
            "object": self.object,
            "table_dom_id": "#shops-table",
            "refresh_event": "refreshShopsTable",
        })

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        resp = HttpResponse("")
        resp["HX-Trigger"] = json.dumps({"closeModal": True, "refreshShopsTable": True})
        return resp


# =============== PRODUCTS ===============
class ProductListView(OwnerQuerysetMixin, ListView):
    model = Product
    template_name = "cadastros/products/list.html"
    context_object_name = "products"
    paginate_by = 12  # se quiser paginação

    def _to_decimal(self, v):
        if not v:
            return None
        # aceita "10,50" ou "10.50"
        v = str(v).replace(".", "").replace(",", ".") if "," in str(v) else str(v)
        try:
            return Decimal(v)
        except InvalidOperation:
            return None

    def get_queryset(self):
        qs = super().get_queryset().filter(owner=self.request.user)

        q = self.request.GET.get("q", "").strip()
        type_ = self.request.GET.get("type", "").strip()
        shared = self.request.GET.get("shared", "").strip()   # "", "1", "0"
        active = self.request.GET.get("active", "").strip()   # "", "1", "0"
        pmin = self._to_decimal(self.request.GET.get("price_min"))
        pmax = self._to_decimal(self.request.GET.get("price_max"))

        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        if type_:
            qs = qs.filter(type=type_)
        if shared in ("0", "1"):
            qs = qs.filter(share_across_shops=(shared == "1"))
        if active in ("0", "1"):
            qs = qs.filter(is_active=(active == "1"))
        if pmin is not None:
            qs = qs.filter(default_price__gte=pmin)
        if pmax is not None:
            qs = qs.filter(default_price__lte=pmax)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # valores atuais para preencher os inputs
        ctx["filters"] = {
            "q": self.request.GET.get("q", ""),
            "type": self.request.GET.get("type", ""),
            "shared": self.request.GET.get("shared", ""),
            "active": self.request.GET.get("active", ""),
            "price_min": self.request.GET.get("price_min", ""),
            "price_max": self.request.GET.get("price_max", ""),
        }
        ctx["type_choices"] = Product._meta.get_field("type").choices
        return ctx

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        # quando pedirem só o fragmento, devolve apenas a parcial
        if request.headers.get("HX-Request") == "true" and request.GET.get("fragment") == "table":
            return render(request, "cadastros/products/_table.html", self.get_context_data())
        return response


class ProductCreateView(OwnerCreateMixin, OwnerQuerysetMixin, HtmxCrudMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "shared/_modal_form.html"   # <<<<<<<<<<
    modal_title = "Novo produto/serviço"
    list_partial_template = "cadastros/products/_table.html"
    list_context_name = "products"
    table_dom_id = "#products-table"
    refresh_event = "refreshProductsTable"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if is_htmx(self.request):
            ctx.update({
                "title": self.modal_title,
                "table_dom_id": self.table_dom_id,
                "refresh_event": self.refresh_event,
            })
        return ctx


class ProductUpdateView(OwnerQuerysetMixin, HtmxCrudMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "shared/_modal_form.html"   # <<<<<<<<<<
    modal_title = "Editar produto/serviço"
    list_partial_template = "cadastros/products/_table.html"
    list_context_name = "products"
    table_dom_id = "#products-table"
    refresh_event = "refreshProductsTable"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if is_htmx(self.request):
            ctx.update({
                "title": self.modal_title,
                "table_dom_id": self.table_dom_id,
                "refresh_event": self.refresh_event,
            })
        return ctx


class ProductDeleteView(OwnerQuerysetMixin, DeleteView):
    model = Product
    template_name = "shared/_confirm_delete.html"
    modal_title = "Excluir produto"
    list_partial_template = "cadastros/products/_table.html"
    list_context_name = "products"
    table_dom_id = "#products-table"
    success_url = reverse_lazy("cadastros:product_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"title": self.modal_title, "refresh_event": "refreshProductsTable"})
        return ctx

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()

        is_htmx = request.headers.get("HX-Request") or request.META.get("HTTP_HX_REQUEST")
        if is_htmx:
            queryset = self.model.objects.filter(owner=request.user)

            table_html = render_to_string(
                self.list_partial_template,
                {self.list_context_name: queryset},
                request=request,
            )
            div_id = (self.table_dom_id or "").lstrip("#")
            oob_html = f'<div id="{div_id}" hx-swap-oob="outerHTML">{table_html}</div>'

            resp = HttpResponse(oob_html)
            resp["HX-Trigger"] = json.dumps({"closeModal": True, "refreshProductsTable": True, "toast": "Excluído."})
            return resp

        # Fallback SSR
        return redirect(self.success_url)

# ========= FUNCIONÁRIOS (MEMBERSHIPS) =========
class MembershipListView(OwnerQuerysetMixin, CurrentShopMixin, ListView):
    model = StaffMembership
    template_name = "cadastros/memberships/list.html"
    context_object_name = "memberships"

    def get_queryset(self):
        qs = super().get_queryset()\
            .select_related("staff", "staff__user", "shop")  # << aqui
        if self.current_shop_id:
            qs = qs.filter(shop_id=self.current_shop_id)
        return qs

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if is_htmx(request) and request.GET.get("fragment") == "table":
            return render(request, "cadastros/memberships/_table.html", {"memberships": self.object_list})
        return response


class MembershipCreateView(OwnerCreateMixin, OwnerQuerysetMixin, HtmxCrudMixin, CreateView):
    model = StaffMembership
    form_class = StaffAndMembershipForm      # <<< combinado
    template_name = "shared/_modal_form.html"
    modal_title = "Cadastrar funcionário e vincular à loja"
    list_partial_template = "cadastros/memberships/_table.html"
    list_context_name = "memberships"
    table_dom_id = "#memberships-table"
    refresh_event = "refreshMembershipsTable"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"title": self.modal_title})
        if is_htmx(self.request):
            ctx.update({"refresh_event": self.refresh_event, "table_dom_id": self.table_dom_id})
        return ctx

    def get_initial(self):
        initial = super().get_initial()
        shop_id = self.request.session.get("current_shop_id")
        if shop_id:
            initial["shop"] = shop_id
        return initial


class MembershipUpdateView(OwnerQuerysetMixin, HtmxCrudMixin, UpdateView):
    model = StaffMembership
    form_class = StaffAndMembershipUpdateForm   # <<< trocar aqui
    template_name = "shared/_modal_form.html"
    modal_title = "Editar meu vínculo"
    list_partial_template = "cadastros/memberships/_table.html"
    list_context_name = "memberships"
    table_dom_id = "#memberships-table"
    refresh_event = "refreshMembershipsTable"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user
        # mantém o user já vinculado ao registro (não troca para o request.user à força)
        # kwargs["current_user"] = self.get_object().user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if is_htmx(self.request):
            ctx.update({
                "title": self.modal_title,
                "table_dom_id": self.table_dom_id,
                "refresh_event": self.refresh_event,
            })
        return ctx


class MembershipDeleteView(OwnerQuerysetMixin, CurrentShopMixin, DeleteView):
    model = StaffMembership
    template_name = "shared/_confirm_delete.html"

    def get_success_url(self):
        url = reverse("cadastros:membership_list")
        if self.current_shop_id:
            url += f"?shop={self.current_shop_id}"
        return url

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["refresh_event"] = "refreshMembershipsTable"
        ctx["title"] = "Excluir vínculo"
        return ctx

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if is_htmx(request):
            resp = HttpResponse("")
            resp["HX-Trigger"] = json.dumps({"closeModal": True, "refreshMembershipsTable": True})
            return resp
        return redirect(self.get_success_url())

# ============= STAFFS =========

class StaffListView(OwnerQuerysetMixin, ListView):
    model = Staff
    template_name = "cadastros/staff/list.html"
    context_object_name = "staffs"


class StaffCreateView(OwnerCreateMixin, OwnerQuerysetMixin, HtmxCrudMixin, CreateView):
    model = Staff
    form_class = StaffForm
    template_name = "shared/_modal_form.html"
    modal_title = "Novo funcionário"
    list_partial_template = "cadastros/staff/_table.html"
    list_context_name = "staffs"
    table_dom_id = "#staff-table"
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["current_user"] = self.request.user  # default: cria perfil para o próprio user
        return kwargs


class StaffUpdateView(OwnerQuerysetMixin, HtmxCrudMixin, UpdateView):
    model = Staff
    form_class = StaffForm
    template_name = "shared/_modal_form.html"
    modal_title = "Editar funcionário"
    list_partial_template = "cadastros/staff/_table.html"
    list_context_name = "staffs"
    table_dom_id = "#staff-table"

# ========= PREÇOS POR LOJA (overrides) =========
class ProductPriceListView(OwnerQuerysetMixin, CurrentShopMixin, ListView):
    model = ProductPrice
    template_name = "cadastros/product_prices/list.html"
    context_object_name = "prices"

    def get_queryset(self):
        qs = super().get_queryset().select_related("product", "shop")
        # filtra por loja atual, se houver
        if self.current_shop_id:
            qs = qs.filter(shop_id=self.current_shop_id)
        # opcional: filtrar por produto via ?product=<uuid>
        product_id = self.request.GET.get("product")
        if product_id:
            qs = qs.filter(product_id=product_id)
        return qs


class ProductPriceCreateView(OwnerCreateMixin, CurrentShopMixin, CreateView):
    model = ProductPrice
    form_class = ProductPriceForm
    template_name = "cadastros/product_prices/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if self.current_shop_id:
            initial["shop"] = self.current_shop_id
        product_id = self.request.GET.get("product")
        if product_id:
            initial["product"] = product_id
        return initial

    def get_success_url(self):
        messages.success(self.request, "Preço por loja criado.")
        url = reverse("cadastros:product_price_list")
        params = []
        if self.current_shop_id:
            params.append(f"shop={self.current_shop_id}")
        product_id = self.request.GET.get("product")
        if product_id:
            params.append(f"product={product_id}")
        if params:
            url += "?" + "&".join(params)
        return url


class ProductPriceUpdateView(OwnerQuerysetMixin, CurrentShopMixin, UpdateView):
    model = ProductPrice
    form_class = ProductPriceForm
    template_name = "cadastros/product_prices/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user
        return kwargs

    def get_success_url(self):
        messages.success(self.request, "Preço por loja atualizado.")
        url = reverse("cadastros:product_price_list")
        if self.current_shop_id:
            url += f"?shop={self.current_shop_id}"
        return url


class ProductPriceDeleteView(OwnerQuerysetMixin, CurrentShopMixin, DeleteView):
    model = ProductPrice
    template_name = "cadastros/product_prices/confirm_delete.html"

    def get_success_url(self):
        url = reverse("cadastros:product_price_list")
        if self.current_shop_id:
            url += f"?shop={self.current_shop_id}"
        return url

# ========= Clientes ========
class ClientListView(OwnerQuerysetMixin, ListView):
    model = Client
    template_name = "cadastros/clients/list.html"
    context_object_name = "clients"
    paginate_by = 12

    def get(self, request, *args, **kwargs):
        resp = super().get(request, *args, **kwargs)
        # fragmento só da tabela (usado em refresh via evento)
        if request.headers.get("HX-Request") == "true" and request.GET.get("fragment") == "table":
            ctx = self.get_context_data()
            html = render_to_string("cadastros/clients/_table.html", ctx, request=request)
            return HttpResponse(html)
        return resp


class ClientCreateView(OwnerCreateMixin, OwnerQuerysetMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = "shared/_modal_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Novo cliente"
        ctx["refresh_event"] = "refreshClientsTable"
        return ctx

    def form_valid(self, form):
        self.object = form.save()
        resp = HttpResponse("")
        resp["HX-Trigger"] = '{"toast": "Cliente salvo."}'
        return resp


class ClientUpdateView(OwnerUpdateMixin, OwnerQuerysetMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = "shared/_modal_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Editar cliente"
        ctx["refresh_event"] = "refreshClientsTable"
        return ctx

    def form_valid(self, form):
        self.object = form.save()
        resp = HttpResponse("")
        resp["HX-Trigger"] = '{"toast": "Cliente atualizado."}'
        return resp


class ClientDeleteView(OwnerQuerysetMixin, DeleteView):
    model = Client
    template_name = "shared/_confirm_delete.html"
    success_url = reverse_lazy("cadastros:client_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Excluir cliente"
        return ctx

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()

        is_htmx = request.headers.get("HX-Request") or request.META.get("HTTP_HX_REQUEST")
        if is_htmx:
            resp = HttpResponse("")
            resp["HX-Trigger"] = '{"closeModal": true, "refreshClientsTable": true, "toast": "Cliente excluído."}'
            return resp
        return redirect(self.success_url)
