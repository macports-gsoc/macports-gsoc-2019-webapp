from django.test import TransactionTestCase, Client
from django.urls import reverse

from ports.models import Dependency, Port
from config import TEST_PORTINDEX_JSON


class TestDependencies(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.client = Client()
        Port.load(TEST_PORTINDEX_JSON)

    def test_rows_created(self):
        self.assertEquals(Dependency.objects.all().count(), 6)

    def test_dependencies_fetched(self):
        response = self.client.get(reverse('port_detail_summary'), data={'port_name': 'port-A1'})
        dependencies = response.context['dependencies']
        self.assertEquals(dependencies.get(type='lib').dependencies.all().count(), 2)
        total_dependencies = []
        for d_type in dependencies:
            for dependency in d_type.dependencies.all():
                total_dependencies.append(dependency)
        self.assertEquals(len(total_dependencies), 3)

    def test_updates(self):
        updated_port = [{
            "name": "port-A5",
            "version": "1.0.0",
            "portdir": "categoryA/port-A5",
            "depends_extract": ["bin:port-C1:port-C1"],
            "depends_run": ["port:port-A1"],
        }]
        Port.update(updated_port)
        dependencies = Dependency.objects.filter(port_name__name__iexact='port-A5')
        self.assertEquals(dependencies.get(type='run').dependencies.all().count(), 1)
        self.assertEquals(dependencies.get(type='run').dependencies.all().first().name, 'port-A1')
        self.assertEquals(dependencies.count(), 2)
