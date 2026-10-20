INSTALL_HINT = (
    "Google client libraries are not installed.\n"
    "From the gdsync directory, run:\n"
    "  python -m pip install -e ."
)


def load():
    try:
        import google.auth.transport.requests as transport
        import google.oauth2.credentials as oauth_credentials
        import google_auth_oauthlib.flow as flow_mod
        import googleapiclient.discovery as discovery
        import googleapiclient.errors as errors
        import googleapiclient.http as http
    except ImportError as exc:
        raise SystemExit(INSTALL_HINT) from exc
    return transport, oauth_credentials, flow_mod, discovery, errors, http
