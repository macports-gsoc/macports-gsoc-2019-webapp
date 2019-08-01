import os
import json
import datetime
import itertools
from distutils.version import LooseVersion

import requests
from bs4 import BeautifulSoup
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Subquery, Count, Case, IntegerField, When
from django.db.models.functions import TruncMonth, Lower

from .models import Port, Category, BuildHistory, Maintainer, Dependency, Builder, Variant, Submission, PortInstallation
from .filters import BuildHistoryFilter, PortFilterByMultiple
from .validators import validate_stats_days, validate_columns_port_installations, validate_unique_columns_port_installations, ALLOWED_DAYS_FOR_STATS
from .utilities.sort_by_version import sort_list_of_dicts_by_version


def index(request):
    categories = Category.objects.all().order_by('name')

    submissions_unique = Submission.objects.filter(timestamp__gte=datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=30)).order_by('user', '-timestamp').distinct('user')
    top_ports = PortInstallation.objects.filter(submission_id__in=Subquery(submissions_unique.values('id')), requested=True).exclude(port__exact='mpstats-gsoc').values('port').annotate(num=Count('port')).order_by('-num')[:10]

    return render(request, 'ports/index.html', {
        'categories': categories,
        'top_ports': top_ports
    })


def categorylist(request, cat):
    try:
        category = Category.objects.get(name__iexact=cat)
        all_ports = Port.objects.filter(categories__name=cat).order_by(Lower('name'))
        portscount = all_ports.count()
        paginated_ports = Paginator(all_ports, 100)
        page = request.GET.get('page', 1)
        try:
            ports = paginated_ports.get_page(page)
        except PageNotAnInteger:
            ports = paginated_ports.get_page(1)
        except EmptyPage:
            ports = paginated_ports.get_page(paginated_ports.num_pages)
        return render(request, 'ports/categorylist.html',
                      {
                          'ports': ports,
                          'portscount': portscount,
                          'category': cat
                      })
    except Category.DoesNotExist:
        return render(request, 'ports/exceptions/category_not_found.html')


def variantlist(request, variant):
    all_objects = Variant.objects.filter(variant=variant).select_related('port')
    all_objects_count = all_objects.count()
    paginated_objects = Paginator(all_objects, 100)
    page = request.GET.get('page', 1)
    try:
        objects = paginated_objects.get_page(page)
    except PageNotAnInteger:
        objects = paginated_objects.get_page(1)
    except EmptyPage:
        objects = paginated_objects.get_page(paginated_objects.num_pages)
    return render(request, 'ports/variantlist.html', {
        'objects': objects,
        'variant': variant,
        'all_objects_count': all_objects_count
    })


# Views for port-detail page START
def portdetail(request, name):
    try:
        req_port = Port.objects.get(name__iexact=name)
        days = request.GET.get('days', 30)
        days_ago = request.GET.get('days_ago', 0)
        tab = request.GET.get('tab', "summary")
        allowed_tabs = ["summary", "builds", "stats", "tickets"]
        if tab not in allowed_tabs:
            return HttpResponse("Invalid tab requested. Expected values: {}".format(allowed_tabs))

        all_latest_builds = BuildHistory.objects.all().order_by('port_name', 'builder_name', '-build_id').distinct('port_name', 'builder_name')
        port_latest_builds = list(BuildHistory.objects.filter(id__in=Subquery(all_latest_builds.values('id')), port_name__iexact=name).values('builder_name__name', 'build_id', 'status'))

        builders = list(Builder.objects.all().values_list('name', flat=True))

        builders.sort(key=LooseVersion, reverse=True)
        latest_builds = {}
        for builder in builders:
            latest_builds[builder] = next((item for item in port_latest_builds if item['builder_name__name'] == builder), False)
        return render(request, 'ports/portdetail.html', {
            'req_port': req_port,
            'latest_builds': latest_builds,
            'tab': tab,
            'days': days,
            'days_ago': days_ago,
        })
    except Port.DoesNotExist:
        return render(request, 'ports/exceptions/port_not_found.html', {
            'name': name
        })


