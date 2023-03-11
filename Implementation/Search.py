import json
import lxml.etree
import Utilites
import prov.model as pr
import prov.serializers.provxml as sr_xml
import prov.serializers.provn as sr_provn
import prov.serializers.provjson as sr_json
from Crypto import Validator
from collections import deque
from typing import Dict, Tuple, List, Optional, Set


# User types
Updates = Dict[pr.QualifiedName, Tuple[List[pr.QualifiedName], List[pr.QualifiedName]]]
Result = Tuple[str, pr.QualifiedName, pr.QualifiedName]
Results = List[Result]
Output = Tuple[Results, Results, Results]
SearchedBundle = Tuple[Optional[bool], Optional[bool]]
SearchedBundles = Dict[Result, SearchedBundle]


class Document:
    """
    Data of single document.
    """
    def __init__(self, document: pr.ProvDocument, path: str):
        self.doc: pr.ProvDocument = document
        self.prefix: str = Utilites.get_prefix(self.doc)
        self.validator: Validator = Validator()
        self.bundles: Dict[pr.QualifiedName, pr.ProvBundle] = Utilites.create_dict(self.doc)
        self.namespace: pr.Namespace = Utilites.get_namespaces(self.doc)[0]
        self.path: str = path
        self.meta: pr.ProvBundle = self.bundles[pr.QualifiedName(self.namespace, "meta")]
        self.updates: Updates = self.prepare_updates()
        self.test_document()

    def check_update_validity(self, update_from: pr.QualifiedName, update_to: pr.QualifiedName) -> bool:
        """
        Checks whether newer version contain confirmation of update by revision.

        :return: Result of verification in newer version
        """
        bundle = self.bundles[update_to]
        for record in list(filter(lambda x: Utilites.filter_attr(x, "prov:type", "Revision"),
                                  bundle.get_records())):
            if record.formal_attributes[1][1] == update_from and record.formal_attributes[0][1] == update_to:
                return True
        print(f"Update from bundle {update_from} into bundle {update_to} does not have confirmation in {update_to}")
        return False

    def prepare_updates(self) -> Updates:
        """
        Initialize data structure containing newer and older version for concrete bundle.

        :return: Dictionary describing newer and older versions.
        """
        updates: Updates = dict()
        records: List[pr.ProvRecord] = list(filter(lambda x: Utilites.filter_attr(x, "prov:type", "Revision"),
                                                   self.meta.get_records()))
        for record in records:
            update_from: pr.QualifiedName = record.formal_attributes[1][1]
            update_to: pr.QualifiedName = record.formal_attributes[0][1]
            update_to_list = updates.get(update_from)
            update_from_list = updates.get(update_to)
            if not self.check_update_validity(update_from, update_to):
                continue
            if update_to_list is None:
                updates[update_from] = ([], [update_to])
            else:
                update_to_list[1].append(update_to)
            if update_from_list is None:
                updates[update_to] = ([update_from], [])
            else:
                updates[update_to][0].append(update_from)
        return updates

    def test_document(self):
        """
        Check whether document has only acyclic updates.

        :raises pr.Error: When cycle is found
        :return: None
        """
        searched: Dict[pr.QualifiedName, bool] = dict()
        for bundle_id, updates in self.updates.items():
            if bundle_id not in searched:
                self.check_acyclic(bundle_id, updates[1], searched)

    def check_acyclic(self, bundle_id: pr.QualifiedName, updates: List[pr.QualifiedName],
                      searched: Dict[pr.QualifiedName, bool]):
        """
        By BFS checks that updates of bundle are acyclic.
        :param bundle_id: Bundle to be examined
        :param updates: Data structure containing information about older and newer versions of specific bundle
        :param searched: Data structure with information about state of certain bundle (Examined, in process, not found)
        :return: None
        """
        if bundle_id not in searched:
            searched[bundle_id] = False
        elif not searched[bundle_id]:
            raise pr.Error("Cycle detected!")
        else:
            return
        for update in updates:
            self.check_acyclic(update, self.updates[update][1], searched)
        searched[bundle_id] = True


# User type after initialization of document
Bundle = Tuple[Document, pr.ProvBundle, pr.QualifiedName]


