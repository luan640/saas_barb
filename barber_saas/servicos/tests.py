from decimal import Decimal
import json

from django.contrib.auth import get_user_model

from django.test import TestCase

from cadastros.models import Shop, Staff, Client, Product
from servicos.models import ServiceOrder, ServiceItem

from .forms import ServiceOrderForm, ServiceItemForm


class CommaDecimalFieldFormTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("owner@example.com", "pass")
        self.staff_user = User.objects.create_user("staff@example.com", "pass")

        self.shop = Shop.objects.create(owner=self.owner, name="Shop")
        self.staff = Staff.objects.create(owner=self.owner, user=self.staff_user, full_name="Staff")
        self.client = Client.objects.create(owner=self.owner, name="Client")
        self.product = Product.objects.create(owner=self.owner, name="Prod", default_price=Decimal("0.00"))

        self.order = ServiceOrder.objects.create(
            owner=self.owner, shop=self.shop, staff=self.staff, client=self.client
        )

    def test_service_order_form_parses_comma_decimal(self):
        data = {
            "shop": self.shop.pk,
            "client": self.client.pk,
            "staff": self.staff.pk,
            "scheduled_for": "",
            "status": ServiceOrder.STATUS_IN_PROGRESS,
            "discount_amount": "10,50",
            "payment_method": "",
            "amount_paid": "20,75",
            "notes": "",
        }
        form = ServiceOrderForm(data=data, instance=ServiceOrder(owner=self.owner))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["discount_amount"], Decimal("10.50"))
        self.assertEqual(form.cleaned_data["amount_paid"], Decimal("20.75"))

    def test_service_order_form_initial_uses_comma(self):
        instance = ServiceOrder(
            owner=self.owner,
            shop=self.shop,
            staff=self.staff,
            client=self.client,
            discount_amount=Decimal("5.50"),
            amount_paid=Decimal("3.25"),
        )
        form = ServiceOrderForm(instance=instance)
        self.assertEqual(form.initial["discount_amount"], "5,50")
        self.assertEqual(form.initial["amount_paid"], "3,25")

    def test_service_item_form_parses_comma_decimal(self):
        data = {"product": self.product.pk, "qty": 1, "unit_price": "10,50"}
        form = ServiceItemForm(data=data, owner=self.owner)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["unit_price"], Decimal("10.50"))

    def test_service_item_form_initial_uses_comma(self):
        item = ServiceItem(
            owner=self.owner,
            order=self.order,
            product=self.product,
            qty=1,
            unit_price=Decimal("2.25"),
        )
        form = ServiceItemForm(instance=item, owner=self.owner)
        self.assertEqual(form.initial["unit_price"], "2,25")

    def test_service_item_form_exposes_price_mapping(self):
        form = ServiceItemForm(owner=self.owner)
        data_attr = form.fields["product"].widget.attrs.get("data-prices", "{}")
        prices = json.loads(data_attr)
        self.assertIn(str(self.product.pk), prices)
        self.assertEqual(prices[str(self.product.pk)], str(self.product.default_price))


