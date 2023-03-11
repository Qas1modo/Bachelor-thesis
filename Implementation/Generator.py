import prov.model as pr
import sys
from LinkedList import LinkedList, Node
from Crypto import SignAuthority
import Utilites
from typing import List, Tuple, Any, Iterable, Dict, Optional, Set


#  User defined types

BundleEntities = List[Tuple[int, List[str], List[int]]]
Bundles = List[BundleEntities]
Update = Tuple[Tuple[int, ...], List[int], BundleEntities]
Updates = List[Update]


class DocumentData:
    """
    Validate all input parameters, create provenance document and later fill it with content.
    """

    def __init__(self, entities_in_bundles: Iterable, updates: Iterable, file_path: str, invalidate_bundles: Iterable,
                 start_id: int):
        """Validates and initialize data required for generation of new provenance document

        :param entities_in_bundles: Bundles are an ordered iterable collection that specifies entities in bundles. Every
        item in the collection represents a single bundle. Ids of bundles are determined by their order in the
        collection on the input. First is with id Bundle1, second with id Bundle2, etc. If a bundle contains more than
        one entity, an array must be used where each item represents a single entity within the bundle.
        An entity can be a single integer that specifies an ID of an entity or a tuple where the second parameter in
        the tuple represents a bundle referenced by has_provenance from this entity (document location in format
        POSIX-path/bundle). A list must be used again when an entity has more than one has_provenance attribute.
        The third parameter represents the IDs of entities utilized to generate this entity (generator adds derivation).
        When there is only one utilized entity, the list does not have to be used. The second and third parameters can
        be omitted. However, the second parameter must be an empty list when only the third parameter should be
        specified. The generator validates input and converts it into a unified format to be able to use it.

        :param updates: Updates are an ordered iterable collection, where each item specifies information about a single
        update in a document, usually in the form of a tuple. This tuple can have 1 to 3 items. When only the first item
        is defined, an outside tuple is redundant and does not have to be used. The first item of the tuple is
        an integer, which specifies the ID of a bundle that will be updated. It can also be a tuple when the update
        should use an already created bundle and not create a new one to enable the operation merge (join) of bundles.
        The update will not occur when the target or source bundle does not yet exist. Consequently, the order of items
        and hence their generation matter. The second item in the tuple is an iterable collection containing IDs of
        entities, which the generator deletes after the update. The third item has an identical format as an item in
        entities_in_bundle collection (previous parameter). It specifies entities (with their references and
        derivations) added by the generator in an updated bundle. The third item can only be established if the second
        item in the tuple is filled. Therefore, an empty list must be used when no entity should be deleted but only
        added.

        :param file_path: This parameter specifies the path in POSIX format, where the generator will save a
        deserialized provenance document. When this parameter is None or invalid, the generator prints the result
        of deserialization on the stdout (standard output).

        :param invalidate_bundles: This parameter represents iterable collection with IDs of bundles, which the
        generator will invalidate after document generation.

        :param start_id: This states ID of the first bundle specified in parameter bundles, from which numbering
        continues.

        :raises TypeError: When invalid input is given.
        """
        # Prevents creation of multiple tokens for single bundle during merge
        self.exclude_tokens: LinkedList = LinkedList()
        # Validates and unifies bundles to be generated
        self.bundles_entities: Bundles = self.validate_bundles(entities_in_bundles)
        self.updates: Updates = self.validate_updates(updates)  # Validates and unifies updates of bundles
        if invalidate_bundles is not None:
            self.invalidate_bundles: List[int] = self.valid_collection(invalidate_bundles)
        else:
            self.invalidate_bundles: List[int] = []
        self.prefix: str = Utilites.PREFIX
        self.path: str = file_path
        self.document: pr.ProvDocument = pr.ProvDocument()  # Creates new provenance document
        self.document.add_namespace(Utilites.PREFIX, Utilites.URI)  # Creates new namespace declaration
        # Dictionary used for quick acquisition of bundles by their id with its base bundle.
        self.bundles: Dict[int, Tuple[pr.ProvBundle, Optional[pr.QualifiedName]]] = dict()
        # Data structure with ids of merged and forked bundles
        self.merges_forks: Tuple[Set[int], Set[int]] = self.get_merges_forks()
        self.sign_authority: SignAuthority = SignAuthority(Utilites.PREFIX, Utilites.SIGN_FUNC,
                                                           Utilites.HASH_FUNC, Utilites.ENCODING)
        self.creator: Creator = Creator(self, start_id)
        self.update_manager: UpdateManager = UpdateManager(self)

    def validate_bundles(self, bundles: Iterable) -> Bundles:
        """
        Checks if input is collection of valid bundles. Returns unified data of user type Bundles.

        :raises TypeError: When input is invalid

        :param bundles: bundle list to validate

        :return: list of bundles entities
        """
        valid_bundles: Bundles = []
        if not isinstance(bundles, Iterable):
            raise TypeError("Bundles parameter is not iterable!")
        for bundle_entities in bundles:
            valid_bundles.append(self.validate_bundle_entities(bundle_entities))
        return valid_bundles

    def validate_bundle_entities(self, bundle_entities: Any) -> BundleEntities:
        """
        :raises TypeError: When bundle cannot be transformed into unified type.

        :param bundle_entities: Input which should be validated.

        :return: valid specification of content in bundle (entity_ID, [has_provenance], [utilized entity])
        """
        output: BundleEntities = []
        if not isinstance(bundle_entities, list):  # When only int is specified
            bundle_entities = [bundle_entities]
        for bundle_entity in bundle_entities:
            if isinstance(bundle_entity, int):
                output.append((bundle_entity, [], []))
            elif self.valid_tuple(bundle_entity, 2, ">="):
                if isinstance(bundle_entity[1], str):
                    hp_refs = [bundle_entity[1]]
                else:
                    hp_refs = self.valid_collection(bundle_entity[1], str)
                if len(bundle_entity) == 2:
                    derivations = []
                elif len(bundle_entity) == 3:
                    if isinstance(bundle_entity[2], int):
                        derivations = [bundle_entity[2]]
                    else:
                        derivations = self.valid_collection(bundle_entity[2])
                else:
                    raise TypeError(f"Invalid number of tuple's members of {bundle_entity} in {bundle_entities}!")
                output.append((bundle_entity[0], hp_refs, derivations))
            else:
                raise TypeError(f"Invalid type of {bundle_entity} in {bundle_entities}!")
        return output

    def validate_updates(self, updates: Iterable) -> Updates:
        """
        Return unified specification of updates according to Updates type.

        :param updates: Input which should be validated.

        :raises TypeError: When input cannot be validated

        :return: valid updates
        """
        valid_updates: Updates = []
        if updates is None or not isinstance(updates, Iterable):
            raise TypeError("Updates are not iterable collection!")
        for update in updates:
            if isinstance(update, int):
                valid_updates.append(((update,), [], []))
                continue
            if not self.valid_tuple(update, 1, ">=", object) or len(update) > 3:
                raise TypeError("Update in updates has invalid format")
            if type(update[0]) is int:
                if len(update) == 2 and type(update[1]) is int:
                    self.exclude_tokens.add_node(update[1])
                    valid_updates.append(((update[0], update[1]), [], []))
                    continue
                update_from_to: Tuple[int] = (update[0],)
            elif self.valid_tuple(update[0], 2) and isinstance(update[0][1], int):
                self.exclude_tokens.add_node(update[0][1])
                update_from_to: Tuple[int] = update[0]
            else:
                raise TypeError("Updates has update with invalid first attribute")
            if len(update) == 1:
                valid_updates.append((update_from_to, [], []))
                continue
            deletion_list: List[int] = self.valid_collection(update[1])
            if len(update) == 2:
                valid_updates.append((update_from_to, deletion_list, []))
                continue
            entities: BundleEntities = self.validate_bundle_entities(update[2])
            valid_updates.append((update_from_to, deletion_list, entities))
        return valid_updates

    @staticmethod
    def valid_tuple(tup: Tuple[list[int], Any], count: int, compare: str = "==", first_elem_type: Any = int) -> bool:
        """
        Check if input is valid tuple, its length and type of first item.

        :param tup: input to be verified.
        :param count: Length of tuple
        :param compare: Comparison symbol used during validation of length.
        :param first_elem_type: Type of first element in tuple. If tuple has length zero. This parameter is ignored.

        :return: True if tuple meets all requirements. False otherwise.
        """
        if isinstance(tup, tuple):
            if compare == "==" and len(tup) == count or \
                    compare == ">" and len(tup) > count or \
                    compare == "<" and len(tup) < count or \
                    compare == "<=" and len(tup) <= count or \
                    compare == ">=" and len(tup) >= count:
                if len(tup) == 0:
                    return True
                return isinstance(tup[0], first_elem_type)
        return False

    @staticmethod
    def valid_collection(collection: Iterable[Any], elem_type: Any = int) -> List[int]:
        """
        Checks if input is iterable collection containing only specifeied type.

        :raises TypeError: When input is not required type

        :param collection: Input to be verified
        :param elem_type: Type of element in iterable collection
        :return: List with content of iterable on input
        """
        output: List[elem_type] = []
        if not isinstance(collection, Iterable):
            raise TypeError("Iterable collection is not used!")
        for elem in collection:
            if not isinstance(elem, elem_type):
                raise TypeError(f"Collection contains different type than {elem_type}")
            output.append(elem)
        return output

    def get_merges_forks(self) -> Tuple[Set[int], Set[int]]:
        """
        Extract bundles that are result of merge or old bundle in fork.

        :return: Tuple where first item are bundles created by merge and second bundles that are forked
        """
        result: Tuple[Set[int], Set[int]] = (set(), set())
        already_seen = []
        for merge_entity in self.exclude_tokens:
            result[0].add(merge_entity.value)
        for entity in self.updates:
            update_from = entity[0][0]
            if update_from in already_seen:
                result[1].add(update_from)
            else:
                already_seen.append(update_from)
        return result


