import copy
import logging
from datetime import datetime

from django.conf import settings
from django.db.models import Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from usaspending_api.awards.v2.filters.sub_award import subaward_filter
from usaspending_api.awards.v2.filters.view_selector import spending_over_time
from usaspending_api.common.api_versioning import api_transformations, API_TRANSFORM_FUNCTIONS
from usaspending_api.common.cache_decorator import cache_response
from usaspending_api.common.exceptions import InvalidParameterException
from usaspending_api.common.helpers.sql_helpers import FiscalMonth, FiscalQuarter, FiscalYear
from usaspending_api.common.helpers.generic_helper import (
    generate_date_ranged_results_from_queryset, generate_fiscal_year)
from usaspending_api.core.validator.award_filter import AWARD_FILTER
from usaspending_api.core.validator.pagination import PAGINATION
from usaspending_api.core.validator.tinyshield import TinyShield


logger = logging.getLogger(__name__)

API_VERSION = settings.API_VERSION


@api_transformations(api_version=API_VERSION, function_list=API_TRANSFORM_FUNCTIONS)
class SpendingOverTimeVisualizationViewSet(APIView):
    """
    This route takes award filters, and returns spending by time. The amount of time is denoted by the "group" value.
    endpoint_doc: /advanced_award_search/spending_over_time.md
    """

    def validate_request_data(self, json_data):
        self.groupings = {
            "quarter": "quarter",
            "q": "quarter",
            "fiscal_year": "fiscal_year",
            "fy": "fiscal_year",
            "month": "month",
            "m": "month",
        }
        models = [
            {"name": "subawards", "key": "subawards", "type": "boolean", "default": False},
            {"name": "sparse", "key": "sparse", "type": "boolean", "default": True},
            {
                "name": "group",
                "key": "group",
                "type": "enum",
                "enum_values": list(self.groupings.keys()),
                "default": "fy",
                "optional": False,  # allow to be optional in the future
            },
        ]
        models.extend(copy.deepcopy(AWARD_FILTER))
        models.extend(copy.deepcopy(PAGINATION))
        validated_data = TinyShield(models).block(json_data)

        if validated_data.get("filters", None) is None:
            raise InvalidParameterException("Missing request parameters: filters")

        return validated_data

    def database_data_layer(self):
        if self.subawards:
            queryset = subaward_filter(self.filters)
            obligation_column = "amount"
        else:
            queryset = spending_over_time(self.filters)
            obligation_column = "generated_pragmatic_obligation"

        values = ["fy"]
        if self.groupings[self.group] == "month":
            queryset = queryset.annotate(month=FiscalMonth("action_date"), fy=FiscalYear("action_date"))
            values.append("month")

        elif self.groupings[self.group] == "quarter":
            queryset = queryset.annotate(quarter=FiscalQuarter("action_date"), fy=FiscalYear("action_date"))
            values.append("quarter")

        elif self.groupings[self.group] == "fiscal_year":
            queryset = queryset.annotate(fy=FiscalYear("action_date"))

        queryset = (
            queryset.values(*values)
            .annotate(aggregated_amount=Sum(obligation_column))
            .order_by(*["{}".format(value) for value in values])
        )

        return queryset, values

    @cache_response()
    def post(self, request):
        json_request = self.validate_request_data(request.data)
        self.group = json_request["group"]
        self.subawards = json_request["subawards"]
        self.filters = json_request["filters"]

        results, values = self.database_data_layer()

        # time_period is optional so we're setting a default window from API_SEARCH_MIN_DATE to end of the current FY.
        # Otherwise, users will see blank results for years
        default_time_period = {'start_date': settings.API_SEARCH_MIN_DATE,
                               'end_date': '{}-09-30'.format(generate_fiscal_year(datetime.utcnow()))}
        time_periods = self.filters.get('time_period', [default_time_period])

        if json_request["sparse"]:
            for result in results:
                result["time_period"] = {}
                for period in values:
                    result["time_period"][self.groupings[period]] = str(result[period])
                    del result[period]
        else:
            results = generate_date_ranged_results_from_queryset(
                filter_time_periods=time_periods,
                queryset=results,
                date_range_type=values[-1])

        return Response({"group": self.groupings[self.group], "results": results})
