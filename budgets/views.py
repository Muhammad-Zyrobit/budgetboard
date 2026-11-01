from datetime import date

from rest_framework import permissions, status, viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .dashboard import budget_vs_actual, month_start
from .importer import import_csv
from .models import Budget, Category, CategoryRule, Transaction
from .serializers import (
    BudgetSerializer,
    CategoryRuleSerializer,
    CategorySerializer,
    ImportSummarySerializer,
    TransactionSerializer,
)


class UserScopedModelViewSet(viewsets.ModelViewSet):
    """Every queryset in this app is scoped to request.user. This is the
    multi-tenant-style isolation that keeps one user from ever seeing or
    editing another user's financial data, even by guessing an id."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CategoryViewSet(UserScopedModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class CategoryRuleViewSet(UserScopedModelViewSet):
    queryset = CategoryRule.objects.all()
    serializer_class = CategoryRuleSerializer


class TransactionViewSet(UserScopedModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer


class BudgetViewSet(UserScopedModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer


class ImportTransactionsView(APIView):
    """POST a CSV file (multipart form field 'file') to import and
    auto-categorize a batch of transactions in one request."""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        if file_obj is None:
            return Response(
                {"detail": "No file uploaded under field name 'file'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = import_csv(request.user, file_obj)
        serializer = ImportSummarySerializer(result.__dict__)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DashboardView(APIView):
    """GET /api/dashboard/?month=2026-10 -> budget-vs-actual breakdown for
    that month, defaulting to the current month."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        month_param = request.query_params.get("month")
        if month_param:
            try:
                month_date = date.fromisoformat(f"{month_param}-01")
            except ValueError:
                return Response(
                    {"detail": "month must be in YYYY-MM format."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            month_date = date.today()

        rows = budget_vs_actual(request.user, month_date)
        total_limit = sum((r["limit_amount"] for r in rows), start=0)
        total_actual = sum((r["actual_spend"] for r in rows), start=0)

        return Response(
            {
                "month": month_start(month_date).isoformat(),
                "categories": rows,
                "total_limit": total_limit,
                "total_actual": total_actual,
                "total_remaining": total_limit - total_actual,
            }
        )