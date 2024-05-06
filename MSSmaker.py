#!/usr/bin/env python

import os
import sys
import re
import math
import gzip
import logging
import argparse
from Bio import SeqIO

# This script is to convert FASTA file to MSS format for GenBank submission

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
parser.add_argument('-f', '--fasta_list', help='Tab-separated table containing the list for the path to FASTA file and metaadata')
parser.add_argument('-m', '--metadata_file', help='Common metadata file (for submitter and reference)')
parser.add_argument('-o', '--outdir', help='Output Directory')
parser.add_argument('-c', '--category', choices=["draft_genome", "draft_mag", "complete_genome", "complete_mag"], 
                    help='Submission category (default: draft_genome)', default='draft_genome')
parser.add_argument('-H', '--hold_date', help='Hold date for the submission, format="yyyymmdd"')
parser.add_argument('-r', '--rename_sequence', action="store_true",help='Rename sequence ID. If set, the sequence ID will be renamed as sequence01, sequence02, ... (default: False)')
parser.add_argument('--linkage_evidence', choices=linkage_evidences, 
                    help='Linkage evidence for assembly_gap features, e.g. "paired-ends", "proximity ligation". (default: "paired-ends")', default="paired-ends")
parser.add_argument('--gap_type', choices=gap_types, 
                    help='Gap types for assembly_gap features, e.g. "within scaffold". (default: auto)', default='auto')
parser.add_argument('--gap_length', choices=["auto", "known", "unknown"], 
                    help='Estimated gap length. (default: auto)', default='auto')
parser.add_argument('--min_gap_length', type=int, 
                    help='Minimum gap length. (default: auto)', default=10)



if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)

args = parser.parse_args()
print(args)
print(args.min_gap_length)


# constant values for assembly_gap feature
# see https://www.ncbi.nlm.nih.gov/assembly/agp/AGP_Specification/
MIN_GAP_LENGTH = args.min_gap_length  # Default 10, Recommendation from the curation staff
LINKAGE_EVIDENCE = args.linkage_evidence.replace("_", "")  # default "paired-ends"  # paired-ends, align genus, proximity ligation, etc. 

if args.gap_type == "auto":
    if LINKAGE_EVIDENCE == "paired-ends":
        GAP_TYPE = "within scaffolds"
    elif LINKAGE_EVIDENCE == "proximity ligation":
        GAP_TYPE = "within scaffolds"
    else:
        raise AssertionError("Please specify gap_type")
else:
    GAP_TYPE = args.gap_type.replace("_", " ")  # within scaffold, between scaffolds, telomere, centromere, short arm, heterochromatin, repeat_within_scaffold, repeat between_scaffolds, contamination, unknown
GAP_TYPE = "within scaffold"  # see https://www.ddbj.nig.ac.jp/ddbj/qualifiers.html#gap_type
if args.gap_length == "auto":
    if LINKAGE_EVIDENCE == "paired-ends":
        GAP_LENGTH = "known"
    elif LINKAGE_EVIDENCE == "proximity ligation":
        GAP_LENGTH = "unknown"
    else:
        raise AssertionError("Please specify gap_length")
else:
    GAP_LENGTH = args.gap_length # known or unknown 

gap_pattern = re.compile('n{%d,}' % MIN_GAP_LENGTH)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_gap_feature(seq):
    """
    Create assembly_feature
    If length_estimated is True, estimated_length is "known", otherwise "unknown"
    MIN_GAP_LENGTH, GAP_TYPE, LINKAGE_EVIDENCE are specific to Marchantia genome, and need adjustment for other species.
    """
    ret = []
    # length_value = "known" if GAP_LENGTH else "unknown"

    for match in gap_pattern.finditer(seq.lower()):
        start = match.start() + 1  # +1 because INSDC coordinate is 1-based
        end = match.end()
        location = f"{start}..{end}"
        ret.append(["", "assembly_gap", location, "estimated_length", GAP_LENGTH])
        ret.append(["", "", "", "gap_type", GAP_TYPE])
        ret.append(["", "", "", "linkage_evidence", LINKAGE_EVIDENCE])

    return ret

