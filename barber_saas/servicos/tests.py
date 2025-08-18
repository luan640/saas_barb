from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from cadastros.models import Shop, Product
from .models import ServiceOrder
from .forms import ServiceItemForm


class ServiceItemFormTests(TestCase):
    def test_autofill_price_when_not_provided(self):
        User = get_user_model()
        owner = User.objects.create_user("owner@example.com", "pw12345")
        shop = Shop.objects.create(owner=owner, name="Main Shop")
        product = Product.objects.create(
            owner=owner, name="Corte", default_price=Decimal("25.00")
        )
        order = ServiceOrder.objects.create(owner=owner, shop=shop)

        form = ServiceItemForm(
            data={"product": product.pk, "qty": 1, "unit_price": ""}, owner=owner
        )
        self.assertTrue(form.is_valid())

        item = form.save(commit=False)
        item.order = order
        item.owner = owner
        item.save()

        self.assertEqual(item.unit_price, product.default_price)
        order.refresh_from_db()
        self.assertEqual(order.subtotal, product.default_price)
