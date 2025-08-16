from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.shortcuts import render
from django.contrib import messages
from django.template.response import TemplateResponse

from .mixins import OwnerQuerysetMixin, OwnerCreateMixin, HtmxCrudMixin, is_htmx, OwnerUpdateMixin
from .models import Shop, Product
from .forms import ShopForm, ProductForm


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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user        # <<<<<< importante
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if is_htmx(self.request):
            ctx.update({"title": self.modal_title, "table_dom_id": self.table_dom_id})
        return ctx


class ShopUpdateView(OwnerUpdateMixin, OwnerQuerysetMixin, HtmxCrudMixin, UpdateView):
    model = Shop
    form_class = ShopForm
    template_name = "shared/_modal_form.html"   # <<<<<<<<<<
    modal_title = "Editar loja"
    list_partial_template = "cadastros/shops/_table.html"
    list_context_name = "shops"
    table_dom_id = "#shops-table"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user        # opcional, mas ok
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if is_htmx(self.request):
            ctx.update({"title": self.modal_title, "table_dom_id": self.table_dom_id})
        return ctx


class ShopDeleteView(OwnerQuerysetMixin, DeleteView):
    model = Shop
    success_url = reverse_lazy("cadastros:shop_list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return TemplateResponse(request, "shared/_confirm_delete.html", {
            "object": self.object,
            "table_dom_id": "#shops-table",
        })

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        qs = Shop.objects.filter(owner=request.user)
        response = render(request, "cadastros/shops/_table.html", {"shops": qs})
        response["HX-Trigger"] = "closeModal"
        return response


# =============== PRODUCTS ===============
class ProductListView(OwnerQuerysetMixin, ListView):
    model = Product
    template_name = "cadastros/products/list.html"
    context_object_name = "products"

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if is_htmx(request) and request.GET.get("fragment") == "table":
            return render(request, "cadastros/products/_table.html", {"products": self.object_list})
        return response


class ProductCreateView(OwnerCreateMixin, OwnerQuerysetMixin, HtmxCrudMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "shared/_modal_form.html"   # <<<<<<<<<<
    modal_title = "Novo produto/serviço"
    list_partial_template = "cadastros/products/_table.html"
    list_context_name = "products"
    table_dom_id = "#products-table"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if is_htmx(self.request):
            ctx.update({"title": self.modal_title, "table_dom_id": self.table_dom_id})
        return ctx


class ProductUpdateView(OwnerQuerysetMixin, HtmxCrudMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "shared/_modal_form.html"   # <<<<<<<<<<
    modal_title = "Editar produto/serviço"
    list_partial_template = "cadastros/products/_table.html"
    list_context_name = "products"
    table_dom_id = "#products-table"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if is_htmx(self.request):
            ctx.update({"title": self.modal_title, "table_dom_id": self.table_dom_id})
        return ctx


class ProductDeleteView(OwnerQuerysetMixin, DeleteView):
    model = Product
    success_url = reverse_lazy("cadastros:product_list")

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        qs = Product.objects.filter(owner=request.user)
        response = render(request, "cadastros/products/_table.html", {"products": qs})
        response["HX-Trigger"] = "closeModal"
        return response