def read_fasta(file_name):
    if file_name.endswith(".gz"):
        return list(SeqIO.parse(gzip.open(file_name, "rt"), "fasta"))
    else:
        return list(SeqIO.parse(file_name, "fasta"))


def read_template_file(template_file):
    with open(template_file) as f:
        template = f.read()
    return template

def join_table(table):

    return "\n".join(["\t".join(x) for x in table]) + "\n"

def make_dblink(metadata):
    allow_list = ["project", "biosample", "sequence_read_archive"]
    ret = []
    for qualifier in allow_list:
        values = metadata.get(qualifier, "")
        if values:
            for value in values.split(";"):
                ret.append(["", "", "", qualifier, value.strip()])
    if ret:
        ret[0][1] = "DBLINK"
    return ret

def add_comment_and_st_comments(metadata, tagset="genome"):
    ret = []
    if "genome" in tagset.lower():
        tagset_id = "Genome-Assembly-Data"
        allow_list = ["Assembly Method", "Assembly Name", "Genome Coverage", "Sequencing Technology"]
    else:
        tagset_id = "Assembly-Data"
        allow_list = ["Assembly Method", "Assembly Name", "Coverage", "Sequencing Technology"]
    ret.append(["", "ST_COMMENT", "", "tagset_id", tagset_id])
    for qualifier in allow_list:
        value = metadata.get(qualifier, "")
        if qualifier in ["Genome Coverage", "Coverage"] and value == "":
            value = "Unknown"
        if value:
            ret.append(["", "", "", qualifier, value])
    if metadata.get("comment"):
        ret_comment = []
        lines = metadata["comment"]
        for line in lines.split(";"):
            ret_comment.append(["", "", "", line, line.strip()])
        if ret_comment:
            ret_comment[0][1] = "COMMENT"
            ret.extend(ret_comment)
    return ret

def add_hold_date(hold_date):
    return [["", "DATE", "", "date", hold_date]]

def make_source_feature(metadata, entry=""):
    allow_list = ["organism", "strain", "isolate", "db_xref", "country", "collection_date"]
    ret = []
    ret.append([entry, "source", "1..E", "mol_type", "genomic DNA"])
    for qualifier in allow_list:
        value = metadata.get(qualifier, "")
        if value:
            ret.append(["", "", "", qualifier, value])
    ret.append(["", "", "", "submitter_seqid", "@@[entry]@@"])
    ret.append(["", "", "", "ff_definition", "@@[entry]@@"])
    return ret

def make_common_entry(template, metadata, category="draft_genome"):

    categories = {
        "draft_genome": {"DATATYPE": "WGS", "KEYWORD": ["WGS", "STANDARD_DRAFT"]},
        "draft_mag": {"DIVISION": "ENV", "DATATYPE": "WGS", "KEYWORD": ["WGS", "STANDARD_DRAFT", "ENV", "MAG", "Metagenome Assembled Genome"]},
        "complete_genome": {},
        "complete_mag": {"DIVISION": "ENV", "KEYWORD": ["ENV", "MAG", "Metagenome Assembled Genome"]},
    }
    qualifiers = {"DIVISION": "division", "DATATYPE": "type", "KEYWORD": "keyword"}

    category_data = categories[category]
    ret = []
    for feature, values in category_data.items():
        qualifier = qualifiers[feature]
        if isinstance(values, list):
            for i, value in enumerate(values):
                if i == 0:
                    ret.append(["", feature, "", qualifier, value])
                else:
                    ret.append(["", "", "", qualifier, value])
        else:
            ret.append(["", feature, "", qualifier, values])
    ret.extend(make_dblink(metadata))
    if ret:
        ret[0][0] = "COMMON"
    else:
        raise AssertionError("No data in COMMON entry. BioProject and BioSample are required.")
    return ret


