#!/usr/bin/env python3

from tre_bagit import BagitData
import csv
import io
import unittest


config_dict = {
    "CONSIGNMENT_REFERENCE": "TDR-2022-AA1"
}
info_dict = {
    "Consignment-Series": "MOCKA 101",
    "Internal-Sender-Identifier": "TDR-2022-AA1",
    "Consignment-Export-Datetime": "2022-07-18T12:45:45Z",
}
manifest_dict = [
    {
        "file": "data/content/file-c1.txt",
        "basename": "file-c1.txt",
        "checksum": "5bd8879fba139fed98c048261cb2a91d727ceafb27414cc54e21c26915e9e40f"
    }
]
driConfig = dict(
    IDENTIFIER_PREFIX='file:/' + "MOCKA101Y22TBAA1" + '/' + "MOCKA_101" + '/'
)


def make_bagit(csv_string):
    csv_data = csv.DictReader(io.StringIO(csv_string))
    return BagitData(config_dict, info_dict, manifest_dict, csv_data)


csv_string_v_1_1 = """Filepath,FileName,FileType,Filesize,RightsCopyright,LegalStatus,HeldBy,Language,FoiExemptionCode,LastModified\n""" + \
                   """data/content/file-c1.txt,file-c1.txt,File,12825,Crown Copyright,Public Record,TNA,English,open,2022-09-29T15:10:20\n""" + \
                   """data/content,content,Folder,,Crown Copyright,Public Record,TNA,English,open,\n"""

#  in version 1.2 of a TDR bagit we have changes:
#    -- `TNA` is replaced by `"The National Archives, Kew"` in the `HeldBy` column
#    -- `Public Record` is replaced by `Public Record(s)` in the `LegalStatus` column
#    -- `open` is instead empty in the `FoiExemptionCode` column

csv_string_v_1_2 = """Filepath,FileName,FileType,Filesize,RightsCopyright,LegalStatus,HeldBy,Language,FoiExemptionCode,LastModified,OriginalFilePath\n""" + \
                   """data/content/file-c1.txt,file-c1.txt,File,36,Crown Copyright,Public Record(s),"The National Archives, Kew",English,,2022-09-29T15:10:20,\n""" + \
                   """data/content,content,Folder,,Crown Copyright,Public Record(s),"The National Archives, Kew",English,,,\n"""


class TestBagitMethods(unittest.TestCase):

    maxDiff = None

    expected_metadata = """identifier,file_name,folder,date_last_modified,checksum,rights_copyright,legal_status,held_by,language,TDR_consignment_ref\n""" + \
                        """file:/MOCKA101Y22TBAA1/MOCKA_101/content/file-c1.txt,file-c1.txt,file,2022-09-29T15:10:20,5bd8879fba139fed98c048261cb2a91d727ceafb27414cc54e21c26915e9e40f,Crown Copyright,Public Record(s),"The National Archives, Kew",English,TDR-2022-AA1\n""" + \
                        """file:/MOCKA101Y22TBAA1/MOCKA_101/content/,content,folder,2022-07-18T12:45:45,,Crown Copyright,Public Record(s),"The National Archives, Kew",English,TDR-2022-AA1\n"""

    def test_bag_1_1_to_metadata(self):
        bagit = make_bagit(csv_string_v_1_1)
        actual_metadata = bagit.to_metadata(driConfig)
        self.assertEqual(actual_metadata, self.expected_metadata)

    def test_bag_1_2_to_metadata(self):
        bagit = make_bagit(csv_string_v_1_2)
        actual_metadata = bagit.to_metadata(driConfig)
        self.assertEqual(actual_metadata, self.expected_metadata)

    expected_closure = """identifier,folder,closure_start_date,closure_period,foi_exemption_code,foi_exemption_asserted,title_public,title_alternate,closure_type\n""" + \
                       """file:/MOCKA101Y22TBAA1/MOCKA_101/content/file-c1.txt,file,,0,open,,TRUE,,open_on_transfer\n""" + \
                       """file:/MOCKA101Y22TBAA1/MOCKA_101/content/,folder,,0,open,,TRUE,,open_on_transfer\n"""

    def test_bag_1_1_to_closure(self):
        bagit = make_bagit(csv_string_v_1_1)
        actual_closure = bagit.to_closure(driConfig)
        self.assertEqual(actual_closure, self.expected_closure)

    def test_bag_1_2_to_closure(self):
        bagit = make_bagit(csv_string_v_1_2)
        actual_closure = bagit.to_closure(driConfig)
        self.assertEqual(actual_closure, self.expected_closure)


if __name__ == '__main__':
    unittest.main()