def portdetail_summary(request):
    try:
        port_name = request.GET.get('port_name')
        port = Port.objects.get(name=port_name)
        port_id = port.id
        maintainers = Maintainer.objects.filter(ports__name=port_name)
        dependencies = Dependency.objects.filter(port_name_id=port_id)
        dependents = Dependency.objects.filter(dependencies__name__iexact=port_name).select_related('port_name').order_by(Lower('port_name__name'))
        variants = Variant.objects.filter(port_id=port_id).order_by(Lower('variant'))

        submissions_last_30_days = Submission.objects.filter(timestamp__gte=datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=30)).order_by('user', '-timestamp').distinct('user')
        requested_count = PortInstallation.objects.filter(submission_id__in=Subquery(submissions_last_30_days.values('id')), requested=True, port__iexact=port_name).values('port').aggregate(Count('port'))
        total_count = PortInstallation.objects.filter(submission_id__in=Subquery(submissions_last_30_days.values('id')), port__iexact=port_name).values('port').aggregate(Count('port'))

        return render(request, 'ports/port-detail/summary.html', {
            'port': port,
            'maintainers': maintainers,
            'dependencies': dependencies,
            'dependents': dependents,
            'variants': variants,
            'requested_count': requested_count,
            'total_count': total_count
        })
    except Port.DoesNotExist:
        return HttpResponse("Visit /port/port-name/ if you are looking for ports.")


def portdetail_build_information(request):
    status = request.GET.get('status', '')
    builder = request.GET.get('builder_name__name', '')
    port_name = request.GET.get('port_name', '')
    page = request.GET.get('page', 1)
    builders = list(Builder.objects.all().values_list('name', flat=True))
    builders.sort(key=LooseVersion, reverse=True)
    builds = BuildHistoryFilter({
        'builder_name__name': builder,
        'status': status,
    }, queryset=BuildHistory.objects.filter(port_name__iexact=port_name).select_related('builder_name').order_by('-time_start')).qs
    paginated_builds = Paginator(builds, 100)
    try:
        result = paginated_builds.get_page(page)
    except PageNotAnInteger:
        result = paginated_builds.get_page(1)
    except EmptyPage:
        result = paginated_builds.get_page(paginated_builds.num_pages)

    return render(request, 'ports/port-detail/build_information.html', {
        'builds': result,
        'builder': builder,
        'builders_list': builders,
        'status': status,
    })


def portdetail_stats(request):
    days = request.GET.get('days', 30)
    days_ago = request.GET.get('days_ago', 0)

    # Validate days and days_ago
    for value in days, days_ago:
        check, message = validate_stats_days(value)
        if check is False:
            return HttpResponse(message)

    port_name = request.GET.get('port_name')
    port = Port.objects.get(name__iexact=port_name)

    end_date = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=int(days_ago))
    start_date = end_date - datetime.timedelta(days=int(days))

    # Section for calculation of current stats
    submissions = Submission.objects.filter(timestamp__range=[start_date, end_date]).order_by('user', '-timestamp').distinct('user')
    port_installations = PortInstallation.objects.filter(submission_id__in=Subquery(submissions.values('id')), port__iexact=port_name)
    requested_port_installations_count = port_installations.filter(requested=True).aggregate(Count('submission__user_id', distinct=True))
    total_port_installations_count = port_installations.aggregate(Count('submission__user_id', distinct=True))
    port_installations_by_port_version = port_installations.values('version').annotate(num=Count('version')).order_by('-num')
    port_installations_by_os_and_xcode_version = sort_list_of_dicts_by_version(list(port_installations.values('submission__xcode_version', 'submission__os_version').annotate(num=Count('submission__user_id', distinct=True))), 'submission__os_version')
    port_installations_by_os_stdlib_build_arch = sort_list_of_dicts_by_version(list(port_installations.values('submission__os_version', 'submission__build_arch', 'submission__cxx_stdlib').annotate(num=Count('submission__user_id', distinct=True))), 'submission__os_version')

    port_installations_by_month = PortInstallation.objects.filter(port__iexact=port_name).annotate(month=TruncMonth('submission__timestamp')).values('month').annotate(num=Count('submission__user', distinct=True))[:12]
    port_installations_by_version_and_month = PortInstallation.objects.filter(port__iexact=port_name).annotate(month=TruncMonth('submission__timestamp')).values('month', 'version').annotate(num=Count('submission__user', distinct=True))[:12]

    return render(request, 'ports/port-detail/installation_stats.html', {
        'requested_port_installations_count': requested_port_installations_count,
        'total_port_installations_count': total_port_installations_count,
        'port_installations_by_port_version': port_installations_by_port_version,
        'port_installations_by_os_and_xcode_version': port_installations_by_os_and_xcode_version,
        'port_installations_by_month': port_installations_by_month,
        'port_installations_by_version_and_month': port_installations_by_version_and_month,
        'port_installations_by_os_stdlib_build_arch': port_installations_by_os_stdlib_build_arch,
        'days': days,
        'days_ago': days_ago,
        'allowed_days': ALLOWED_DAYS_FOR_STATS
    })


