import ecdsa
from ecdsa import SigningKey, NIST384p, VerifyingKey, NIST521p, NIST256p, BadSignatureError, NIST192p
import rsa
from datetime import datetime, timedelta
import prov.model as pr
import hashlib
import Utilites
from typing import Tuple, Optional, List


class CryptoUtils:
    @staticmethod
    def sort_by_id(x: pr.ProvRecord) -> str:
        if x is None or x.identifier is None:
            raise pr.Error("No identifier")
        return x.identifier.localpart

    @staticmethod
    def sort_attr(x: Tuple[pr.QualifiedName | str, pr.QualifiedName | str]) -> Tuple[str, str]:
        if isinstance(x[0], pr.QualifiedName):
            first = x[0].localpart
        else:
            first = x[0]
        if isinstance(x[1], pr.QualifiedName):
            second = x[1].localpart
        else:
            second = x[1]
        return first, second

    @staticmethod
    def bundle_to_bytes(bundle: pr.ProvBundle, encoding: str) -> bytes:
        """
        Converts bundle into unique combination of bytes according to its content with specific ordering.

        :param bundle: Bundle which will converted into bytes.
        :param encoding: Encoding used
        :return:
        """
        if bundle is None:
            return b"\x00"
        if bundle.identifier is not None:
            output = bundle.identifier.localpart + "%"
        else:
            raise pr.Error("No identifier")
        records: list[pr.ProvRecord] = sorted(list(bundle.records), key=CryptoUtils.sort_by_id)
        for record in records:
            output += record.identifier.localpart
            attributes = sorted(record.attributes, key=CryptoUtils.sort_attr)
            for attribute in attributes:
                output += "+" + attribute[0].localpart + "~"
                if isinstance(attribute[1], str):
                    output += attribute[1]
                elif isinstance(attribute[1], pr.QualifiedName):
                    output += attribute[1].localpart
                else:
                    output += str(attribute[1])
            output += "#"
        return output.encode(encoding)

    @staticmethod
    def hash_bundle(bundle: pr.ProvBundle, algorithm_name: str,
                    encoding: str = "UTF-8", to_bytes: bytes = None) -> bytes:
        if to_bytes is None:
            to_bytes = CryptoUtils.bundle_to_bytes(bundle, encoding)
        return rsa.compute_hash(to_bytes, algorithm_name)

    @staticmethod
    def get_sign_info(sign_func: str, return_bytes: bool = False) -> Tuple[str, int, ecdsa.curves.Curve]:
        """
        Extract information from string with function used for signing.

        :param sign_func: String that contains information about signing function
        :param return_bytes: If in return should figure bytes or bits
        :return: Name of signing function with number of bytes and curve if NIST is used.
        """
        index: int = 0
        sign_type: str = ""
        sign_bits_str: str = ""
        while sign_func and not sign_func[index].isnumeric():
            sign_type += sign_func[index]
            index += 1
            if index >= len(sign_func):
                raise TypeError(f"Invalid sign algorithm {sign_func}!")
        if index == 0:
            raise TypeError(f"Invalid sign algorithm {sign_func}!")
        while index < len(sign_func) and sign_func[index].isnumeric():
            sign_bits_str += sign_func[index]
            index += 1
        sign_bits = int(sign_bits_str)
        curve: ecdsa.curves = None
        if sign_type == "NIST":
            match sign_bits:
                case 384:
                    sign_bits = 768
                    curve = NIST384p
                case 521:
                    curve = NIST521p
                    sign_bits = 1056
                case 256:
                    curve = NIST256p
                    sign_bits = 512
                case 192:
                    curve = NIST192p
                    sign_bits = 384
                case _:
                    raise TypeError(f"Unsupported count of NITS bits")
        if return_bytes:
            return sign_type, sign_bits // 8, curve
        return sign_type, sign_bits, curve

    @staticmethod
    def get_hash_func(hash_func: str):
        match hash_func:
            case "SHA3-512":
                return hashlib.sha3_512
            case "SHA3-256":
                return hashlib.sha3_256
            case "SHA3-384":
                return hashlib.sha3_384
            case _:
                raise TypeError("Unknown hash type")


