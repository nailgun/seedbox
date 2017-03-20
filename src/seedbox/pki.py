import ssl
import idna
import datetime
import operator
import ipaddress
import subprocess
from OpenSSL import crypto
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def create_ca_certificate(cn, key_size=2048, certify_days=365):
    key = rsa.generate_private_key(public_exponent=65537, key_size=key_size, backend=default_backend())
    key_id = x509.SubjectKeyIdentifier.from_public_key(key.public_key())

    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])

    now = datetime.datetime.utcnow()
    serial = x509.random_serial_number()
    cert = x509.CertificateBuilder() \
        .subject_name(subject) \
        .issuer_name(issuer) \
        .public_key(key.public_key()) \
        .serial_number(serial) \
        .not_valid_before(now) \
        .not_valid_after(now + datetime.timedelta(days=certify_days)) \
        .add_extension(key_id, critical=False) \
        .add_extension(x509.AuthorityKeyIdentifier(key_id.digest, [x509.DirectoryName(issuer)], serial), critical=False) \
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=False) \
        .sign(key, hashes.SHA256(), default_backend())

    cert = cert.public_bytes(serialization.Encoding.PEM)
    key = key.private_bytes(encoding=serialization.Encoding.PEM,
                            format=serialization.PrivateFormat.TraditionalOpenSSL,
                            encryption_algorithm=serialization.NoEncryption())
    return cert, key


def issue_certificate(cn, ca_cert, ca_key, san_dns=(), san_ips=(), key_size=2048, certify_days=365):
    ca_cert = x509.load_pem_x509_certificate(ca_cert, default_backend())
    ca_key = serialization.load_pem_private_key(ca_key, password=None, backend=default_backend())

    key = rsa.generate_private_key(public_exponent=65537, key_size=key_size, backend=default_backend())

    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])

    now = datetime.datetime.utcnow()
    cert = x509.CertificateBuilder() \
        .subject_name(subject) \
        .issuer_name(ca_cert.issuer) \
        .public_key(key.public_key()) \
        .serial_number(x509.random_serial_number()) \
        .not_valid_before(now) \
        .not_valid_after(now + datetime.timedelta(days=certify_days)) \
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=False) \
        .add_extension(x509.KeyUsage(digital_signature=True,
                                     content_commitment=True,
                                     key_encipherment=True,
                                     data_encipherment=False,
                                     key_agreement=False,
                                     key_cert_sign=False,
                                     crl_sign=False,
                                     encipher_only=False,
                                     decipher_only=False),
                       critical=False)

    # TODO: add CA info

    sans = [x509.DNSName(name) for name in san_dns]
    sans += [x509.IPAddress(ipaddress.ip_address(ip)) for ip in san_ips]
    if sans:
        cert = cert.add_extension(x509.SubjectAlternativeName(sans), critical=False)

    cert = cert.sign(ca_key, hashes.SHA256(), default_backend())

    cert = cert.public_bytes(serialization.Encoding.PEM)
    key = key.private_bytes(encoding=serialization.Encoding.PEM,
                            format=serialization.PrivateFormat.TraditionalOpenSSL,
                            encryption_algorithm=serialization.NoEncryption())
    return cert, key


def get_certificate_text(cert):
    return subprocess.run(['openssl', 'x509',
                           '-in', '/dev/stdin',
                           '-text'],
                          check=True,
                          stdout=subprocess.PIPE,
                          input=cert).stdout


def verify_certificate_chain(ca_pem_data, cert_pem_data):
    try:
        ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, ca_pem_data)
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_pem_data)

        store = crypto.X509Store()
        store.add_cert(ca_cert)

        store_ctx = crypto.X509StoreContext(store, cert)
        store_ctx.verify_certificate()
    except crypto.Error as e:
        raise InvalidCertificate('Broken certificate') from e
    except crypto.X509StoreContextError as e:
        raise InvalidCertificate('Invalid certificate chain: ' + str(e)) from e


def wrap_subject_matching_errors(func):
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except idna.core.IDNAError as e:
            raise InvalidCertificate('Invalid subject IDNA name') from e
    return wrapped


@wrap_subject_matching_errors
def validate_certificate_subject_name(cert_pem_data, subject_name):
    cert = x509.load_pem_x509_certificate(cert_pem_data, default_backend())
    _match_subject_name(cert, subject_name)


@wrap_subject_matching_errors
def validate_certificate_hosts(cert_pem_data, host_names):
    cert = x509.load_pem_x509_certificate(cert_pem_data, default_backend())
    for host_name in host_names:
        _match_subject_name(cert, host_name, compare_func=ssl._dnsname_match)


@wrap_subject_matching_errors
def validate_certificate_host_ips(cert_pem_data, host_ips):
    cert = x509.load_pem_x509_certificate(cert_pem_data, default_backend())
    for host_ip in host_ips:
        _match_subject_ip(cert, host_ip)


@wrap_subject_matching_errors
def validate_certificate_key_usage(cert_pem_data):
    cert = x509.load_pem_x509_certificate(cert_pem_data, default_backend())
    try:
        key_usage = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
        key_usage = key_usage.value
    except x509.extensions.ExtensionNotFound:
        raise InvalidCertificate("Key usage not specified")

    if not key_usage.digital_signature:
        raise InvalidCertificate("Not intented for Digital Signature")

    if not key_usage.content_commitment:
        raise InvalidCertificate("Not intented for Non Repudiation")

    if not key_usage.key_encipherment:
        raise InvalidCertificate("Not intented for Key Encipherment")


@wrap_subject_matching_errors
def validate_ca_certificate_constraints(cert_pem_data):
    cert = x509.load_pem_x509_certificate(cert_pem_data, default_backend())
    try:
        constraints = cert.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS)
        constraints = constraints.value
    except x509.extensions.ExtensionNotFound:
        return

    if not constraints.ca:
        raise InvalidCertificate("Not a CA certificate")


# based on ssl.match_hostname code
# https://github.com/python/cpython/blob/6f0eb93183519024cb360162bdd81b9faec97ba6/Lib/ssl.py#L279
def _match_subject_name(cert, subject_name, compare_func=operator.eq):
    try:
        alt_names = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        names = alt_names.value.get_values_for_type(x509.DNSName)
    except x509.extensions.ExtensionNotFound:
        names = []

    if not names:
        common_names = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if common_names:
            common_name = common_names[0]
            names = [common_name.value]

    if not any(compare_func(name, subject_name) for name in names):
        if len(names) > 1:
            raise InvalidCertificate("Subject name %r doesn't match either of %s" % (subject_name, ', '.join(map(repr, names))))
        elif len(names) == 1:
            raise InvalidCertificate("Subject name %r doesn't match %r" % (subject_name, names[0]))
        else:
            raise InvalidCertificate("No appropriate commonName or subjectAltName DNSName fields were found")


def _match_subject_ip(cert, subject_ip, compare_func=operator.eq):
    alt_names = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
    ips = alt_names.value.get_values_for_type(x509.IPAddress)

    subject_ip = ipaddress.ip_address(subject_ip)
    if not any(compare_func(ip, subject_ip) for ip in ips):
        if len(ips) > 1:
            raise InvalidCertificate("Subject ip %s doesn't match either of %s" % (subject_ip, ', '.join(map(repr, ips))))
        elif len(ips) == 1:
            raise InvalidCertificate("Subject ip %s doesn't match %s" % (subject_ip, ips[0]))
        else:
            raise InvalidCertificate("No appropriate subjectAltName IPAddress fields were found")


class InvalidCertificate(Exception):
    pass