class SearchData:
    """
    Object that encapsulates data needed during the search and handles search logic.
    """

    def __init__(self, document: pr.ProvDocument, entity_id: str, strict: bool, initial_path: str):
        """
        Initialize data required for searching.

        :param document: Provenance document, which will be processed
        :param entity_id: ID of entity for which the algorithm finds related provenance
        :param strict: Mode of the search.
        :param initial_path: Path of initial document
        """
        self.documents: Dict[str, Document] = dict()
        self.documents[initial_path] = Document(document, initial_path)  # Found documents with data
        self.searched_entity: str = entity_id
        self.strict: bool = strict
        # Data structures used during the search to capture information
        self.valid_bundles, self.invalid_bundles, self.postpone_updates = deque(), deque(), deque()
        self.searched_bundles: SearchedBundles = dict()  # Already searched bundles (found, contains entity)
        self.bundles_validity = dict()  # Remember validity of specific bundle
        self.output_valid, self.output_invalid, self.output_low = [], [], []  # Output of the algorithm
        self.prepare_search(initial_path)  # Find initial bundles and prepare search

    def get_validity(self, document, bundle) -> bool:
        """
        Check if certain bundle is valid

        :param document: Document where bundle is stored
        :param bundle: Bundle to check validity
        :return: Result of verification or lookup
        """
        valid = self.bundles_validity.get((document.path, bundle.identifier))
        if valid is not None:
            return valid
        valid = document.validator.valid_bundle(document.meta, bundle)
        self.bundles_validity[(document.path, bundle.identifier)] = valid
        return valid

    def prepare_search(self, initial_path: str):
        """
        Finds initial bundles and add them into corresponding category.

        :param initial_path: Path of initial document
        :return: None
        """
        initial_document = self.documents.get(initial_path)
        for bundle in initial_document.bundles.values():
            if not initial_document.updates.get(bundle.identifier, ([], []))[0]\
                    and bundle.identifier not in self.searched_bundles and bundle != initial_document.meta:
                entity = Utilites.get_entity(self.searched_entity, bundle)
                if entity is not None:
                    self.entity_check(initial_document, bundle, entity.identifier, True, initial_document=True)

    def entity_check(self, document: Document, bundle: pr.ProvBundle, searched_entity: pr.QualifiedName,
                     still_valid: bool, postpone: bool = False, previous_bundle: pr.ProvBundle = None,
                     initial_document: bool = False) -> bool:
        """
        Find the newest version (versions if fork occurred) of (valid if strict attribute is true) bundles
        with searched entity in update branch by BFS.

        :param document: Document where the algorithm currently looks
        :param bundle: Current bundle that is examined
        :param searched_entity: ID of entity which the algorithm currently seeks
        :param still_valid: All previous bundles in path were valid, otherwise False
        :param postpone: Older version traversed through invalid bundle
        :param previous_bundle: Bundle previously examined in previous bundle in recursion tree
        :param initial_document: If the algorithm currently seeks for initial bundles
        :return:
        """
        current_bundle = self.searched_bundles.get((document.path, bundle.identifier, searched_entity))
        if current_bundle is not None and current_bundle[0]:  # Checks if bundle has been already found
            return current_bundle[1]
        found: bool = False  # Checks if any newer version contains entity
        next_ids: List[pr.QualifiedName] = document.updates.get(bundle.identifier, ([], []))[1]  # Newer versions
        current_valid = self.get_validity(document, bundle)
        for next_id in next_ids:
            next_bundle: pr.ProvBundle = document.bundles[next_id]
            next_contains: SearchedBundle = self.searched_bundles.get((document.path, next_id, searched_entity))
            if next_contains is not None:
                if next_contains[1]:
                    found = True  # newer bundle has been found and contains entity
                if next_contains[0]:
                    continue  # newer bundle examined all its newer versions
            if not current_valid and previous_bundle is not None and not initial_document:
                postpone = True  # the algorithm traverses through invalid update
            # Check newer version
            found = self.entity_check(document, next_bundle, searched_entity, still_valid, postpone, bundle,
                                      initial_document) or found
        result = True
        if not found:  # Newer bundle does not contain entity (tries to use this one)
            if Utilites.get_entity(searched_entity.localpart, bundle) is None:  # Contains entity
                self.searched_bundles[(document.path, bundle.identifier, searched_entity)] = True, False
                return False
            if current_valid:
                result = self.add_valid_output(document, bundle, searched_entity, still_valid, postpone)
            else:
                result = self.add_invalid_output(document, bundle, searched_entity)
            if result and not postpone:  # Check if there is newer version to show warning
                self.check_successors(next_ids, bundle.identifier, searched_entity)
        return result

    def add_valid_output(self, document: Document, bundle: pr.ProvBundle, searched_entity: pr.QualifiedName,
                         still_valid: bool, postpone: bool = False):
        """
        :return: If bundle has been successfully added into valid bundles
        """
        if still_valid:
            if postpone:
                # Wait until all valid bundles found their references
                # and then continue to follow references of this bundle
                self.postpone_updates.append((document, bundle, searched_entity))
                return True
            self.valid_bundles.append((document, bundle, searched_entity))
            self.output_valid.append((document.path, bundle.identifier, searched_entity))
        else:
            # Bundle is after invalid bundle in path from initial bundle
            self.invalid_bundles.append((document, bundle, searched_entity))
            self.output_low.append((document.path, bundle.identifier, searched_entity))
        if not self.check_prev_validity(document, bundle.identifier, searched_entity, True):
            print(f"Origin of starting bundle {bundle.identifier} is not trustworthy!")
        return True

    def add_invalid_output(self, document: Document, bundle: pr.ProvBundle, searched_entity: pr.QualifiedName):
        """
        :return: If bundle has been successfully added into invalid bundles. Strict return always false.
        """
        if self.strict:
            self.searched_bundles[bundle.identifier] = True, False
            return False
        self.invalid_bundles.append((document, bundle, searched_entity))
        self.output_invalid.append((document.path, bundle.identifier, searched_entity))
        self.check_prev_validity(document, bundle.identifier, searched_entity, False)
        return True

    def check_successors(self, next_ids: List[pr.QualifiedName], bundle_id: pr.QualifiedName,
                         searched_entity: pr.QualifiedName):
        """
        Check if bundle has newer version that could not have been added into the output

        :param next_ids: Newer versions of bundle
        :param bundle_id: Bundle that is checked
        :param searched_entity: Currently searched entity
        :return: None
        """
        if len(next_ids) != 0:
            if self.strict:
                print(f"Newer versions of {bundle_id} are invalid"
                      f" or does not contain searched entity {searched_entity}")
            else:
                print(f"Newer versions of {bundle_id} "
                      f"does not contain searched entity {searched_entity}")

    def check_prev_validity(self, document: Document, bundle: pr.QualifiedName, entity: pr.QualifiedName,
                            still_valid: bool, mark_searched: bool = True) -> bool:
        """
        Mark older versions of specific bundle and entity as searched if they do not have unexamined newer version.
         And checks if bundle have invalid predecessor.

        :param document: Document where the algorithm currently is
        :param bundle: Currently processed bundle within recursion
        :param entity: Entity found in newer version
        :param still_valid: Flag that signals the algorithm has not found invalid version yet
        :param mark_searched: Flag that signals the bundle has all newer versions examined and therefore can be
         added into searched bundles.
        :return:
        """
        if not still_valid and not mark_searched:
            return False  # There is no point for further traversing
        older_bundles, newer_bundles = document.updates.get(bundle, ([], []))
        if mark_searched:
            for new_bundle in newer_bundles:
                searched = self.searched_bundles.get((document.path, new_bundle, entity))
                if searched is None or not searched[0]:
                    mark_searched = False
                    self.searched_bundles[(document.path, bundle, entity)] = False, True
                    break
            else:
                self.searched_bundles[(document.path, bundle, entity)] = True, True
        else:
            self.searched_bundles[(document.path, bundle, entity)] = False, True
        for prev in older_bundles:
            prev_bundle: pr.ProvBundle = document.bundles.get(prev)
            if not self.check_prev_validity(document, prev, entity, still_valid, mark_searched) or \
                    not self.get_validity(document, prev_bundle):
                still_valid = False
        return still_valid


