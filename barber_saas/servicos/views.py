from datetime import date
from django.db.models import Sum, Count, Q
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, CreateView, UpdateView, ListView
from django.http import HttpResponse
from django.template.loader import render_to_string

from cadastros.mixins import OwnerCreateMixin, OwnerUpdateMixin, OwnerQuerysetMixin, HtmxCrudMixin
from .models import ServiceOrder
from .forms import ServiceOrderForm, ServiceItemFormSet

# ---- DASHBOARD HOME ----
class HomeView(OwnerQuerysetMixin, TemplateView):
    template_name = "servicos/home.html"
    context_object_name = "orders"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        current_shop_id = self.request.session.get("current_shop_id")

        today = date.today()
        base = ServiceOrder.objects.filter(owner=user, created_at__date=today)
        if current_shop_id:
            base = base.filter(shop_id=current_shop_id)

        faturado = base.filter(status=ServiceOrder.STATUS_DONE).aggregate(
            total=Sum("total_amount")
        )["total"] or 0

        agendamentos = base.filter(status=ServiceOrder.STATUS_SCHEDULED).count()
        andamento = base.filter(status=ServiceOrder.STATUS_IN_PROGRESS).count()

        ctx["kpis"] = {
            "faturado_hoje": faturado,
            "agendados_hoje": agendamentos,
            "em_andamento": andamento,
        }

        # Listas
        qs_sched = ServiceOrder.objects.filter(owner=user, status=ServiceOrder.STATUS_SCHEDULED)
        qs_prog = ServiceOrder.objects.filter(owner=user, status=ServiceOrder.STATUS_IN_PROGRESS)
        if current_shop_id:
            qs_sched = qs_sched.filter(shop_id=current_shop_id)
            qs_prog = qs_prog.filter(shop_id=current_shop_id)

        ctx["scheduled"] = qs_sched.select_related("shop", "staff")
        ctx["in_progress"] = qs_prog.select_related("shop", "staff")
        return ctx

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data()
        if request.headers.get("HX-Request") == "true" and request.GET.get("fragment") in {"scheduled", "inprogress", "kpis"}:
            frag = request.GET["fragment"]
            if frag == "kpis":
                html = render_to_string("servicos/_kpis.html", ctx, request=request)
            elif frag == "scheduled":
                html = render_to_string("servicos/_orders_table.html", {"orders": ctx["scheduled"], "table_id": "orders-scheduled-table", "title": "Agendados"}, request=request)
            else:
                html = render_to_string("servicos/_orders_table.html", {"orders": ctx["in_progress"], "table_id": "orders-inprogress-table", "title": "Em andamento"}, request=request)
            return HttpResponse(html)
        return render(request, self.template_name, ctx)


# ---- CREATE / UPDATE (modal com formset) ----
class ServiceOrderCreateView(OwnerCreateMixin, OwnerQuerysetMixin, CreateView):
    model = ServiceOrder
    form_class = ServiceOrderForm
    template_name = "servicos/_order_modal.html"
    modal_title = "Nova comanda"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = ctx["form"]  # use a instância do form
        if self.request.method == "POST":
            ctx["formset"] = ServiceItemFormSet(
                self.request.POST, instance=form.instance, owner=self.request.user
            )
        else:
            ctx["formset"] = ServiceItemFormSet(
                instance=form.instance, owner=self.request.user
            )
        ctx["title"] = self.modal_title
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]
        if not formset.is_valid():
            return render(self.request, self.template_name,
                          {"form": form, "formset": formset, "title": self.modal_title}, status=200)
        self.object = form.save()
        formset.instance = self.object
        formset.save()
        self.object.recalc_totals(); self.object.save(update_fields=["subtotal", "total_amount"])

        resp = HttpResponse("")
        resp["HX-Trigger"] = '{"closeModal": true, "refreshOrdersScheduled": true, "refreshOrdersInProgress": true, "refreshKpis": true, "toast": "Comanda criada."}'
        return resp


class ServiceOrderUpdateView(OwnerUpdateMixin, OwnerQuerysetMixin, UpdateView):
    model = ServiceOrder
    form_class = ServiceOrderForm
    template_name = "servicos/_order_modal.html"
    modal_title = "Editar comanda"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = ctx["form"]
        if self.request.method == "POST":
            ctx["formset"] = ServiceItemFormSet(
                self.request.POST, instance=form.instance, owner=self.request.user
            )
        else:
            ctx["formset"] = ServiceItemFormSet(
                instance=form.instance, owner=self.request.user
            )
        ctx["title"] = self.modal_title
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]
        if not formset.is_valid():
            return render(self.request, self.template_name,
                          {"form": form, "formset": formset, "title": self.modal_title}, status=200)
        self.object = form.save()
        formset.save()
        self.object.recalc_totals(); self.object.save(update_fields=["subtotal", "total_amount"])

        resp = HttpResponse("")
        resp["HX-Trigger"] = '{"closeModal": true, "refreshOrdersScheduled": true, "refreshOrdersInProgress": true, "refreshKpis": true, "toast": "Comanda atualizada."}'
        return resp
