import django_filters

from build.models import BuildHistory


class BuildHistoryFilter(django_filters.FilterSet):
    port_name = django_filters.CharFilter(lookup_expr='icontains')
    status = django_filters.CharFilter(lookup_expr='contains')

    class Meta:
        model = BuildHistory
        fields = ['builder_name__display_name']
