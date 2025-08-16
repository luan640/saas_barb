from django.urls import path
from . import views

app_name = "cadastros"

urlpatterns = [
    # Shops
    path("shops/", views.ShopListView.as_view(), name="shop_list"),
    path("shops/new/", views.ShopCreateView.as_view(), name="shop_create"),
    path("shops/<uuid:pk>/edit/", views.ShopUpdateView.as_view(), name="shop_update"),
    path("shops/<uuid:pk>/delete/", views.ShopDeleteView.as_view(), name="shop_delete"),

    # Funcionários (Memberships)
    path("memberships/", views.MembershipListView.as_view(), name="membership_list"),
    path("memberships/new/", views.MembershipCreateView.as_view(), name="membership_create"),
    path("memberships/<uuid:pk>/edit/", views.MembershipUpdateView.as_view(), name="membership_update"),
    path("memberships/<uuid:pk>/delete/", views.MembershipDeleteView.as_view(), name="membership_delete"),

    # Preços por loja
    path("product-prices/", views.ProductPriceListView.as_view(), name="product_price_list"),
    path("product-prices/new/", views.ProductPriceCreateView.as_view(), name="product_price_create"),
    path("product-prices/<uuid:pk>/edit/", views.ProductPriceUpdateView.as_view(), name="product_price_update"),
    path("product-prices/<uuid:pk>/delete/", views.ProductPriceDeleteView.as_view(), name="product_price_delete"),

    # Products
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/new/", views.ProductCreateView.as_view(), name="product_create"),
    path("products/<uuid:pk>/edit/", views.ProductUpdateView.as_view(), name="product_update"),
    path("products/<uuid:pk>/delete/", views.ProductDeleteView.as_view(), name="product_delete"),

    # Clientes
    path("clients/", views.ClientListView.as_view(), name="client_list"),
    path("clients/new/", views.ClientCreateView.as_view(), name="client_create"),
    path("clients/<uuid:pk>/edit/", views.ClientUpdateView.as_view(), name="client_update"),
    path("clients/<uuid:pk>/delete/", views.ClientDeleteView.as_view(), name="client_delete"),


]
