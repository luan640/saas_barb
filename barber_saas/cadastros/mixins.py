from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

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
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if hasattr(form.instance, "owner_id") and form.instance.owner_id is None:
            form.instance.owner = self.request.user
        return form

class HtmxCrudMixin:
    list_partial_template = None
    list_context_name = None
    table_dom_id = None
    modal_form_template = "shared/_modal_form.html"

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
            resp["HX-Trigger"] = "closeModal"
            return resp

        return super().form_valid(form)
