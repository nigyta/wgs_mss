import pandas as pd
import os
import json
import datetime
from .schema_util import get_remote_schema, load_json_file, validate_json, get_subschema_for_category, set_default_to_json
import copy
from .json2mss import create_qualifier, create_feature, create_common
from .seq_util import create_source_feature, read_fasta, check_number_of_seqs
import math
from .gap_annotator import GapAnnotator

def initialize_json_data_and_schema(base_json_data, base_schema, _trad_submission_category):
    """
    initilize json data and json schema for the given submission category.
    only internally used from row_to_dict
    """
    json_data = copy.deepcopy(base_json_data)
    schema = copy.deepcopy(base_schema)
    get_subschema_for_category(schema, _trad_submission_category)
    json_data["_trad_submission_category"] = _trad_submission_category
    set_default_to_json(json_data, schema)
    return json_data, schema



def row_to_dict(row: pd.Series, base_json_data: dict, base_schema: dict) -> tuple[str, str, dict, dict, dict, dict]:
    """
    Create JSON files from the row data in the Excel file.
    """

    def str2array(value: str) -> list[str]:
        return [v.strip() for v in value.split(";")]

    _trad_submission_category = row[("_", "_trad_submission_category")]
    file_path = row[("_", "_file_path")]
    json_data, schema = initialize_json_data_and_schema(base_json_data, base_schema, _trad_submission_category)
    dict_sequence = {}
    dict_source = {}

    for feature_name, qualifier_key in row.index:
        # print(f"{feature_name}, {qualifier_key}: {S[(feature_name, qualifier_key)]}")
        value = row[(feature_name, qualifier_key)]
        # feature_obj = json_data.get(feature_name)  # array for COMMENT and REFERENCE
        if not value:
            continue
        if feature_name == "-":
            continue
        elif feature_name == "_sequence":
            if qualifier_key in ["seq_names", "seq_types", "seq_topologies"]:
                value = str2array(value)
            dict_sequence[qualifier_key] = value
        elif feature_name == "source":
            if qualifier_key == "collection_date" and (isinstance(value, pd.Timestamp) or isinstance(value, datetime.datetime)):
                value = value.strftime("%Y-%m-%d")
            dict_source[qualifier_key] = value
        elif feature_name == "COMMENT":
            values = str2array(value)
            json_data.setdefault(feature_name, []).append({qualifier_key: values})
        elif qualifier_key in ["biosample", "sequence read archive"]:
            value = value.replace(";", ",")
            values = [v.strip() for v in value.split(",")]
            json_data.setdefault(feature_name, {})[qualifier_key] = values
        else:
            json_data.setdefault(feature_name, {})[qualifier_key] = value

    # validate_json(json_data, schema)

    return file_path, _trad_submission_category, json_data, dict_sequence, dict_source, schema


def create_mss(S: pd.Series, base_json_data: dict, base_schema: dict, out_dir: str, gap_annotator: GapAnnotator|None=None, hold_date: str|None=None) -> list[list[str]]:
    file_path, _trad_submission_category, json_data, dict_sequence, dict_source, schema = row_to_dict(S, base_json_data, base_schema)

    annot = create_common(json_data)  # COMMON Feature (list of 5-element lists)
    if hold_date:
        annot.append(["", "DATE", "", "hold_date", hold_date])

    # creating source feature and assembly_gap feature
    if _trad_submission_category in ["GNM", "MAG"]:
        seq_records = read_fasta(file_path)
        check_number_of_seqs(seq_records, dict_sequence)
        for seq_record, seq_name, seq_type, seq_topology in zip(seq_records, dict_sequence["seq_names"], dict_sequence["seq_types"], dict_sequence["seq_topologies"]):
            source_feature = create_source_feature(_trad_submission_category, seq_name, seq_type, seq_topology, dict_source)
            annot += source_feature
            # add gap features
            if gap_annotator:
                annot += gap_annotator.create_gap_feature(str(seq_record.seq), seq_name=None)
            seq_record.id = seq_name
            seq_record.name, seq_record.description = "", ""

    elif _trad_submission_category in ["WGS", "MAG-WGS"]:
        seq_records = read_fasta(file_path)
        seq_prefix = dict_sequence.get("seq_prefix")
        seq_name, seq_type, seq_topology = None, None, None
        source_feature = create_source_feature(_trad_submission_category, seq_name, seq_type, seq_topology, dict_source)
        annot += source_feature
        num_width = int(math.log10(len(seq_records))) + 1
        for i, seq_record in enumerate(seq_records, 1):
            if seq_prefix:
                seq_name = f"{seq_prefix}_{str(i).zfill(num_width)}"
            else:
                seq_name = seq_record.id
            if gap_annotator:
                annot += gap_annotator.create_gap_feature(str(seq_record.seq), seq_name)
            seq_record.id = seq_name
            seq_record.name, seq_record.description = "", ""

    biosample = json_data.get("DBLINK", {}).get("biosample", ["NO_BIOSAMPLE"])
    biosample = ",".join(biosample)
    strain = dict_source.get("strain")
    isolate = dict_source.get("isolate")
    identifier = strain or isolate or "NO_IDENTIFIER"
    prefix = f"{biosample}_{identifier}".replace(" ", "_")
    output(out_dir, prefix, annot, seq_records)

    # return annot, seq_records

def output(out_dir, prefix, annot, seq_records):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    out_annot = os.path.join(out_dir, f"{prefix}.ann")
    out_seq = os.path.join(out_dir, f"{prefix}.fa")
    with open(out_annot, "w") as f:
        for row in annot:
            f.write("\t".join(map(str, row)) + "\n")
    with open(out_seq, "w") as f:
        for seq_record in seq_records:
            f.write(seq_record.format("fasta"))
            f.write("//\n")