def all_builds_view(request):
    builders = list(Builder.objects.all().values_list('name', flat=True))
    builders.sort(key=LooseVersion, reverse=True)
    jump_to_page = request.GET.get('page', 1)

    return render(request, 'ports/all_builds.html', {
        'builders': builders,
        'jump_to_page': jump_to_page
    })


def all_builds_filter(request):
    builder = request.GET.get('builder_name__name')
    status = request.GET.get('status')
    port_name = request.GET.get('port_name')
    page = request.GET.get('page')

    if status == 'unresolved':
        all_latest_builds = BuildHistory.objects.all().order_by('port_name', 'builder_name', '-build_id').distinct('port_name', 'builder_name')
        builds = BuildHistoryFilter({
            'builder_name__name': builder,
            'port_name': port_name,
        }, queryset=BuildHistory.objects.filter(id__in=Subquery(all_latest_builds.values('id')), status__icontains='failed').select_related('builder_name').order_by('-time_start')).qs
    else:
        builds = BuildHistoryFilter(request.GET, queryset=BuildHistory.objects.all().select_related('builder_name').order_by('-time_start')).qs

    paginated_builds = Paginator(builds, 100)
    try:
        result = paginated_builds.get_page(page)
    except PageNotAnInteger:
        result = paginated_builds.get_page(1)
    except EmptyPage:
        result = paginated_builds.get_page(paginated_builds.num_pages)

    return render(request, 'ports/ajax-filters/builds_filtered_table.html', {
        'builds': result,
        'builder': builder,
        'status': status,
        'port_name': port_name,
    })


def stats(request):
    days = request.GET.get('days', 30)

    # Validate days
    check, message = validate_stats_days(days)
    if check is False:
        return HttpResponse(message)
    current_week = datetime.datetime.today().isocalendar()[1]
    all_submissions = Submission.objects.all()
    total_unique_users = all_submissions.distinct('user').count()
    current_week_unique = all_submissions.filter(timestamp__week=current_week).distinct('user').count()
    last_week_unique = all_submissions.filter(timestamp__week=current_week - 1).distinct('user').count()

    # Number of unique users vs month
    users_by_month = Submission.objects.annotate(month=TruncMonth('timestamp')).values('month').annotate(num=Count('user_id', distinct=True))[:12]

    # System Stats for Current Users
    submissions_last_x_days = Submission.objects.filter(timestamp__gte=datetime.datetime.now(tz=datetime.timezone.utc)-datetime.timedelta(days=int(days))).order_by('user', '-timestamp').distinct('user')
    submissions_unique = Submission.objects.filter(id__in=Subquery(submissions_last_x_days.values('id')))
    macports_distribution = submissions_unique.values('macports_version').annotate(num=Count('macports_version'))
    os_distribution = sort_list_of_dicts_by_version(list(submissions_unique.values('os_version', 'os_arch').annotate(num=Count('user_id', distinct=True))), 'os_version')
    xcode_distribution = sort_list_of_dicts_by_version(list(submissions_unique.values('xcode_version', 'os_version').annotate(num=Count('user_id', distinct=True))), 'os_version')

    return render(request, 'ports/stats.html', {
        'total_submissions': all_submissions.count(),
        'unique_users': total_unique_users,
        'current_week': current_week_unique,
        'last_week': last_week_unique,
        'users_by_month': users_by_month,
        'os_distribution': os_distribution,
        'macports_distribution': macports_distribution,
        'xcode_distribution': xcode_distribution,
        'days': int(days),
        'allowed_days': ALLOWED_DAYS_FOR_STATS
    })


