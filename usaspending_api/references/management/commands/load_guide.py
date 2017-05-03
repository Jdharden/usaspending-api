import logging
import os.path

from django.conf import settings
from django.core.management.base import BaseCommand
from openpyxl import load_workbook

from usaspending_api.references.models import Definition, DefinitionResource


class Command(BaseCommand):
    help = "Loads an Excel spreadsheet of USAspending terminology definitions into the Guide model"

    logger = logging.getLogger('console')

    def add_arguments(self, parser):
        path = 'usaspending_api/data/USAspendingGuide.xlsx'
        path = os.path.normpath(path)
        default = os.path.join(settings.BASE_DIR, path)
        parser.add_argument(
            '-p',
            '--path',
            help='the path to the Excel spreadsheet to load',
            default=default)
        parser.add_argument(
            '-a',
            '--append',
            help='Append to existing guide',
            action='store_true',
            default=False)

    def handle(self, *args, **options):

        wb = load_workbook(filename=options['path'])
        ws = wb.active
        rows = ws.rows

        headers = [c.value for c in next(rows)[:5]]
        expected_headers = [
            'Term', 'Plain Language', 'DATA Act Schema Term',
            'DATA Act Schema Definition', 'More Resources'
        ]
        if headers != expected_headers:
            raise Exception('Expected headers of {} in {}'.format(
                expected_headers, options['path']))
       
        if options['append']:
            logging.info('Appending definitions to existing guide')
        else:
            logging.info('Deleting existing definitions from guide')
            DefinitionResource.objects.all().delete()
            Definition.objects.all().delete()

        field_names = ('term', 'plain', 'data_act_term', 'official')
        row_count = 0
        for row in rows:
            if not row[0].value:
                break
            definition = Definition()
            for (i, field_name) in enumerate(field_names):
                setattr(definition, field_name, row[i].value)
            definition.save()
            row_count += 1
            rsrc_cell = row[4]
            if rsrc_cell.value:
                resource = DefinitionResource(
                    definition=definition, title=rsrc_cell.value)
                if rsrc_cell.hyperlink:
                    resource.url = rsrc_cell.hyperlink.target
                resource.save()
        self.logger.info('{} definitions loaded from {}'.format(
            row_count, options['path']))