class SignAuthority:
    """
    Object used for cryptographic operations with data.
    """

    def __init__(self, prefix: str, sign_func: str, hash_func: str, encoding: str):
        self.sign_func: str = sign_func
        self.sign_bits: int = 0
        self.curve: Optional[ecdsa.curves.Curve] = None
        self.sign_func_type: str = ""
        self.prefix: str = prefix
        self.hash_type: str = hash_func
        self.hash_func = CryptoUtils.get_hash_func(hash_func)
        self.encoding: str = encoding
        self.private_key, self.public_key = None, None
        self.generate_new_keys(sign_func)

    def generate_new_keys(self, sign_func):
        self.sign_func = sign_func
        self.sign_func_type, self.sign_bits, self.curve = CryptoUtils.get_sign_info(sign_func)
        if self.sign_func_type == "NIST":
            self.private_key: SigningKey = SigningKey.generate(curve=self.curve, hashfunc=self.hash_func)
            self.public_key = self.private_key.verifying_key
        elif self.sign_func_type == "RSA":
            self.public_key, self.private_key = rsa.newkeys(self.sign_bits)
        else:
            raise pr.Error("Unknown sign function!")

    def sign_bytes(self, input_bytes: bytes) -> int:
        if self.sign_func_type == "RSA":
            sign_bytes: bytes = rsa.sign(input_bytes, self.private_key, self.hash_type)
        else:
            sign_bytes: bytes = self.private_key.sign(input_bytes)
        return int.from_bytes(sign_bytes, Utilites.ENDIAN)

    def get_public_key(self):
        if self.sign_func_type == "RSA":
            return self.public_key
        return int.from_bytes(self.public_key.to_string(), Utilites.ENDIAN)

    def sign_bundle(self, meta_bundle: pr.ProvBundle, bundle: pr.ProvBundle):
        """
        Sign specific bundle and store its token in meta-bundle.
        :param meta_bundle: Meta-bundle where token will be saved
        :param bundle: Bundle to be signed.
        :return: None
        """
        if bundle.identifier is None or bundle.identifier == meta_bundle.identifier:
            return
        time: str = str(datetime.utcnow())
        current_bundle: bytes = CryptoUtils.bundle_to_bytes(bundle, self.encoding)
        current_hash: bytes = CryptoUtils.hash_bundle(bundle, self.hash_type, to_bytes=current_bundle)
        try:
            return meta_bundle.entity(f"{bundle.identifier}token", (
                (f"{self.prefix}:hash_func", self.hash_type),
                (f"{self.prefix}:hash", int.from_bytes(current_hash, Utilites.ENDIAN)),
                (f"{self.prefix}:sign_func", self.sign_func),
                (f"{self.prefix}:sign", self.sign_bytes(current_bundle)),
                (f"{self.prefix}:timestamp", time),
                (f"{self.prefix}:sign_time", self.sign_bytes(time.encode(self.encoding))),
                (f"{self.prefix}:public_key", self.get_public_key()),
                (f"{self.prefix}:encoding", self.encoding),
                (f"{self.prefix}:expire_in_days", Utilites.EXPIRE_IN_DAYS)))
        except OverflowError:
            raise pr.Error("Hash is too big for sign function! Lowering number of bytes in hash function"
                           " or increasing bits of sign function will solve this problem!")


