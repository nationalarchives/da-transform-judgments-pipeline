#!/usr/bin/env python3

def simple_dri_metadata(bagit_metadata_row):
    dri_metadata = {}
    for k, v in bagit_metadata_row.items():
        match k:
            case 'Filepath':
                pass  # used in a function to build dri 'identifier'
            case 'FileName':
                dri_metadata['file_name'] = v
            case 'FileType':
                match v:
                    case 'File': dri_metadata['folder'] = 'file'
                    case 'Folder': dri_metadata['folder'] = 'folder'
                    case _: handle_error(k, v)

            case 'Filesize':
                pass  # not taken by dri
            case 'RightsCopyright':
                match v:
                    case 'Crown Copyright': dri_metadata['rights_copyright'] = 'Crown Copyright'
                    case _: handle_error(k, v)
            case 'LegalStatus':
                match v:  # the case match can be an OR as the output is the same
                    case 'Public Record' | 'Public Record(s)': dri_metadata['legal_status'] = 'Public Record(s)'
                    case _: handle_error(k, v)
            case 'HeldBy':
                match v:
                    case 'TNA' | 'The National Archives, Kew': dri_metadata['held_by'] = 'The National Archives, Kew'
                    case _: handle_error(k, v)
            case 'Language':
                match v:
                    case 'English': dri_metadata['language'] = 'English'
                    case _: handle_error(k, v)
            case 'FoiExemptionCode':
                pass  # not used in dri metadata file (related to closure)
            case 'LastModified':
                pass  # used in a function to build dri 'last_modified'
            case 'OriginalFilePath':
                pass  # not implemented yet
            case _: handle_error(k, v)
    return dri_metadata


def simple_dri_closure(bagit_metadata_row):
    dri_closure = {}
    for k, v in bagit_metadata_row.items():
        match k:
            case 'FileType':
                match v:
                    case 'File': dri_closure['folder'] = 'file'
                    case 'Folder': dri_closure['folder'] = 'folder'
                    case _: handle_error(k, v)
            case 'FoiExemptionCode':
                match v:
                    case '' | 'open': dri_closure['foi_exemption_code'] = 'open'
                    case _: handle_error(k, v)
            case 'RightsCopyright' | 'LegalStatus' | 'HeldBy' | 'Language' | 'LastModified' | 'FileName':
                pass  # not used in closure
            case 'Filepath':
                pass  # used in a function to build dri 'identifier'
            case 'Filesize':
                pass  # not taken by dri
            case 'OriginalFilePath':
                pass  # not implemented yet
            case _: handle_error(k, v)
    return dri_closure


def handle_error(k,v):
    return ValueError("value " + v + "not expected for key " + k)
