from django.contrib import admin

# Register your models here.
# expenses/admin.py
from .models import Expense

admin.site.register(Expense)
