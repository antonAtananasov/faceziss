import json
import textwrap


def objectToDict(obj: any) -> dict:
    result = {}
    methods = []
    exceptions = []

    knownTypes = (bool, str, int, float, type(None), list)

    for attr in dir(obj):
        if attr.startswith("_" * 2):
            continue
        value = None
        try:
            value = getattr(obj, attr)
            if ".method" in value.__repr__():
                methods.append(f"{attr}()")
            else:
                if isinstance(value, knownTypes):
                    result[attr] = value
                elif isinstance(value, dict):
                    if value:
                        result[attr] = value
                else:
                    dictVal = objectToDict(value)
                    if dictVal:
                        result[attr] = dictVal

        except Exception as e:
            exceptions.append(attr)

    if exceptions:
        result["EXCEPTIONS"] = exceptions
    if methods:
        result["METHODS"] = methods

    return result


def pprintObject(obj: any, indent: int = 4, maxPaketLength: int = 2048) -> None:
    if not isinstance(obj, dict):
        obj = objectToDict(obj)
    jsonString = json.dumps(obj, indent=indent) if indent else json.dumps(obj)
    packets = textwrap.wrap(jsonString, maxPaketLength)
    for packet in packets:
        print(packet)

