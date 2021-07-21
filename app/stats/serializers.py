import datetime

from rest_framework import serializers
from django.db.models import Count, Subquery, Value, CharField
from django.db.models.functions import TruncMonth, Cast, ExtractMonth, ExtractYear, Concat

from stats.models import PortInstallation
from stats.models import Submission
from stats.utilities.sort_by_version import sort_list_of_dicts_by_version
from stats.validators import ALLOWED_DAYS_FOR_STATS as ALLOWED_DAYS
from stats.validators import ALLOWED_PROPERTIES, ALLOWED_GENERAL_PROPERTIES


class PortStatisticsSerializer(serializers.Serializer):
    result = serializers.SerializerMethodField()

    sort_by = None
    days = None
    days_ago = None
    properties = []
    port_name = None

    class Meta:
        fields = ('property', 'result')

    def validate_context(self):
        days = self.context.get('days', '30')
        days_ago = self.context.get('days_ago', '0')
        if (not days.isnumeric()) or (not days_ago.isnumeric()):
            return False

        days = int(days)
        days_ago = int(days_ago)

        if (days not in ALLOWED_DAYS) or (days_ago not in ALLOWED_DAYS):
            return False

        self.days = int(days)
        self.days_ago = int(days_ago)
        return self.validate_properties()

    def validate_properties(self):
        properties = self.context.get('property')
        for p in properties:
            if p not in ALLOWED_PROPERTIES:
                return False
        self.properties = properties
        return self.validate_port()

    def validate_sorting(self):
        sort_by = self.context.get('sort_by')
        if sort_by == "" or sort_by is None:
            return
        if sort_by == "variants" or sort_by == "requested":
            return
        if sort_by not in ALLOWED_PROPERTIES or sort_by not in self.properties:
            return
        self.sort_by = sort_by
        return

    def validate_port(self):
        port_name = self.context.get('name')
        if port_name is None or port_name == "":
            return False
        self.port_name = port_name
        return True

    def generate_time_range_query(self):
        is_valid = self.validate_context()
        if not is_valid:
            return PortInstallation.objects.none()

        end_date = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=self.days_ago)
        start_date = end_date - datetime.timedelta(days=self.days)
        submissions = Submission.objects.defer('raw_json').filter(timestamp__range=[start_date, end_date]).order_by('user', '-timestamp').distinct('user')
        port_installations = PortInstallation.objects\
            .filter(
                submission_id__in=Subquery(submissions.values('id')),
                port__iexact=self.port_name
            )\
            .select_related('submission')\
            .only(
                'submission__user_id',
            )
        return port_installations

    def get_result(self, obj):
        result = self.generate_time_range_query().values(*self.properties).annotate(count=Count('submission__user_id'))
        self.validate_sorting()
        if self.sort_by:
            result = sort_list_of_dicts_by_version(list(result), self.sort_by)
        return result


class PortMonthlyInstallationsSerializer(serializers.Serializer):
    result = serializers.SerializerMethodField()

    port_name = None
    values = None


    class Meta:
        fields = ('result', )

    def validate_context(self):
        port_name = self.context.get('name')
        if port_name == "" or port_name is None:
            return False
        self.port_name = port_name

        include_versions = self.context.get('include_versions')
        if include_versions == "yes":
            self.values = ['month', 'version']
        else:
            self.values = ['month']

        return True

    def get_result(self, obj):
        is_valid = self.validate_context()
        if not is_valid:
            return PortInstallation.objects.none()
        today_day = datetime.datetime.now().day
        last_12_months = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(365)
        last_12_months.replace(day=1)

        result = PortInstallation.objects \
            .only('id') \
            .filter(port__iexact=self.port_name, submission__timestamp__gte=last_12_months) \
            .annotate(datetime=TruncMonth('submission__timestamp')) \
            .order_by('datetime') \
            .annotate(
                m=Cast(ExtractMonth('datetime'), CharField()),
                y=Cast(ExtractYear('datetime'), CharField()),
                month=Concat('y', Value(','), 'm')
            ) \
            .values(*self.values) \
            .annotate(count=Count('submission__user_id', distinct=True))

        return result


class GeneralStatisticsSerializer(PortStatisticsSerializer):
    result = serializers.SerializerMethodField()

    class Meta:
        fields = ('result', )

    def generate_time_range_query(self):
        is_valid = self.validate_context()
        if not is_valid:
            return Submission.objects.none()

        end_date = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=self.days_ago)
        start_date = end_date - datetime.timedelta(days=self.days)
        submissions = Submission.objects.only('id').filter(timestamp__range=[start_date, end_date]).order_by('user', '-timestamp').distinct('user')
        return Submission.objects.filter(id__in=Subquery(submissions.values('id')))

    def validate_properties(self):
        properties = self.context.get('property')
        for p in properties:
            if p not in ALLOWED_GENERAL_PROPERTIES:
                return False
        self.properties = properties
        return True

    def validate_sorting(self):
        sort_by = self.context.get('sort_by')
        if sort_by == "" or sort_by is None:
            return
        if sort_by not in ALLOWED_GENERAL_PROPERTIES or sort_by not in self.properties:
            return
        self.sort_by = sort_by
        return

    def get_result(self, obj):
        result = self.generate_time_range_query().values(*self.properties).annotate(count=Count('user'))
        self.validate_sorting()
        if self.sort_by:
            result = sort_list_of_dicts_by_version(list(result), self.sort_by)
        return result
