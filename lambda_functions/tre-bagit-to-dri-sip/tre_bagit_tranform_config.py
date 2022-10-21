metadata_spec = {
    'Filepath': {
       'tdr-field': 'Filepath',
       'transform-type': 'pass'  # used in a function
    },
    'FileName': {
        'tdr-field': 'FileName',
        'transform-type': 'copy-to',
        'dri-field': 'file_name'
    },
    'FileType': {
        'tdr-field': 'FileType',
        'transform-type': 'map-to',
        'dri-field': 'folder',
        'mappings': [
            {'from': 'File', 'to': 'file'},
            {'from': 'Folder', 'to': 'folder'}
        ]
    },
    'Filesize': {
        'tdr-field': 'Filesize',
        'transform-type': 'pass'  # not used in dri
    },
    'RightsCopyright': {
        'tdr-field': 'RightsCopyright',
        'transform-type': 'map-to',
        'dri-field': 'rights_copyright',
        'mappings': [
            {'from': 'Crown Copyright', 'to': 'Crown Copyright'}
        ]
    },
    'LegalStatus': {
        'tdr-field': 'LegalStatus',
        'transform-type': 'map-to',
        'dri-field': 'legal_status',
        'mappings': [
            {'from': 'Public Record', 'to': 'Public Record(s)'},
            {'from': 'Public Record(s)', 'to': 'Public Record(s)'}
        ]
    },
    'HeldBy': {
        'tdr-field': 'HeldBy',
        'transform-type': 'map-to',
        'dri-field': 'held_by',
        'mappings': [
            {'from': 'TNA', 'to': 'The National Archives, Kew'},
            {'from': '"The National Archives, Kew"', 'to': 'The National Archives, Kew'}
        ]
    },
    'Language': {
        'tdr-field': 'Language',
        'transform-type': 'map-to',
        'dri-field': 'language',
        'mappings': [
            {'from': 'English', 'to': 'English'}
        ]
    },
    'FoiExemptionCode': {
        'tdr-field': 'FoiExemptionCode',
        'transform-type': 'pass'  # not used in metadata (is for closure)
    },
    'LastModified': {
        'tdr-field': 'LastModified',
        'transform-type': 'pass'  # used in a function
    },
    'OriginalFilePath': {
        'tdr-field': 'OriginalFilePath',
        'transform-type': 'pass'  # not implemented yet
    }
}