class Creator:
    """
    Object used for creating (adding) records into provenance document.
    """

    def __init__(self, data: DocumentData, start_id: int):
        self.data: DocumentData = data
        self.bundle_ID: int = start_id - 1

    def entity(self, bundle: pr.ProvBundle, entity_id: int, to_hp_list: List[str]):
        """
        Create new entity within bundle

        :param bundle: Bundle where entity will be added
        :param entity_id: ID of the new entity
        :param to_hp_list: Has provenance references of this entity.
        :return: New entity
        """
        tuple_list: List[Tuple[str, str]] = []
        for to_hp in to_hp_list:
            path = to_hp.split("/")
            path.append(f"bundle{path.pop()}")
            tuple_list.append((f"prov:has_provenance", "/".join(path)))
        return bundle.entity(f"{self.data.prefix}:{entity_id}", tuple(tuple_list))

    def bundle(self, specialization: pr.QualifiedName = None, create_new_spec: bool = False) -> pr.ProvBundle:
        """
        Creates new bundle with incremented ID

        :param specialization: Bundle which will be used in specialization or will be utilized by new base bundle.
        :param create_new_spec: If new base bundle should be created.
        :return: New bundle
        """
        self.bundle_ID += 1
        bundle: pr.ProvBundle = self.data.document.bundle(f"{self.data.prefix}:bundle{self.bundle_ID}")
        meta = self.meta_bundle()
        # Creates representation in meta-bundle of the new bundle together with specialization bundles.
        new_entity = meta.entity(f"{self.data.prefix}:bundle{self.bundle_ID}")
        if specialization is None or create_new_spec or self.bundle_ID in self.data.merges_forks[0]:
            new_specialization: pr.QualifiedName = meta.entity(f"{self.data.prefix}:base{self.bundle_ID}")
            if specialization is not None:
                meta.wasDerivedFrom(new_specialization, specialization)
        else:
            new_specialization: pr.QualifiedName = specialization
        meta.specializationOf(new_entity, new_specialization)
        self.data.bundles[self.bundle_ID] = bundle, new_specialization
        return bundle

    def meta_bundle(self) -> Optional[pr.ProvBundle]:
        """
        Creates or finds meta-bundle within document

        :return: Meta-bundle
        """
        meta_spec: Tuple[pr.ProvBundle, pr.QualifiedName] = self.data.bundles.get(-1)  # meta_bundle has identifier -1
        if self.data.document is None or meta_spec is not None:
            return meta_spec[0]
        self.data.bundles[-1] = self.data.document.bundle(f"{self.data.prefix}:meta"), None
        return self.data.bundles[-1][0]

    def bundle_with_entities(self, entities: BundleEntities, bundle: pr.ProvBundle = None) -> pr.ProvBundle:
        """
        :param entities: Entities that will be added in the bundle
        :param bundle: Bundle in which will be added new entities. When none new is created.
        :return: Bundle with entities
        """
        if bundle is None:
            bundle = self.bundle()  # Creates new bundle with base bundle
        namespace = Utilites.get_namespaces(bundle.document)[0]
        for entity in entities:
            new_entity = self.entity(bundle, entity[0], entity[1]).identifier
            for derivation in entity[2]:  # Add derivation relation into bundle
                used_entity = pr.QualifiedName(namespace, f"{derivation}")
                bundle.derivation(new_entity, used_entity,
                                  identifier=pr.QualifiedName(namespace, f"der{new_entity.localpart}-"
                                                                         f"{used_entity.localpart}"))
        try:
            bundle_id: int = int(bundle.identifier.localpart[6:])  # Gets bundle numerical ID
        except ValueError:
            raise TypeError("Invalid bundle id!")
        exclusion: Node
        # Check if all bundles that merge into this bundle were examined to prevent creating token multiple times.
        for exclusion in self.data.exclude_tokens:
            if exclusion.value == bundle_id:
                self.data.exclude_tokens.remove(exclusion)
                break
        else:
            #  Create token for bundle
            meta = self.meta_bundle()
            token = self.data.sign_authority.sign_bundle(meta, bundle)
            meta.wasDerivedFrom(token.identifier, bundle.identifier,
                                other_attributes=[("prov:type", pr.QualifiedName(namespace, "Token"))])
        return bundle


