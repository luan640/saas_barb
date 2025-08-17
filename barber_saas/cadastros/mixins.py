import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.template.loader import render_to_string  # <- precisa deste import
from django.http import HttpResponse

def is_htmx(request):
    return request.headers.get("HX-Request") == "true"

class OwnerQuerysetMixin(LoginRequiredMixin):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(owner=self.request.user)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.owner_id != self.request.user.id:
            raise PermissionDenied
        return obj

class OwnerCreateMixin(LoginRequiredMixin):
    """
    Para CreateView: garante que a instância inicial já tenha owner
    antes da validação do ModelForm (que chama model.clean()).
    Além disso, passa `owner` pro Form (TenantOwnedForm) filtrar FKs.
    """
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # passa para o Form (ex.: TenantOwnedForm)
        kwargs["owner"] = self.request.user

        # instancia com owner ANTES da validação
        inst = kwargs.get("instance")
        if inst is None:
            # CreateView normalmente passa instance=None; criamos uma já com owner
            kwargs["instance"] = self.model(owner=self.request.user)
        else:
            # fallback para qualquer caso atípico
            if getattr(inst, "owner_id", None) is None:
                inst.owner = self.request.user

        return kwargs

class OwnerUpdateMixin(LoginRequiredMixin):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user
        return kwargs

class CurrentShopMixin:
    """
    Lê a loja atual de ?shop=<uuid> ou da sessão.
    Guarda em self.current_shop_id e self.current_shop (opcional).
    """
    session_key = "current_shop_id"

    def dispatch(self, request, *args, **kwargs):
        shop_id = request.GET.get("shop") or request.session.get(self.session_key)
        if shop_id:
            request.session[self.session_key] = str(shop_id)
        self.current_shop_id = request.session.get(self.session_key)
        return super().dispatch(request, *args, **kwargs)

class HtmxCrudMixin:
    list_partial_template = None
    list_context_name = None
    table_dom_id = None
    modal_form_template = "shared/_modal_form.html"
    refresh_event = None

    def render_modal(self, context, status=200):
        return render(self.request, self.modal_form_template, context=context, status=status)

    def form_invalid(self, form):
        # >>> antes devolvia 400 — mude para 200 para o HTMX atualizar o modal
        ctx = {"form": form, "title": getattr(self, "modal_title", "Editar")}
        return self.render_modal(ctx, status=200)

    def form_valid(self, form):
        obj = form.save()
        if self.request.headers.get("HX-Request") == "true":
            queryset = self.model.objects.filter(owner=self.request.user)
            if hasattr(self, "filter_queryset_for_list"):
                queryset = self.filter_queryset_for_list(queryset)

            table_html = render_to_string(
                self.list_partial_template,
                {self.list_context_name: queryset},
                request=self.request,
            )

            div_id = (self.table_dom_id or "").lstrip("#")
            oob_html = f'<div id="{div_id}" hx-swap-oob="outerHTML">{table_html}</div>'

            resp = HttpResponse(oob_html)
            triggers = {"closeModal": True}
            if self.refresh_event:
                triggers[self.refresh_event] = True
            resp["HX-Trigger"] = json.dumps(triggers)
            return resp

        return super().form_valid(form)