def stats_port_installations(request):
    days = request.GET.get('days', 30)
    first = str(request.GET.get('first', '-total_count'))
    second = str(request.GET.get('second', '-req_count'))
    third = str(request.GET.get('third', 'port'))
    columns = [first, second, third]

    # Validate days
    check, message = validate_stats_days(days)
    if check is False:
        return HttpResponse(message)

    # Validate columns
    check, message = validate_columns_port_installations(columns)
    if check is False:
        return HttpResponse(message)

    # Validate unique columns
    check, message = validate_unique_columns_port_installations(columns)
    if check is False:
        return HttpResponse(message)

    return render(request, 'ports/stats_port_installations.html', {
        'days': days,
        'first': first,
        'second': second,
        'third': third,
        'allowed_days': ALLOWED_DAYS_FOR_STATS
    })


def stats_port_installations_filter(request):
    days = request.GET.get('days', 30)
    order_by_1 = str(request.GET.get('order_by_1', '-total_count'))
    order_by_2 = str(request.GET.get('order_by_2', '-req_count'))
    order_by_3 = str(request.GET.get('order_by_3', 'port'))
    search_by = str(request.GET.get('search_by', ''))
    columns = [order_by_1, order_by_2, order_by_3]

    # Validate days
    check, message = validate_stats_days(days)
    if check is False:
        return HttpResponse(message)

    # Validate columns
    check, message = validate_columns_port_installations(columns)
    if check is False:
        return HttpResponse(message)

    # Validate unique columns
    check, message = validate_unique_columns_port_installations(columns)
    if check is False:
        return HttpResponse(message)

    submissions_unique = Submission.objects.filter(timestamp__gte=datetime.datetime.now(tz=datetime.timezone.utc)-datetime.timedelta(days=int(days))).order_by('user', '-timestamp').distinct('user')
    installations = PortInstallation.objects.order_by('port')\
        .filter(submission_id__in=Subquery(submissions_unique.values('id')))\
        .values('port').annotate(total_count=Count('port'))\
        .annotate(req_count=Count(Case(When(requested=True, then=1), output_field=IntegerField())))\
        .exclude(port__iexact='mpstats-gsoc')\
        .filter(port__icontains=search_by)\
        .extra(select={'port': 'lower(port)'})\
        .order_by(order_by_1, order_by_2, order_by_3)

    paginated_obj = Paginator(installations, 100)
    page = request.GET.get('page', 1)
    try:
        installs = paginated_obj.get_page(page)
    except PageNotAnInteger:
        installs = paginated_obj.get_page(1)
    except EmptyPage:
        installs = paginated_obj.get_page(paginated_obj.num_pages)

    return render(request, 'ports/ajax-filters/port_installations_table.html', {
        'installs': installs,
        'search_by': search_by
    })


def get_ports_of_maintainers(maintainers, request):
    i = 0
    for maintainer in maintainers:
        if i > 0:
            all_ports = maintainer.ports.all().order_by('id') | all_ports
        else:
            all_ports = maintainer.ports.all().order_by('id')
        i = i + 1

    all_ports_num = all_ports.count()
    paginated_ports = Paginator(all_ports, 100)
    page = request.GET.get('page', 1)
    try:
        ports = paginated_ports.get_page(page)
    except PageNotAnInteger:
        ports = paginated_ports.get_page(1)
    except EmptyPage:
        ports = paginated_ports.get_page(paginated_ports.num_pages)

    return ports, all_ports_num


def maintainer_detail_github(request, github_handle):
    maintainers = Maintainer.objects.filter(github=github_handle)
    ports, all_ports_num = get_ports_of_maintainers(maintainers, request)

    return render(request, 'ports/maintainerdetail.html', {
        'maintainers': maintainers,
        'maintainer': github_handle,
        'all_ports_num': all_ports_num,
        'ports': ports,
        'github': True,
    })


