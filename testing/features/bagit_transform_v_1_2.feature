Feature: Verify bagit transforms to dri closure.csv / metadata.csv.

#  in version 1.2 of a TDR bagit we have changes:
#    -- `TNA` is replaced by `"The National Archives, Kew"` in the `HeldBy` column
#    -- `Public Record` is replaced by `Public Record(s)` in the `LegalStatus` column
#    -- `open` is instead empty in the `FoiExemptionCode` column

  Scenario: Verify a file's closure in TDR version 1.2

    Given a bagit with files that include:
      | File                | Field                          | Value                              |
      | bag-info.txt        | Consignment-Series             | MOCKA 101                          |
      | bag-info.txt        | Internal-Sender-Identifier     | TDR-2022-AA1                       |
      | file-metadata.csv   | Filepath                       | data/content/folder-a/file-a1.txt  |
      | file-metadata.csv   | FileType                       | File                               |
      | file-metadata.csv   | FoiExemptionCode               |                                    |

    When transform that bagit to make closure.csv

    Then the file closure.csv has:
      | Field                  | Value                                                            |
      | identifier             | file:/MOCKA101Y22TBAA1/MOCKA_101/content/folder-a/file-a1.txt    |
      | folder                 | file                                                             |
      | closure_start_date     |                                                                  |
      | closure_period         | 0                                                                |
      | foi_exemption_code     | open                                                             |
      | foi_exemption_asserted |                                                                  |
      | title_public           | TRUE                                                             |
      | title_alternate        |                                                                  |
      | closure_type           | open_on_transfer                                                 |

  Scenario: Verify a folder's closure in TDR version 1.2

    Given a bagit with files that include:
      | File                | Field                          | Value                              |
      | bag-info.txt        | Consignment-Series             | MOCKA 101                          |
      | bag-info.txt        | Internal-Sender-Identifier     | TDR-2022-AA1                       |
      | file-metadata.csv   | Filepath                       | data/content/folder-a              |
      | file-metadata.csv   | FileType                       | Folder                             |
      | file-metadata.csv   | FoiExemptionCode               |                                    |

    When transform that bagit to make closure.csv

    Then the file closure.csv has:
      | Field                  | Value                                                            |
      | identifier             | file:/MOCKA101Y22TBAA1/MOCKA_101/content/folder-a/               |
      | folder                 | folder                                                           |
      | closure_start_date     |                                                                  |
      | closure_period         | 0                                                                |
      | foi_exemption_code     | open                                                             |
      | foi_exemption_asserted |                                                                  |
      | title_public           | TRUE                                                             |
      | title_alternate        |                                                                  |
      | closure_type           | open_on_transfer                                                 |

  Scenario: Verify a file's metadata in TDR version 1.2

    Given a bagit with files that include:
      | File                | Field                          | Value                              |
      | bag-info.txt        | Consignment-Series             | MOCKA 101                          |
      | bag-info.txt        | Internal-Sender-Identifier     | TDR-2022-AA1                       |
      | bag-info.txt        | Consignment-Export-Datetime    | 2022-07-18T12:45:45Z               |
      | manifest-sha256.txt | checksum                       | 4ef13f1d2350fe1e9f79a88ec063031f65da834e8afdd0512e230544cca0a34b |
      | manifest-sha256.txt | file                           | data/content/folder-a/file-a1.txt  |
      | file-metadata.csv   | Filepath                       | data/content/folder-a/file-a1.txt  |
      | file-metadata.csv   | FileType                       | File                               |
      | file-metadata.csv   | LegalStatus                    | Public Record(s)                   |
      | file-metadata.csv   | HeldBy                         | The National Archives, Kew         |
      | file-metadata.csv   | FileName                       | file-a1.txt                        |
      | file-metadata.csv   | LastModified                   | 2022-07-18T00:00:00                |
      | file-metadata.csv   | RightsCopyright                | Crown Copyright                    |
      | file-metadata.csv   | Language                       | English                            |

    When transform that bagit to make metadata.csv

    Then the file metadata.csv has:
      | Field                  | Value                                                            |
      | identifier             | file:/MOCKA101Y22TBAA1/MOCKA_101/content/folder-a/file-a1.txt    |
      | file_name              | file-a1.txt                                                      |
      | folder                 | file                                                             |
      | date_last_modified     | 2022-07-18T00:00:00                                              |
      | checksum               | 4ef13f1d2350fe1e9f79a88ec063031f65da834e8afdd0512e230544cca0a34b |
      | rights_copyright       | Crown Copyright                                                  |
      | legal_status           | Public Record(s)                                                 |
      | held_by                | The National Archives, Kew                                       |
      | language               | English                                                          |
      | TDR_consignment_ref    | TDR-2022-AA1                                                     |


  Scenario: Verify a folder's metadata in TDR version 1.2

    Given a bagit with files that include:
      | File                | Field                          | Value                              |
      | bag-info.txt        | Consignment-Series             | MOCKA 101                          |
      | bag-info.txt        | Internal-Sender-Identifier     | TDR-2022-AA1                       |
      | bag-info.txt        | Consignment-Export-Datetime    | 2022-07-18T12:45:45Z               |
      | file-metadata.csv   | Filepath                       | data/content/folder-a              |
      | file-metadata.csv   | FileType                       | Folder                             |
      | file-metadata.csv   | FileName                       | folder-a                           |
      | file-metadata.csv   | LegalStatus                    | Public Record(s)                   |
      | file-metadata.csv   | HeldBy                         | The National Archives, Kew         |
      | file-metadata.csv   | RightsCopyright                | Crown Copyright                    |
      | file-metadata.csv   | Language                       | English                            |

    When transform that bagit to make metadata.csv

    Then the file metadata.csv has:

      | identifier             | file:/MOCKA101Y22TBAA1/MOCKA_101/content/folder-a/               |
      | file_name              | folder-a                                                         |
      | folder                 | folder                                                           |
      | date_last_modified     | 2022-07-18T12:45:45                                              |
      | checksum               |                                                                  |
      | rights_copyright       | Crown Copyright                                                  |
      | legal_status           | Public Record(s)                                                 |
      | held_by                | The National Archives, Kew                                       |
      | language               | English                                                          |
      | TDR_consignment_ref    | TDR-2022-AA1                                                     |
