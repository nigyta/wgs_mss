#%%
import pandas as pd
import urllib.request
import json
import datetime
from schema_util import get_remote_schema, load_json_file, validate_json, get_subschema_for_category, set_default_to_json
import copy
from json2mss import create_qualifier, create_feature, create_common
from seq_util import create_source_feature, read_fasta, check_number_of_seqs, create_gap_feature
import math
jsaon_schema_url = "https://raw.githubusercontent.com/ddbj/template_generator_api/main/src/dev_schemas/MSS_COMMON_template.json"


#%%
common_json_data = load_json_file("example/common_example.json")
common_schema = get_remote_schema()


#%%
def get_base_data(common_json_data, common_schema, _trad_submission_category):
    base_json_data = copy.deepcopy(common_json_data)
    base_schema = copy.deepcopy(common_schema)
    get_subschema_for_category(base_schema, _trad_submission_category)
    base_json_data["_trad_submission_category"] = _trad_submission_category
    set_default_to_json(base_json_data, base_schema)
    return base_json_data, base_schema

# base_json_data, base_schema = get_base_data(common_json_data, common_schema, "WGS")
# print(base_json_data)
# print(base_schema)


#%%
# conda install pandas openpyxl


sample_list_xls_file = "example/sample_list.xlsx"

df = pd.read_excel(sample_list_xls_file, sheet_name="WGS", header=[0,1])
df.fillna("", inplace=True)
# print(df)
# print(df.columns)

# print(df.iloc[0].index)
S=df.iloc[1]

def row_to_dict(row: pd.Series, common_json_data: dict, common_schema: dict) -> tuple[str, str, dict, dict, dict, dict]:
    """
    Create JSON files from the row data in the Excel file.
    """

    def str2array(value: str) -> list[str]:
        value = value.replace(";", ",")
        return [v.strip() for v in value.split(",")]

    _trad_submission_category = row[("_", "_trad_submission_category")]
    file_path = row[("_", "_file_path")]
    json_data, schema = get_base_data(common_json_data, common_schema, _trad_submission_category)
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

def create_mss(S: pd.Series, common_json_data: dict, common_schema: dict) -> list[list[str]]:
    file_path, _trad_submission_category, json_data, dict_sequence, dict_source, schema = row_to_dict(S, common_json_data, common_schema)

    ret = create_common(json_data)

    if _trad_submission_category in ["GNM", "MAG"]:
        seq_list = read_fasta(file_path)
        check_number_of_seqs(seq_list, dict_sequence["seq_names"], dict_sequence["seq_types"], dict_sequence["seq_topologies"])
        for seq, seq_name, seq_type, seq_topology in zip(seq_list, dict_sequence["seq_names"], dict_sequence["seq_types"], dict_sequence["seq_topologies"]):
            source_feature = create_source_feature(_trad_submission_category, seq_name, seq_type, seq_topology, dict_source)
            ret += source_feature
            # add gap features
            ret += create_gap_feature(str(seq.seq), seq_name=None)

    elif _trad_submission_category in ["WGS", "MAG-WGS"]:
        seq_list = read_fasta(file_path)
        seq_prefix = dict_sequence.get("seq_prefix")
        seq_name, seq_type, seq_topology = None, None, None
        source_feature = create_source_feature(_trad_submission_category, seq_name, seq_type, seq_topology, dict_source)
        ret += source_feature
        num_width = int(math.log10(len(seq_list))) + 1
        for i, seq in enumerate(seq_list, 1):
            if seq_prefix:
                seq_name = f"{seq_prefix}_{str(i).zfill(num_width)}"
            else:
                seq_name = seq.id
            ret += create_gap_feature(str(seq.seq), seq_name=seq_name)

    return ret

for i, row in df.iterrows():
    ret = create_mss(row, common_json_data, common_schema)
    for row in ret:
        print("\t".join(map(str, row)))
    print()

# ret = create_mss(S, common_json_data, common_schema)
# for row in ret:
#     print("\t".join(map(str, row)))