def maintainer_detail_email(request, name, domain):
    maintainers = Maintainer.objects.filter(name=name, domain=domain)
    ports, all_ports_num = get_ports_of_maintainers(maintainers, request)

    return render(request, 'ports/maintainerdetail.html', {
        'maintainers': maintainers,
        'maintainer': name,
        'ports': ports,
        'all_ports_num': all_ports_num,
        'github': False
    })


# Respond to ajax-call triggered by the search box
def search(request):
    query = request.GET.get('search_text', '')
    search_by = request.GET.get('search_by', '')
    ports = PortFilterByMultiple(request.GET, queryset=Port.objects.all()).qs[:50]

    return render(request, 'ports/ajax-filters/filtered_table.html', {
        'ports': ports,
        'query': query,
        'search_by': search_by
    })


# Respond to ajax call for loading tickets
def tickets(request):
    port_name = request.GET.get('port_name')
    URL = "https://trac.macports.org/query?status=!closed&port=~{}".format(port_name)
    response = requests.get(URL)
    Soup = BeautifulSoup(response.content, 'html5lib')
    all_tickets = []
    for row in Soup.findAll('tr', attrs={'class': 'prio2'}):
        srow = row.find('td', attrs={'class': 'summary'})
        idrow = row.find('td', attrs={'class': 'id'})
        typerow = row.find('td', attrs={'class': 'type'})
        ticket = {}
        ticket['url'] = srow.a['href']
        ticket['title'] = srow.a.text
        ticket['id'] = idrow.a.text
        ticket['type'] = typerow.text
        all_tickets.append(ticket)

    return render(request, 'ports/ajax-filters/tickets.html', {
        'portname': port_name,
        'tickets': all_tickets,
    })


# Respond to ajax calls for searching within a category
def search_ports_in_category(request):
    query = request.GET.get('name')
    search_in = request.GET.get('categories__name')

    filtered_ports = PortFilterByMultiple(request.GET, queryset=Port.objects.all()).qs[:50]
    return render(request, 'ports/ajax-filters/filtered_table.html', {
        'ports': filtered_ports,
        'query': query,
        'search_in': search_in,
        'content': "Category"
    })


# Respond to ajax calls for searching within a maintainer
def search_ports_in_maintainer(request):
    query = request.GET.get('name', '')
    name = request.GET.get('maintainers__name')
    github = request.GET.get('maintainers__github')
    if name is None:
        search_in = github
    else:
        search_in = name

    filtered_ports = PortFilterByMultiple(request.GET, queryset=Port.objects.all()).qs
    return render(request, 'ports/ajax-filters/filtered_table.html', {
        'ports': filtered_ports,
        'query': query,
        'search_in': search_in,
        'content': "Maintainer"
    })


def search_ports_in_variant(request):
    query = request.GET.get('name', '')
    search_in = request.GET.get('variant', '')

    filtered_ports = Variant.objects.filter(variant=search_in, port__name__icontains=query)
    return render(request, 'ports/ajax-filters/filtered_table.html', {
        'ports': filtered_ports,
        'query': query,
        'search_in': search_in,
        'content': "Variant"
    })


@csrf_exempt
def stats_submit(request):
    if request.method == "POST":
        try:
            received_body = request.body.decode()
            prefix = 'submission[data]='
            if not received_body.startswith(prefix):
                return HttpResponse("Invalid body of the request.")

            received_json = json.loads(received_body[len(prefix):], encoding='utf-8')
            submission_id = Submission.populate(received_json, datetime.datetime.now(tz=datetime.timezone.utc))
            PortInstallation.populate(received_json['active_ports'], submission_id)

            return HttpResponse("Success")

        except:
            return HttpResponse("Something went wrong")
    else:
        return HttpResponse("Method Not Allowed")


@csrf_exempt
def update_api(request):
    if request.method == 'POST':
        key = request.POST.get('key')
        print(key)
        if key == os.environ['UPDATE_API_KEY']:
            try:
                received_json = json.loads(request.POST.get('ports'))
                Port.update(received_json)
                return HttpResponse("Updating successful")
            except:
                return HttpResponse("Failed to parse the JSON")

        else:
            return HttpResponse("Authentication failed. Invalid Key")
    else:
        return HttpResponse('Method not allowed')