class UpdateManager:
    """
    Object responsible for creating updates in document.
    """

    def __init__(self, data: DocumentData):
        self.data: DocumentData = data

    def create_updates(self):
        """
        Creates new bundle with updated content

        :raises pr.Error: If bundle to updated was not found
        :return: None
        """
        meta_bundle: pr.ProvBundle = self.data.creator.meta_bundle()
        for update in self.data.updates:
            bundle, specialization = self.data.bundles.get(update[0][0], (None, None))
            if bundle is None or specialization is None:
                raise(pr.Error(f"Bundle with {update[0][0]} could not have been found during update"))
            if len(update[0]) == 1:
                new_bundle = self.data.creator.bundle(specialization, update[0][0] in self.data.merges_forks[1])
                new_bundle_id = new_bundle.identifier.localpart
            else:
                new_bundle_id: int = update[0][1]
                new_bundle, new_specialization = self.data.bundles.get(new_bundle_id, (None, None))
                meta_bundle.wasDerivedFrom(new_specialization, specialization)
            if bundle is None or new_bundle is None:
                continue
            #  Inserting update confirmation in newer version
            new_bundle.add_record(meta_bundle.wasRevisionOf(new_bundle.identifier, bundle.identifier,
                                                            identifier=f"{self.data.prefix}:up#bundle"
                                                                       f"{update[0][0]}-{new_bundle_id}"))
            self.update_bundle(bundle, new_bundle, update)

    def update_bundle(self, bundle: pr.ProvBundle, new_bundle: pr.ProvBundle, update: Update):
        """
        Adds records from older version into updated bundle

        :param bundle: Older version of bundle
        :param new_bundle: Newer bundle without content
        :param update: Modification of older bundle specified on the generator output
        :return: None
        """
        record: pr.ProvRecord
        for record in bundle.records:
            if record.identifier is None or Utilites.filter_attr(record, "prov:type", "Revision"):
                continue
            for deletion in update[1]:
                if isinstance(record, pr.ProvDerivation):
                    if Utilites.filter_attr(record, "prov:generatedEntity", str(deletion)):
                        break
                if record.identifier.localpart == str(deletion):
                    break
            else:
                new_bundle.add_record(record)
        self.data.creator.bundle_with_entities(update[2], new_bundle)


