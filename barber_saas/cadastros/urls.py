from django.urls import path
from . import views

app_name = "cadastros"

urlpatterns = [
    # Shops
    path("shops/", views.ShopListView.as_view(), name="shop_list"),
    path("shops/new/", views.ShopCreateView.as_view(), name="shop_create"),
    path("shops/<uuid:pk>/edit/", views.ShopUpdateView.as_view(), name="shop_update"),
    path("shops/<uuid:pk>/delete/", views.ShopDeleteView.as_view(), name="shop_delete"),

    # Products
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/new/", views.ProductCreateView.as_view(), name="product_create"),
    path("products/<uuid:pk>/edit/", views.ProductUpdateView.as_view(), name="product_update"),
    path("products/<uuid:pk>/delete/", views.ProductDeleteView.as_view(), name="product_delete"),
]
