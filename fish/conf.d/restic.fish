if test -f /etc/pki/tls/certs/ca-bundle.crt
    set -gx RESTIC_CACERT /etc/pki/tls/certs/ca-bundle.crt
end
