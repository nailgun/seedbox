import ssl
import sys
import idna
import operator
import tempfile
import ipaddress
import subprocess
from OpenSSL import crypto
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.backends import default_backend

encoding = sys.getdefaultencoding()

# TODO: should be different for user (no alt_names at least)
CNF_TEMPLATE = b"""
[req]
req_extensions = v3_req
distinguished_name = req_distinguished_name

[req_distinguished_name]

[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.101 = kubernetes
DNS.102 = kubernetes.default
DNS.103 = kubernetes.default.svc
DNS.104 = kubernetes.default.svc.cluster.local
"""


def gen_rsakey(length_bits=2048):
    return subprocess.run(['openssl', 'genrsa', str(length_bits)], check=True, stdout=subprocess.PIPE).stdout


def create_ca_certificate(cn, key_length_bits=2048, certify_days=365):
    key = gen_rsakey(key_length_bits)
    cert = subprocess.run(['openssl', 'req',
                           '-x509',
                           '-new',
                           '-key', '/dev/stdin',
                           '-days', str(certify_days),
                           '-subj', '/CN={}'.format(cn)],
                          check=True,
                          stdout=subprocess.PIPE,
                          input=key).stdout
    return cert, key


def create_certificate(cn, ips, fqdns, ca_cert, ca_key, key_length_bits=2048, certify_days=365):
    key = gen_rsakey(key_length_bits)

    with tempfile.NamedTemporaryFile() as csr_file:
        with tempfile.NamedTemporaryFile() as cnf_file:

            cnf = CNF_TEMPLATE
            for idx, ip in enumerate(ips, 1):
                cnf += 'IP.{}={}\n'.format(idx, ip).encode(encoding)
            for idx, fqdn in enumerate(fqdns, 1):
                cnf += 'DNS.{}={}\n'.format(idx, fqdn).encode(encoding)
            cnf_file.write(cnf)
            cnf_file.flush()

            subprocess.run(['openssl', 'req',
                            '-new',
                            '-key', '/dev/stdin',
                            '-out', csr_file.name,
                            '-subj', '/CN={}'.format(cn),
                            '-config', cnf_file.name],
                           check=True,
                           input=key)

            with tempfile.NamedTemporaryFile() as ca_cert_file:
                ca_cert_file.write(ca_cert)
                ca_cert_file.flush()

                cert = subprocess.run(['openssl', 'x509',
                                       '-req',
                                       '-in', csr_file.name,
                                       '-CA', ca_cert_file.name,
                                       '-CAkey', '/dev/stdin',
                                       '-CAcreateserial',
                                       '-days', str(certify_days),
                                       '-extensions', 'v3_req',
                                       '-extfile', cnf_file.name],
                                      check=True,
                                      stdout=subprocess.PIPE,
                                      input=ca_key).stdout

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
def validate_certificate_host(cert_pem_data, host_name, host_ip):
    cert = x509.load_pem_x509_certificate(cert_pem_data, default_backend())
    _match_subject_name(cert, host_name, compare_func=ssl._dnsname_match)
    _match_subject_ip(cert, host_ip)


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
            raise InvalidCertificate("subject name %r doesn't match either of %s" % (subject_name, ', '.join(map(repr, names))))
        elif len(names) == 1:
            raise InvalidCertificate("subject name %r doesn't match %r" % (subject_name, names[0]))
        else:
            raise InvalidCertificate("no appropriate commonName or subjectAltName DNSName fields were found")


def _match_subject_ip(cert, subject_ip, compare_func=operator.eq):
    alt_names = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
    ips = alt_names.value.get_values_for_type(x509.IPAddress)

    subject_ip = ipaddress.ip_address(subject_ip)
    if not any(compare_func(ip, subject_ip) for ip in ips):
        if len(ips) > 1:
            raise InvalidCertificate("subject ip %s doesn't match either of %s" % (subject_ip, ', '.join(map(repr, ips))))
        elif len(ips) == 1:
            raise InvalidCertificate("subject ip %s doesn't match %s" % (subject_ip, ips[0]))
        else:
            raise InvalidCertificate("no appropriate subjectAltName IPAddress fields were found")


class InvalidCertificate(Exception):
    pass