def create_mss_files(fasta_file, template_file, metadata, out_dir, category="draft_genome", hold_date=None, rename_sequence=False):
    logger.info(f"Input Files ====================")
    logger.info(f"\tFASTA file: {fasta_file}")
    logger.info(f"\tTemplate file: {template_file}")

    suffix = metadata.get("biosample") or os.path.basename(fasta_file).rsplit(".", 1)[0]
    prefix = metadata.get("strain") or metadata.get("isolate") or metadata.get("clone") or "unknown"
    out_base = suffix + "_" + prefix
    out_seq_file = os.path.join(out_dir, out_base + ".fa")
    out_ann_file = os.path.join(out_dir, out_base + ".ann")

    logger.info(f"Output Files ===================")
    logger.info(f"\tSeq file: {out_seq_file}")
    logger.info(f"\tAnnotation file: {out_ann_file}")

    logger.info(f"Converting FASTA file to MSS format")
    template = read_template_file(template_file)
    mss_out = join_table(make_common_entry(template, metadata, category=category))
    mss_out += template
    mss_out += join_table(add_comment_and_st_comments(metadata))
    if hold_date:
        mss_out += join_table(add_hold_date(hold_date))
    mss_out += join_table(make_source_feature(metadata))
    R = read_fasta(fasta_file)
    if rename_sequence:
        num_seq = len(R)
        seq_width = int(math.log10(num_seq)) + 1
        logger.info(f"Number of sequences: {num_seq}")
        logger.info(f"Sequence IDs will be renamed as sequence{'1'.zfill(seq_width)}, sequence{'1'.zfill(seq_width)}, ... sequence{str(num_seq).zfill(seq_width)}")
    logger.info(f"Writing sequence file to {out_seq_file}")
    f_seq = open(out_seq_file, "w")
    ret = []
    for i, r in enumerate(R, 1):
        # print(r.id, len(r.seq))
        r.name, r.description = "", ""
        if rename_sequence:
            
            r.id = f"sequence{str(i).zfill(seq_width)}"
        f_seq.write(r.format("fasta") + "//\n")
        assembly_gaps = create_gap_feature(str(r.seq))
        if assembly_gaps:
            assembly_gaps[0][0] = r.id
            ret.extend(assembly_gaps)
    f_seq.close()
    mss_out += join_table(ret)
    logger.info(f"Writing annotation file to {out_ann_file}")
    with open(out_ann_file, "w") as f_ann:
        f_ann.write(mss_out)

def read_sample_list(sample_list_file):
    with open(sample_list_file) as f:
        lines = [x.strip() for x in f]
        header = lines[0].split("\t")
        for line in lines[1:]:
            cols = line.split("\t")
            fasta_file = cols[0]
            metadata = {}
            for qualifer, value in zip(header[1:], cols[1:]):
                metadata[qualifer] = value
            yield fasta_file, metadata

def create_mss_files_from_list(sample_list_file, template_file, out_dir, category="draft_genome", hold_date=None, rename_sequence=False):
    for fasta_file, metadata in read_sample_list(sample_list_file):
        create_mss_files(fasta_file, template_file, metadata, out_dir, category=category,hold_date=hold_date, rename_sequence=rename_sequence)


create_mss_files_from_list(args.fasta_list, args.metadata_file, args.outdir, 
                           category=args.category, hold_date=args.hold_date, rename_sequence=args.rename_sequence)


# if __name__ == "__main__":
#     sample_list_file = "file_list_example.tsv"
#     template_file = "metadata_wgs_example.tsv"
#     out_dir = "."
#     create_mss_files_from_list(sample_list_file, template_file, out_dir, category="draft_mag")

#     # fasta_file = "example/GCA_003307255.1.fna"
#     # template_file = "example/metadata_wgs_example.tsv"
#     # metadata = {
#     #     "project": "PRJNA123",
#     #     "biosample": "SAMN123",
#     #     "sequence_read_archive": "SRR123",
#     #     "Assembly Method": "Unknown",
#     #     "Assembly Name": "Unknown",
#     #     "Genome Coverage": "Unknown",
#     #     "Sequencing Technology": "Unknown",
#     #     "organism": "Marchantia polymorpha",
#     #     "strain": "Tak-1",
#     #     "country": "Japan",
#     #     "collection_date": "2018"
#     # }
#     # out_dir = "example"
#     # create_mss_files(fasta_file, template_file, metadata, out_dir, category="draft_mag")
