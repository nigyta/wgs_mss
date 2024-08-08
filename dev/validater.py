import urllib.request
import json
from jsonschema import validate, ValidationError

schema_url = "https://raw.githubusercontent.com/ddbj/template_generator_api/main/src/dev_schemas/MSS_COMMON_template.json"
schema_local_filename = "MSS_COMMON_template.json"


def download_json_file(url, local_filename):
    try:
        # URLからデータを取得する
        with urllib.request.urlopen(url) as response:
            data = response.read().decode('utf-8')

        # JSONデータをファイルに保存する
        with open(local_filename, 'w', encoding='utf-8') as file:
            file.write(data)

        print(f"ファイルが正常にダウンロードされ、{local_filename} に保存されました。")
    except urllib.error.HTTPError as http_err:
        print(f"HTTPエラーが発生しました: {http_err}")
    except Exception as err:
        print(f"エラーが発生しました: {err}")

def load_json_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as err:
        print(f"ファイルの読み込み中にエラーが発生しました: {err}")
        return None

def validate_json(json_data, schema):
    try:
        validate(instance=json_data, schema=schema)
        print("JSONデータはスキーマに従っています。")
    except ValidationError as err:
        print(f"バリデーションエラー: {err.message}")
    except Exception as err:
        print(f"バリデーション中にエラーが発生しました: {err}")

from jsonschema import Draft202012Validator, validators

# definitions = schema.get("definitions", {})

def get_subschema_for_category(schema, category):
    def _check_category(subschema):
        return category == subschema.get("if", {}).get("properties", {}).get("_trad_submission_category", {}).get("const", "")
    subschemas = [subschema for subschema in schema.get("allOf", []) if _check_category(subschema)]
    properties = {}
    required = []
    for subschema in subschemas:
        properties.update(subschema.get("then", {}).get("properties", {}))
        required += subschema.get("then", {}).get("required", [])
    del schema["allOf"]
    schema.setdefault("properties", {}).update(properties)
    schema.setdefault("required",[]).extend(required)

def extend_with_default(validator_class):
    # デフォルの値を設定する
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in properties.items():
            # print(f"{property=}, {subschema=}, {instance=}")
            # if len(subschema) == 1 and "$ref" in subschema:
            # print(f"{property=}\n{subschema=}\n{instance=}\n======")
            if "$ref" in subschema:
                # if "definitions" not in schema:
                #     print("----")
                #     print(schema)
                #     exit()
                definition_subchema = definitions[subschema["$ref"].split("/")[-1]]
                definition_subchema.update(subschema)
                subschema = definition_subchema
                del subschema["$ref"]
                # print("ref", subschema)
            if "default" in subschema:
                # print("-"*10)
                # print(f"Default value found: {subschema['default']}, {instance=}")
                instance.setdefault(property, subschema["default"])
                # print(f"Applied default, {instance=}")
                # print("-"*10)
            if subschema.get("type") == "object":
                set_defaults(validator, subschema.get("properties", {}), instance.setdefault(property, {}), schema)
            elif subschema.get("type") == "array" and property == "REFERENCE":
                for item in instance.setdefault(property, [{}]):
                    if subschema.get("items", {}).get("type") == "object":
                        set_defaults(validator, subschema.get("items", {}).get("properties", {}), item, schema)

        # for error in validate_properties(
        #     validator, properties, instance, schema,
        # ):
        #     yield error

    return validators.extend(
        validator_class, {"properties" : set_defaults},
    )



# download_json_file(schema_url, schema_local_filename)

# ダウンロードしたJSONファイルを読み込み
schema = load_json_file(schema_local_filename)
definitions = schema.get("definitions", {})

DefaultValidatingValidator = extend_with_default(Draft202012Validator)


# スキーマを定義（ここでは例として、簡単なスキーマを定義します）
json_data = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "type": {"type": "string"},
        "properties": {"type": "object"}
    },
    "required": ["title", "type", "properties"]
}

# json_data = json.load(open('example.json', 'r', encoding='utf-8'))


# # JSONデータをバリデート
# if json_data is not None:
#     validate_json(json_data, schema)


json_data = {}
# category = "MAG-WGS"
category = "MAG"
# obj = {"_trad_submission_category": category, "DBLINK": {"biosample": ["SAMD99999"]}, "REFERENCE": [{"title": "title1", "ab_name": ["Tanizawa,Y.", "Fujisawa,T."]}], "SUBMITTER": {"contact": "YT", "phone": "1234567890"}}
obj = {"_trad_submission_category": category}
get_subschema_for_category(schema, category)

# Note jsonschema.validate(obj, schema, cls=DefaultValidatingValidator)
# will not work because the metaschema contains `default` keywords.
DefaultValidatingValidator(schema).validate(obj)

print(json.dumps(obj, indent=2,))


# validate_json(obj, schema)

# print(schema)

# import jsonschema_default
# default_obj = jsonschema_default.create_from(schema)
# print(default_obj)