# file_path, _trad_submission_category, json_data, dict_sequence, dict_source, schema = row_to_dict(S, common_json_data, common_schema)

# # print(json_data)
# # # print(schema)
# print(dict_source)
# # print(dict_sequence)

# common = create_common(json_data)

# if _trad_submission_category in ["GNM", "MAG"]:
#     seq_list = read_fasta(file_path)
#     check_number_of_seqs(seq_list, dict_sequence["seq_names"], dict_sequence["seq_types"], dict_sequence["seq_topologies"])
#     for seq, seq_name, seq_type, seq_topology in zip(seq_list, dict_sequence["seq_names"], dict_sequence["seq_types"], dict_sequence["seq_topologies"]):
#         source_feature = create_source_feature(_trad_submission_category, seq_name, seq_type, seq_topology, dict_source)
#         common += source_feature
#         # add gap features
#         common += create_gap_feature(str(seq.seq), seq_name=None)

# elif _trad_submission_category in ["WGS", "MAG-WGS"]:
#     seq_list = read_fasta(file_path)
#     seq_name, seq_type, seq_topology = None, None, None
#     source_feature = create_source_feature(_trad_submission_category, seq_name, seq_type, seq_topology, dict_source)
#     common += source_feature
#     for seq in seq_list:
#         common += create_gap_feature(str(seq.seq), seq_name=seq.id)


# exit()

exit()
_trad_submission_category = S[("_", "_trad_submission_category")]
# print(_trad_submission_category)
for feature_name, qualifier_key in S.index:


    # print(f"{feature_name}, {qualifier_key}: {S[(feature_name, qualifier_key)]}")
    value = S[(feature_name, qualifier_key)]
    # feature_obj = base_json_data.get(feature_name)  # array for COMMENT and REFERENCE
    if feature_name in ["_", "_sequence"]:
        continue

    if not value:
        continue
    if feature_name == "COMMENT":
        base_json_data.setdefault(feature_name, []).append({qualifier_key: value})
    elif qualifier_key in ["biosample", "sequence read archive"]: # array data
        value = value.replace(";", ",")
        values = [v.strip() for v in value.split(",")]
        base_json_data.get(feature_name, {})[qualifier_key] = values
    else:
        base_json_data.setdefault(feature_name, {})[qualifier_key] = value

            # if isinstance(qualifier_obj, list):
            #     print("DEBUG", value)
            #     values = [v.strip() for v in value.split(",")]
            #     base_json_data.get(feature_name, {})[qualifier_key] = values
            # elif isinstance(qualifier_obj, dict):
            #     base_json_data.get(feature_name, {})[qualifier_key] = value
            # elif isinstance(qualifier_obj, str):
            #     base_json_data.get(feature_name, {})[qualifier_key] = value
            # elif qualifier_obj is None:
            #     base_json_data.get(feature_name, {})[qualifier_key] = value
            # else:
            #     print(qualifier_obj)
            #     print(f"{feature_name}, {qualifier_key}: {S[(feature_name, qualifier_key)]}")
            #     raise AssertionError
            # base_json_data.setdefault(feature_name, {})[qualifier_key]

print(base_json_data)
z = create_common(base_json_data)
for row in z:
    print("\t".join(map(str, row)))
exit()
# %%
S=df.iloc[0]
# %%
for i in S.index:
    print(i)

#%%
def get_schema():
    try:
        with urllib.request.urlopen(jsaon_schema_url) as response:
            data = response.read()
            json_data = json.loads(data.decode())
            return json_data    
    except urllib.error.HTTPError as http_err:
        print(f"HTTP error. Failed to retrieve a remote file: {http_err}")
    except Exception as err:
        print(f"Unexpected Error while retrieving a remote file: {err}")

schema = get_schema()

#%%
# def apply_default


# %%
def row_to_dict(row: pd.Series) -> dict:
    d = {}
    for i, v in enumerate(row):
        if v:
            d[i] = v
    return d