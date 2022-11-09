import json

from behave import *
from tre_bagit import BagitData
from tre_bagit_transforms import dri_config_dict
import csv
import shutil
import os


temp_dir = '/tmp/tre-test/features'
file_metadata_path = f'{temp_dir}/file-metadata.csv'
bag_info_path = f'{temp_dir}/bag-info.json'
manifest_path = f'{temp_dir}/manifest.json'


def make_clean_temp_dir(temp_dir):
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
        except OSError as e:
            return IOError("Error: %s : %s" % (temp_dir, e.strerror))
    os.makedirs(temp_dir, exist_ok=True)


@given(u'a bagit with files that include')
def step_impl(context):
    info_dict = {}
    manifest_dict = []
    csv_dict = {}
    manifest_row = {}
    for file, k, v in context.table:
        print(str(file))
        if file == 'bag-info.txt':
            info_dict[k] = v
        elif file == 'file-metadata.csv':
            csv_dict[k] = v
        elif file == 'manifest-sha256.txt':
            manifest_row[k] = v
        else:
            return ValueError("file " + file + " not implemented")
    manifest_dict.append(manifest_row)

    make_clean_temp_dir(temp_dir)

    # make file-metadata csv file in temp_dir
    with open(file_metadata_path, 'x') as file_metadata:
        file_metadata_fieldnames = list(csv_dict.keys())
        file_metadata_writer = csv.DictWriter(file_metadata, fieldnames=file_metadata_fieldnames, lineterminator="\n")
        file_metadata_writer.writeheader()
        file_metadata_writer.writerow(csv_dict)
    # make bag-info json file in temp_dir
    with open(bag_info_path, 'x') as bif:
        bif.write(json.dumps(info_dict))
    # make manifest json file in tmp file
    with open(manifest_path, 'x') as mf:
        mf.write(json.dumps(manifest_dict))


@when(u'transform that bagit to make {output}')
def step_impl(context, output):
    config_dict = {}
    # make the bagit from the files in temp_dir
    with open(bag_info_path) as bif:
        info_dict = json.load(bif)
    with open(manifest_path) as mf:
        manifest_row = json.load(mf)
    with open(file_metadata_path) as file_metadata:
        file_metadata = csv.DictReader(file_metadata)
        bagit = BagitData(config_dict, info_dict, manifest_row, file_metadata)
    # run the required transformation and write the csv file to temp_dir
    dc = dri_config_dict(bagit.consignment_reference, bagit.consignment_series, folder_check=False)
    if output == dc['CLOSURE']:
        closure = bagit.to_closure(dc)
        closure_filename = dc['CLOSURE']
        closure_csv_path = f'{temp_dir}/{closure_filename}'
        with open(closure_csv_path, 'x') as closure_csv:
            closure_csv.write(closure)
    elif output == dc['METADATA']:
        metadata = bagit.to_metadata(dc)
        metadata_filename = dc['METADATA']
        metadata_csv_path = f'{temp_dir}/{metadata_filename}'
        with open(metadata_csv_path, 'x') as metadata_csv:
            metadata_csv.write(metadata)


@then(u'the file {file_name} has')
def step_impl(context, file_name):
    # read the required csv file from temp_dir and check values
    with open(f'{temp_dir}/{file_name}') as csv_file:
        file_metadata = csv.DictReader(csv_file)
        row = next(file_metadata)
        for k, v in context.table:
            print("assert that key: " + k + " has expected value: " + v + " actual value is: " + row[k])
            assert(row[k] == v)
