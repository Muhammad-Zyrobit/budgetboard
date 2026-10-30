from rest_framework import serializers

from .models import Budget, Category, CategoryRule, Transaction


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class CategoryRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryRule
        fields = ["id", "keyword", "category"]


class TransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "date",
            "description",
            "amount",
            "category",
            "category_name",
            "external_id",
        ]
        read_only_fields = ["external_id"]


class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Budget
        fields = ["id", "category", "category_name", "month", "limit_amount"]


class ImportSummarySerializer(serializers.Serializer):
    created = serializers.IntegerField()
    skipped_duplicate = serializers.IntegerField()
    skipped_invalid = serializers.IntegerField()
    errors = serializers.ListField(child=serializers.CharField())