class Search:
    """
    Class passing bundles into search logic and traverse by has_provenance.
    """
    def __init__(self, path: str, entity_id: str, strict: bool):
        initial_document: pr.ProvDocument = DocumentDeserializer.deserialize(path)
        if initial_document is None:
            raise pr.Error("Some error occurred and initial document could not have been deserialized")
        self.data = SearchData(initial_document, entity_id, strict, path)
        self.result_valid, self.result_invalid, self.result_low = self.search()

    def search(self) -> Output:
        """
        Initializer of the traversing from initial bundles
        :return: Related entities with bundles and documents that contain object's provenance represented
        by searched ID on the input.
        """
        # Searching bundles found by traversing only by hp references in valid bundles from the initial bundle
        while self.data.valid_bundles:
            to_search: Bundle = self.data.valid_bundles.pop()
            self.search_traverse(to_search, True)
        # Searching bundles found by traversing through invalid version of the bundle and hence are postponed until now
        for postpone in self.data.postpone_updates:
            document, bundle, searched_entity = postpone
            output = (document.path, bundle.identifier, searched_entity)
            status = self.data.searched_bundles.get(output)
            if status is None:  # Check whether bundle has not been found during postpone interval
                next_ids = document.updates.get(bundle.identifier, ([], []))[1]
                # Add bundle into the low credibility output
                self.data.add_valid_output(document, bundle, searched_entity, False)
                # mark predecessors as searched
                self.data.check_successors(next_ids, bundle.identifier, searched_entity)
        # Traversing invalid bundles or bundles referenced after invalid bundle from initial bundle
        while self.data.invalid_bundles:
            to_search: Bundle = self.data.invalid_bundles.pop()
            self.search_traverse(to_search, False)
        return self.data.output_valid, self.data.output_invalid, self.data.output_low

    def search_traverse(self, bundle_entity: Bundle, still_valid: bool):
        """
        Finds has_provenance references of the entity and all entities used in its generation that are later used
         for further traversing.

        :param bundle_entity: Document and Bundle with entity that will be processed
        :param still_valid: Flag denoting whether bundle with this entity is referenced after invalid bundle.
        :return: None
        """
        document, bundle, entity = bundle_entity
        related_entities: Set[pr.QualifiedName] = set()  # Structure containing derived entities from entity on input
        record: pr.ProvRecord
        for record in bundle.get_records(pr.ProvDerivation):
            if Utilites.get_attribute(record, "prov:generatedEntity", False) == entity:
                related_entities.add(Utilites.get_attribute(record, "prov:usedEntity", False))
        for related_entity in related_entities:
            # Checking for newer versions with this entity and then lookup for derived entities and traverse further
            self.data.entity_check(document, bundle, related_entity, still_valid)
        next_bundles: List[str] = []
        # Find has_provenance references of all occurrences of the entity.
        for identical_entity in Utilites.get_entities([entity], bundle):
            next_bundles.extend(identical_entity.get_attribute(f"prov:has_provenance"))
        # Traverse to bundles referenced by has_provenance
        for next_bundle_path in next_bundles:
            path = next_bundle_path.split("/")
            next_bundle_id = path.pop(-1)
            path = "/".join(path)
            next_document = DocumentDeserializer.document(path, self.data)
            if next_document is None:
                print(f"Unable to open file reference {path} with bundle {next_bundle_id}")
                continue
            next_bundle = next_document.bundles.get(pr.QualifiedName(next_document.namespace, next_bundle_id))
            if next_bundle is None:
                print(f"Unable to find bundle with id {next_bundle_id} in {path}")
                continue
            if not self.data.entity_check(next_document, next_bundle, entity, still_valid):
                if self.data.strict:
                    print(f"Reference into {next_bundle_path} in {bundle.identifier} does not contain {entity}"
                          f" or valid bundle")
                else:
                    print(f"Reference into {next_bundle_path} in {bundle.identifier} does not contain {entity}")


