import sys
import tempfile
import subprocess


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


def get_certificate_info(cert):
    return subprocess.run(['openssl', 'x509',
                           '-in', '/dev/stdin',
                           '-text'],
                          check=True,
                          stdout=subprocess.PIPE,
                          input=cert).stdout
