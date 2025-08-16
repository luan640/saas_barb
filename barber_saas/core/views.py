from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView

from .forms import StoreForm, EmployeeForm, ProductForm
from .models import Store, Employee, Product


class StoreListView(ListView):
    model = Store
    template_name = 'core/store_list.html'


class StoreCreateView(CreateView):
    model = Store
    form_class = StoreForm
    template_name = 'core/store_form.html'
    success_url = reverse_lazy('core:store_list')


class EmployeeListView(ListView):
    model = Employee
    template_name = 'core/employee_list.html'


class EmployeeCreateView(CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'core/employee_form.html'
    success_url = reverse_lazy('core:employee_list')


class ProductListView(ListView):
    model = Product
    template_name = 'core/product_list.html'


class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'core/product_form.html'
    success_url = reverse_lazy('core:product_list')
