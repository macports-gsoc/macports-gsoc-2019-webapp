from django.core.management.base import BaseCommand, CommandError

from parsing_scripts import git_update
from port_detail.models import Port, LastPortIndexUpdate


class Command(BaseCommand):
    help = "Populates the database with Initial data from portindex.json file"

    def add_arguments(self, parser):
        parser.add_argument('new_commit',
                            nargs='?',
                            default=None,
                            help="Define a commit till which the update should be processed")
        parser.add_argument('old_commit',
                            nargs='?',
                            default=None,
                            help="Not recommended. Helps you provide a commit from which update should start")

    def handle(self, *args, **options):
        # Fetch the latest version of PortIndex.json and open the file
        data = Port.PortIndexUpdateHandler().sync_and_open_file()

        # If no argument is provided, use the commit-hash from JSON file:
        if options['new_commit'] is None:
            new_commit = data['info']['commit']
        # If argument is provided
        else:
            new_commit = options['new_commit']

        # If no argument is provided, options['old_commit'] will default to None
        # The code will then use the commit from last update which is stored in the database
        updated_portdirs = git_update.get_list_of_changed_ports(new_commit, options['old_commit'])

        # Generate a dictionary containing all the portdirs and initialise their values
        # with empty sets. The set would contain the ports under that portdir.
        dict_of_portdirs_with_ports = {}
        for portdir in updated_portdirs:
            dict_of_portdirs_with_ports[portdir] = set()

        # Using the received set of updated portdirs, find corresponding JSON objects for all ports under
        # that portdir.
        ports_to_be_updated_json = []
        for port in data['ports']:
            portdir = port['portdir'].lower()
            portname = port['name'].lower()
            if portdir in updated_portdirs:
                ports_to_be_updated_json.append(port)
                dict_of_portdirs_with_ports[portdir].add(portname)

        # Mark deleted ports
        Port.mark_deleted(dict_of_portdirs_with_ports)

        # Run updates
        Port.update(ports_to_be_updated_json)

        # Write the commit hash into database
        LastPortIndexUpdate.update_or_create_first_object(data['info']['commit'])