class Validator:
    """
    Class that validates bundle against its token.
    """

    def __init__(self):
        self.prefix = Utilites.PREFIX

    @staticmethod
    def extract_public_key(key, sign_func_type: str, sign_bytes: int, curve: ecdsa.curves.Curve, hash_func):
        if sign_func_type == "RSA":
            public_key = eval("rsa." + key)
        elif sign_func_type == "NIST":
            public_key = VerifyingKey.from_string(key.to_bytes(sign_bytes, Utilites.ENDIAN), curve=curve,
                                                  hashfunc=CryptoUtils.get_hash_func(hash_func))
        else:
            raise TypeError(f"Unknown sign type {sign_func_type}")
        return public_key

    def validate_record(self, bundle: pr.ProvBundle, token: pr.ProvRecord):
        # Extract information from token
        try:
            encoding: str = Utilites.get_attribute(token, f"{self.prefix}:encoding")
            hash_func: str = Utilites.get_attribute(token, f"{self.prefix}:hash_func")
            hash_bytes: int = int(hash_func.split("-", 2)[1]) // 8
            hash_value: bytes = Utilites.get_attribute(token, f"{self.prefix}:hash")\
                .to_bytes(hash_bytes, Utilites.ENDIAN)
            sign_func: str = Utilites.get_attribute(token, f"{self.prefix}:sign_func")
            sign_func_type, sign_bytes, curve = CryptoUtils.get_sign_info(sign_func, True)
            public_key = self.extract_public_key(Utilites.get_attribute(token, f"{self.prefix}:public_key"),
                                                 sign_func_type, sign_bytes, curve, hash_func)
            sign: bytes = Utilites.get_attribute(token, f"{self.prefix}:sign").to_bytes(sign_bytes, Utilites.ENDIAN)
            time: str = Utilites.get_attribute(token, f"{self.prefix}:timestamp")
            sign_time: bytes = Utilites.get_attribute(token, f"{self.prefix}:sign_time")\
                .to_bytes(sign_bytes, Utilites.ENDIAN)
            expire_in_days: int = Utilites.get_attribute(token, f"{self.prefix}:expire_in_days")
        except IndexError:
            print(f"{bundle.identifier} is not valid due to missing or invalid information within token in meta bundle")
            return False
        except (TypeError, AttributeError):
            print(f"Invalid data in token representing {bundle.identifier}")
            return False
        except (ecdsa.MalformedPointError, ecdsa.InvalidCurveError):
            print("Invalid public key")
            return False
        # Validate data
        if CryptoUtils.hash_bundle(bundle, hash_func, encoding) != hash_value:
            print(f"{bundle.identifier} is not valid due to mismatch of bundle´s hashes")
            return False
        try:
            if sign_func_type == "RSA":
                rsa.pkcs1.verify(CryptoUtils.bundle_to_bytes(bundle, encoding), sign, public_key)
                rsa.verify(time.encode(encoding), sign_time, public_key)
            else:
                public_key.verify_digest(sign, hash_value, allow_truncate=True)
                public_key.verify(sign_time, time.encode(encoding), allow_truncate=True)
        except (BadSignatureError, rsa.VerificationError):
            print(f"{bundle.identifier} is not valid due to invalid signature of bundle or time")
            return False
        if datetime.fromisoformat(time) + timedelta(days=expire_in_days) <= datetime.utcnow():
            print(f"{bundle.identifier} is not valid due to expiration of sign")
            return False
        return True

    def valid_bundle(self, meta_bundle: pr.ProvBundle, bundle: pr.ProvBundle) -> bool:
        """
        Checks whether bundle has valid token.

        :param meta_bundle: Meta-bundle where token will be searched
        :param bundle: Bundle to be validated
        :return: Result of verification
        """
        if meta_bundle is None or bundle is None:
            return False
        # Finds token for bundle
        records: List[pr.ProvRecord] = []
        for record in meta_bundle.get_records(pr.ProvDerivation):
            if Utilites.filter_attr(record, "prov:type", "Token") and \
                    Utilites.filter_attr(record, "prov:usedEntity", bundle.identifier):
                records.append(meta_bundle.get_record(Utilites.get_attribute(record, "prov:generatedEntity", False))[0])
        if len(records) > 1:
            print(f"There are more than one token for {bundle.identifier}! Therefore it is not valid")
            return False
        elif len(records) == 1:
            if self.validate_record(bundle, records[0]):
                return True
        else:
            print(f"Token of {bundle.identifier} does not occur in meta bundle! Therefore it is not valid")
        return False
