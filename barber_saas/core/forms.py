from django import forms

from .models import Store, Employee, Product


class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ["name", "address", "phone"]


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["store", "first_name", "last_name", "email", "role"]


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["store", "name", "description", "price"]
