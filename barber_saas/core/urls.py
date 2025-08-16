from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('stores/', views.StoreListView.as_view(), name='store_list'),
    path('stores/new/', views.StoreCreateView.as_view(), name='store_create'),
    path('employees/', views.EmployeeListView.as_view(), name='employee_list'),
    path('employees/new/', views.EmployeeCreateView.as_view(), name='employee_create'),
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/new/', views.ProductCreateView.as_view(), name='product_create'),
]
