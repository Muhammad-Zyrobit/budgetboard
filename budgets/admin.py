from django.contrib import admin

from .models import Budget, Category, CategoryRule, Transaction

admin.site.register(Category)
admin.site.register(CategoryRule)
admin.site.register(Transaction)
admin.site.register(Budget)