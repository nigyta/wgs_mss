import json

def create_qualifier(qualifier_key: str, value: str|list) -> list[list[str]]:
    ret = []
    if isinstance(value, list):  # For array data
        for v in value:
            ret.append(["", "", "", qualifier_key, v])
    else:  # For string
        ret.append(["", "", "", qualifier_key, value])
    return ret


def sort_st_comment(qualifier_keys: list[str]) -> list[str]:
    return [k for k in qualifier_keys if k == "tagset_id"] + sorted([k for k in qualifier_keys if k != "tagset_id"])

def create_feature(feature_name: str, feature_values: dict|list) -> list[list[str]]:
    ret = []
    if isinstance(feature_values, list):  # For array data (REFERENCE and COMMENT)
        for v in feature_values:
            ret.extend(create_feature(feature_name, v))
    elif feature_name == "ST_COMMENT":  # qualifier must be sorted in alphabetical order
        qualifier_keys = sort_st_comment(feature_values.keys())
        for qualifier_key in qualifier_keys:
            ret.extend(create_qualifier(qualifier_key, feature_values[qualifier_key]))
    else:
        for qualifier_key, value in feature_values.items():
            ret.extend(create_qualifier(qualifier_key, value))
    if ret:
        ret[0][1] = feature_name
    return ret

def create_common(common_json: dict) -> list[list[str]]:
    ret = []
    for feature_name, feature_values in common_json.items():
        if not feature_name.startswith("_"):
            ret.extend(create_feature(feature_name, feature_values))
    if ret:
        ret[0][0] = "COMMON"
    return ret

if __name__ == "__main__":
    import sys
    input_json = sys.argv[1]

    with open(input_json, "r") as f:
        common_json = json.load(open(input_json, "r"))
    common = create_common(common_json)

    for row in common:
        row = map(str, row)
        print("\t".join(row))

