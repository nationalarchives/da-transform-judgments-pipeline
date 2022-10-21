#!/usr/bin/env python3
import tre_bagit_tranform_config


def simple_dri_metadata_from_config(bagit_metadata_row):
    dri_metadata = {}
    for k, v in bagit_metadata_row.items():
        field_spec = tre_bagit_tranform_config.metadata_spec[k]
        match field_spec['transform-type']:
            case 'pass':
                pass
            case 'map-to':
                target_mapping = [mapping for mapping in field_spec['mappings'] if mapping['from'] == v]
                if len(target_mapping) == 1:
                    dri_value = target_mapping[0]['to']
                else:
                    return ValueError("failed to find single mapping for: " + v)
                dri_metadata[field_spec['dri-field']] = dri_value
            case 'copy-to':
                dri_metadata[field_spec['dri-field']] = v
            case other_value:
                return ValueError("didn't expect spec to include: " + other_value)
    return dri_metadata
