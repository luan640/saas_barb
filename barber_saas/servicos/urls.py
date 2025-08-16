from django.urls import path
from .views import HomeView, ServiceOrderCreateView, ServiceOrderUpdateView

app_name = "servicos"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("orders/new/", ServiceOrderCreateView.as_view(), name="order_create"),
    path("orders/<uuid:pk>/edit/", ServiceOrderUpdateView.as_view(), name="order_update"),
]
