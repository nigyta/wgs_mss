#!/usr/bin/env python

import os
import sys
import math
import gzip
import logging
import argparse
from Bio import SeqIO
import pandas as pd
from src.main_mss_maker import create_mss
from src.gap_annotator import GapAnnotator
from src.schema_util import load_json_file, get_remote_schema, get_local_schema
# This script is to convert FASTA file to MSS format for GenBank submission


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


linkage_evidences = [
    "pcr", "paired-ends", "align_genus", "align_xgenus", "align_trnscpt", 
    "within_clone", "clone_contig", "map", "strobe", "proximity_ligation", 
    "unspecified"
]
gap_types = [
    "auto", "between_scaffolds", "within_scaffold", "telomere", "centromere", "short_arm", 
    "heterochromatin", "repeat_within_scaffold", "repeat between_scaffolds", "contamination", "unknown"
]

# parse arguments
parser = argparse.ArgumentParser(description='Convert FASTA file to MSS format for GenBank submission')
group1 = parser.add_mutually_exclusive_group(required=True)
group1.add_argument('--excel', type=str, help='Excel workbook file')
group1.add_argument('--tsv', type=str, help='TSV file')

# parser.add_argument('-f', '--fasta_list', help='Tab-separated table containing the list for the path to FASTA file and metaadata')
parser.add_argument('--sheet', type=str, help='Sheet name in the Excel workbook. --excel option is required (default: Sheet1)', default='Sheet1')

parser.add_argument('-m', '--metadata_json_file', help='Common metadata in JSON format (for submitter and reference)')
parser.add_argument('-o', '--out_dir', help='Output Directory', default=".")
# parser.add_argument('-c', '--category', choices=["draft_genome", "draft_mag"], 
#                     help='Submission category (default: draft_genome)', default='draft_genome')
parser.add_argument('-H', '--hold_date', help='Hold date for the submission, format="yyyymmdd"')
# parser.add_argument('-r', '--rename_sequence', action="store_true",help='Rename sequence ID. If set, the sequence ID will be renamed as sequence01, sequence02, ... (default: False)')
parser.add_argument('--linkage_evidence', choices=linkage_evidences, 
                    help='Linkage evidence for assembly_gap features, e.g. "paired-ends", "proximity ligation". (default: "paired-ends")', default="paired-ends")
parser.add_argument('--gap_type', choices=gap_types, 
                    help='Gap types for assembly_gap features, e.g. "within scaffold". (default: auto)', default='auto')
parser.add_argument('--gap_length', choices=["auto", "known", "unknown"], 
                    help='Estimated gap length. (default: auto)', default='auto')
parser.add_argument('--min_gap_length', type=int, 
                    help='Minimum gap length. (default: 10)', default=10)



if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)

args = parser.parse_args()

gap_annotator = GapAnnotator.initialize(parser.parse_args())

# load common metadata and schema
base_json_data = load_json_file(args.metadata_json_file)
base_schema = get_local_schema()

# load sample list from excel or tsv
if args.excel:
    df = pd.read_excel(args.excel, sheet_name=args.sheet, header=[0,1], dtype=str)
else:
    df = pd.read_csv(args.tsv, sep="\t", header=[0,1], dtype=str)
df.fillna("", inplace=True)


out_dir = args.out_dir
for i, row in df.iterrows():
    ret = create_mss(row, base_json_data, base_schema, out_dir, gap_annotator, hold_date=args.hold_date)
    # for row in ret:
    #     print("\t".join(map(str, row)))
    # print()