class DocumentDeserializer:

    @staticmethod
    def document(path: str, data: SearchData) -> Optional[Document]:
        """
        Acquire document by path.
        :param path: Path of desired document.
        :param data: Data with already deserialized documents
        :return: Document or None, where it could not have been deserialized or found.
        """
        document = data.documents.get(path)  # Try to find document in already deserialized documents
        if document is not None:
            return document
        document = DocumentDeserializer.deserialize(path)
        if document is None:
            return None
        try:
            return Document(document, path)
        except pr.Error:
            print(f"Document at {path} contains cycle of updates!")
            return None

    @staticmethod
    def deserialize(path: str) -> Optional[pr.ProvDocument]:
        """
        Deserialize document from path.
        :param path: POSIX path where document is located.
        :return: Deserialize provenance document if no error has occurred.
        """
        file = Utilites.open_file(path, "r")
        if file is None:
            return None
        if Utilites.DOC_FORMAT == "xml":
            serializer: pr.serializers = sr_xml.ProvXMLSerializer()
        elif Utilites.DOC_FORMAT == "json":
            serializer: pr.serializers = sr_json.ProvJSONSerializer()
        elif Utilites.DOC_FORMAT == "provn":
            serializer: pr.serializers = sr_provn.ProvNSerializer()
        else:
            raise pr.Error("Unknown type of documents")
        try:
            return serializer.deserialize(file)
        except pr.Error:
            return None
        except (lxml.etree.ParseError, lxml.etree.Error, sr_xml.ProvXMLException, sr_json.ProvJSONException,
                json.JSONDecodeError):
            print("Parse Error, File is not valid!")
            return None
        except NotImplementedError:
            print("PROVN notation does not have currently implemented deserialization of format PROVN, "
                  "only serialization which is the most readable!")
            return None
