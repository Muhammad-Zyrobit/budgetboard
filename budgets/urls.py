from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BudgetViewSet,
    CategoryRuleViewSet,
    CategoryViewSet,
    DashboardView,
    ImportTransactionsView,
    TransactionViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("category-rules", CategoryRuleViewSet, basename="categoryrule")
router.register("transactions", TransactionViewSet, basename="transaction")
router.register("budgets", BudgetViewSet, basename="budget")

urlpatterns = [
    path("", include(router.urls)),
    path("import/", ImportTransactionsView.as_view(), name="import-transactions"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]