#!/usr/bin/env python3

def simple_dri_metadata(bagit_metadata_row):
    dri_metadata = {}
    for k, v in bagit_metadata_row.items():
        if k == 'Filepath':
            pass  # used in a function to build dri 'identifier'
        elif k == 'FileName':
            dri_metadata['file_name'] = v
        elif k == 'FileType':
            if v == 'File':
                dri_metadata['folder'] = 'file'
            elif v == 'Folder':
                dri_metadata['folder'] = 'folder'
            else:
                handle_error(k, v)
        elif k == 'Filesize':
            pass  # not taken by dri
        elif k == 'RightsCopyright':
            if v == 'Crown Copyright':
                dri_metadata['rights_copyright'] = 'Crown Copyright'
            else:
                handle_error(k, v)
        elif k == 'LegalStatus':
            if v in ('Public Record', 'Public Record(s)'):
                dri_metadata['legal_status'] = 'Public Record(s)'
            else:
                handle_error(k, v)
        elif k == 'HeldBy':
            if v in ('TNA', 'The National Archives, Kew'):
                dri_metadata['held_by'] = 'The National Archives, Kew'
            else:
                handle_error(k, v)
        elif k == 'Language':
            if v == 'English':
                dri_metadata['language'] = 'English'
            else:
                handle_error(k, v)
        elif k == 'FoiExemptionCode':
            pass  # not used in dri metadata file (related to closure)
        elif k == 'LastModified':
            pass  # used in a function to build dri 'last_modified'
        elif k == 'OriginalFilePath':
            pass  # not implemented yet
        else:
            handle_error(k, v)
    return dri_metadata


def simple_dri_closure(bagit_metadata_row):
    dri_closure = {}
    for k, v in bagit_metadata_row.items():
        if k == 'FileType':
            if v == 'File':
                dri_closure['folder'] = 'file'
            elif v == 'Folder':
                dri_closure['folder'] = 'folder'
            else:
                handle_error(k, v)
        elif k == 'FoiExemptionCode':
            if v in ('', 'open'):
                dri_closure['foi_exemption_code'] = 'open'
            else:
                handle_error(k, v)
        elif k in ('RightsCopyright', 'LegalStatus', 'HeldBy', 'Language', 'LastModified', 'FileName'):
            pass  # not used in closure
        elif k == 'Filepath':
            pass  # used in a function to build dri 'identifier'
        elif k == 'Filesize':
            pass  # not taken by dri
        elif k == 'OriginalFilePath':
            pass  # not implemented yet
        else:
            handle_error(k, v)
    return dri_closure


def handle_error(k,v):
    return ValueError("value " + v + "not expected for key " + k)
