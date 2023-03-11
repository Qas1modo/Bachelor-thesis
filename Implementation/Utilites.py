from pathlib import Path

import prov.model as pr
from typing import Optional, Literal, List, Dict, Iterable

# Global variables
ENDIAN: Literal["little", "big"] = "big"
DOC_FORMAT: Literal["xml", "json", "provn"] = "xml"
HASH_FUNC: Literal["SHA3-512", "SHA3-384", "SHA3-256"] = "SHA3-512"
SIGN_FUNC: Literal["NIST521", "NIST384", "NIST256", "NIST192", "RSA512", "RSA1024", "RSA1536", "RSA2048"] = "NIST256"
ENCODING: str = "UTF-8"
PREFIX: str = "ex"
URI: str = "Some_url/"
EXPIRE_IN_DAYS = 1


def get_attribute(record: pr.ProvRecord, name: str, throw_exception: bool = True, index: int = 0):
    """
    Get attribute value with specific index by its name within a record

    :param record: Record to be searched
    :param name: Name of attribute.
    :param throw_exception: Throw exception when attribute is not present within record
    :param index: Index of returned attribute
    :return: Value stored within attribute
    """
    record_type = list(record.get_attribute(name))
    if index >= len(record_type):
        if throw_exception:
            raise IndexError
        return None
    result = record_type[index]
    return result


def filter_attr(record: pr.ProvRecord, attribute_name: str, attribute_value: pr.QualifiedName | str):
    """
    Check if a record has attribute with specific type and check whether it has   of record has specific

    :param record: Record in which attribute is stored
    :param attribute_name: Name of attribute
    :param attribute_value: Value of attribute
    :return: True if record has attribute with specified name and value
    """
    attr = get_attribute(record, attribute_name, False)
    if attr is None:
        return False
    if isinstance(attribute_value, str):
        if isinstance(attr, str):
            return attribute_value == attr
        if isinstance(attr, pr.QualifiedName):
            return attribute_value == attr.localpart
    if isinstance(attr, str):
        return attribute_name == attribute_value.localpart
    return attribute_value == attr


def open_file(path: str, mode: str = "w"):
    """
    Open file on specific POSIX path
    :param path: POSIX path
    :param mode: Open mode, default write
    :return: Opened file or None when error occurred
    """
    home = get_path(path)
    if not isinstance(home, Path):
        return None
    try:
        home.parent.mkdir(0o777, True, True)
        output = open(home, mode)
    except (OSError, FileNotFoundError):
        return None
    return output


def get_path(path: str) -> Optional[Path]:
    """
    Transform path into Path object
    :param path: POSIX path
    :return: Path or None when input is invalid
    """
    if path is None or len(path) == 0:
        return None
    path_list = path.split("/", 1)
    expand_symbol: str = path_list[0]
    if expand_symbol == "~":
        return Path.home().joinpath(path_list[1])
    if expand_symbol == "@":
        return Path.cwd().joinpath("Cases").joinpath(path_list[1])
    return Path(path)


def get_prefix(document: pr.ProvDocument) -> str:
    """
    Get prefix of first namespace.

    :param document: Document with prefix
    :return: First prefix of document on the input
    """
    return get_namespaces(document)[0].prefix


def get_namespaces(document: pr.ProvDocument) -> List[pr.Namespace]:
    """
    Get namespaces of particular document
    :param document: Document from which namespaces will be extracted
    :return: Namespaces of the document
    """
    if document is None:
        raise pr.Error("Document not defined!")
    namespaces: List[pr.Namespace] = list(document.namespaces)
    if len(namespaces) == 0:
        raise pr.Error("No namespace defined!")
    return namespaces


def create_dict(document: pr.ProvDocument) -> Dict[pr.QualifiedName, pr.ProvBundle]:
    """
    Create dictionary mapping identifiers to the bundles.

    :param document: Document with bundles
    :return: Dictionary mapping identifiers to bundles
    """
    output = dict()
    for bundle in document.bundles:
        output[bundle.identifier] = bundle
    return output


def get_entity(entity_id: str, bundle: pr.ProvBundle) -> Optional[pr.ProvEntity]:
    """
    Get entity from bundle by specific id.

    :param entity_id: ID of a desired entity
    :param bundle: Bundle where entity is located
    :return: Record representing the entity or None when it could not be found
    """
    if bundle is None:
        return
    for record in bundle.records:
        if record.identifier is not None and record.identifier.localpart == entity_id:
            return record


def get_entities(entities: Iterable[pr.QualifiedName], bundle: pr.ProvBundle) -> List[pr.ProvEntity]:
    """
    Get list of entities specified by entities on the input.

    :param entities: Iterable collection with IDs of a desired entities
    :param bundle: Bundle where entities are located
    :return: List of entities.
    """
    output = []
    record: pr.ProvRecord
    for record in bundle.records:
        if isinstance(record, pr.ProvEntity) and record.identifier in entities:
            output.append(record)
    return output
