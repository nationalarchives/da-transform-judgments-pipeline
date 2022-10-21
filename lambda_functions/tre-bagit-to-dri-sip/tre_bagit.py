#!/usr/bin/env python3

import logging
import csv
import io
import urllib.parse
import tre_bagit_transforms

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class BagitData:

    def __init__(self, config_dict, info_dict, manifest_dict, csv_data):
        self.bagit = config_dict
        self.info_dict = info_dict
        self.manifest_dict = manifest_dict
        self.csv_data = list(csv_data)
        self.consignment_series = self.info_dict.get('Consignment-Series')
        self.tdr_bagit_export_time = self.info_dict.get('Consignment-Export-Datetime')
        self.consignment_reference = self.info_dict.get('Internal-Sender-Identifier')

    def to_metadata(self, dc):
        metadata_fieldnames = ['identifier', 'file_name', 'folder', 'date_last_modified', 'checksum',
                               'rights_copyright', 'legal_status', 'held_by', 'language', 'TDR_consignment_ref']
        metadata_output = io.StringIO()
        metadata_writer = csv.DictWriter(metadata_output, fieldnames=metadata_fieldnames, lineterminator="\n")
        metadata_writer.writeheader()
        for row in self.csv_data:
            dri_metadata = tre_bagit_transforms.simple_dri_metadata(row)
            result = self.dri_identifier(row, dc)
            dri_metadata['identifier'] = result
            dri_metadata['date_last_modified'] = self.dri_last_modified(row)
            dri_metadata['checksum'] = self.dri_checksum(row)
            dri_metadata['TDR_consignment_ref'] = self.consignment_reference
            metadata_writer.writerow(dri_metadata)
        return metadata_output.getvalue()

    def to_closure(self, dc):
        closure_fieldnames = ['identifier', 'folder', 'closure_start_date', 'closure_period', 'foi_exemption_code',
                              'foi_exemption_asserted', 'title_public', 'title_alternate', 'closure_type']
        closure_output = io.StringIO()
        closure_writer = csv.DictWriter(closure_output, fieldnames=closure_fieldnames, lineterminator="\n")
        closure_writer.writeheader()
        for row in self.csv_data:
            dri_closure = tre_bagit_transforms.simple_dri_closure(row)
            dri_closure['identifier'] = self.dri_identifier(row, dc)
            dri_closure['closure_start_date'] = ''
            dri_closure['closure_period'] = 0
            dri_closure['foi_exemption_asserted'] = ''
            dri_closure['title_public'] = 'TRUE'
            dri_closure['title_alternate'] = ''
            dri_closure['closure_type'] = 'open_on_transfer'
            closure_writer.writerow(dri_closure)
        return closure_output.getvalue()

    # ==== specific transformations for individual field values ====
    @staticmethod
    def dri_folder(row):
        # remove capitalisation coming from tdr
        return row.get('FileType').lower()

    @staticmethod
    def dri_identifier(row, dc):
        # set dri batch/series/ prefix, escape the uri + append a `/` if folder
        dri_identifier = row.get('Filepath').replace('data/', dc["IDENTIFIER_PREFIX"], 1)
        final_slash_if_folder = "/" if(BagitData.dri_folder(row) == 'folder') else ""
        return urllib.parse.quote(dri_identifier).replace('%3A', ':') + final_slash_if_folder

    def dri_checksum(self, row):
        # comes from the manifest and only exists for files
        bagit_manifest_for_row = list(filter(lambda d: d.get('file') == row.get('Filepath'), self.manifest_dict))
        return bagit_manifest_for_row[0].get('checksum') if(len(bagit_manifest_for_row) == 1) else ''

    def dri_last_modified(self, row):
        if self.dri_folder(row) == 'file':
            return row.get('LastModified')
        else:
            # use bagit export time for folders as they have no dlm from tdr
            return self.tdr_bagit_export_time.replace('Z', '', 1)
