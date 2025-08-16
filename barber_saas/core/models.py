from django.db import models


class Store(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self) -> str:
        return self.name


class Employee(models.Model):
    store = models.ForeignKey(Store, related_name='employees', on_delete=models.CASCADE)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    role = models.CharField(max_length=100, blank=True)

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Product(models.Model):
    store = models.ForeignKey(Store, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self) -> str:
        return self.name