class DocumentGenerator:
    """
    Object responsible for creating provenance document and its serialization.
    """

    def __init__(self, bundles: Iterable, updates: Iterable, file_path: str = None, invalidate_bundles: Iterable = None,
                 start_id: int = 1):
        # Initialize and unify data on the input.
        self.data: DocumentData = DocumentData(bundles, updates, file_path, invalidate_bundles, start_id)
        self.create_document()

    def create_document(self):
        """
        Create document from data passed on the input.

        :return: None
        """
        self.create_document_without_updates()  # Creates base bundles
        self.data.update_manager.create_updates()  # Create updates
        self.invalidate_bundle_token(self.data.invalidate_bundles)  # Invalidate tokens of bundles
        output = self.data.document.serialize(format=Utilites.DOC_FORMAT)
        file = Utilites.open_file(self.data.path)
        if file is None:
            if self.data.path is not None:
                print(f"Output path {self.data.path} is invalid and the serialization"
                      f" is printed on the standard output:\n")
            file = sys.stdout
        file.write(output)

    def create_document_without_updates(self):
        """
        Create first version of bundles without any updates.

        :return: None
        """
        for bundle_entities in self.data.bundles_entities:
            self.data.creator.bundle_with_entities(bundle_entities)

    def invalidate_bundle_token(self, identifiers: List[int]):
        """
        Invalidate tokens of specific bundles.

        :raises ValueError: When any bundle with id on the input does not exist.

        :param identifiers: IDs of bundles to invalidate
        :return: None
        """
        for identifier in identifiers:
            bundle, _ = self.data.bundles.get(identifier, (None, None))
            if bundle is not None:
                self.data.creator.entity(bundle, -1, [])
            else:
                raise ValueError(f"Bundle to invalidate with identifier bundle{identifier} cannot be found!")
