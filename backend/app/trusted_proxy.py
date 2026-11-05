"""One explicitly trusted ingress peer; disabled unless installed by dedicated setup.

Requires a future network boundary that prevents clients reaching the backend or
impersonating the peer. The proxy must replace, never append, forwarded headers.
"""

from ipaddress import ip_address

from werkzeug.wrappers import Response


class TrustedProxy:
    def __init__(self, app, *, enabled, peers, authority):
        self.app = app
        self.enabled = enabled
        self.peers = frozenset(peers)
        self.authority = authority

    def __call__(self, environ, start_response):
        forwarded = {k for k in environ if k == "HTTP_FORWARDED"
                     or k.startswith("HTTP_X_FORWARDED_")}
        if not self.enabled:
            if forwarded:
                return self._reject(environ, start_response)
            return self.app(environ, start_response)
        try:
            peer = str(ip_address(environ.get("REMOTE_ADDR", "")))
            allowed = {"HTTP_X_FORWARDED_FOR", "HTTP_X_FORWARDED_PROTO",
                       "HTTP_X_FORWARDED_HOST", "HTTP_X_FORWARDED_PORT"}
            client = str(ip_address(environ.get("HTTP_X_FORWARDED_FOR", "")))
            if (peer not in self.peers or not forwarded <= allowed
                    or environ.get("HTTP_X_FORWARDED_PROTO") != "https"
                    or environ.get("HTTP_X_FORWARDED_HOST") != self.authority
                    or environ.get("HTTP_HOST") != self.authority
                    or environ.get("HTTP_X_FORWARDED_PORT", "8443") != "8443"):
                raise ValueError()
        except ValueError:
            return self._reject(environ, start_response)
        # Copy: the socket peer is validated before the client address is replaced.
        clean = {k: v for k, v in environ.items() if k not in forwarded}
        clean.update(REMOTE_ADDR=client, **{"wsgi.url_scheme": "https"},
                     HTTP_HOST=self.authority, SERVER_NAME="livenet-v2.home.arpa",
                     SERVER_PORT="8443")
        return self.app(clean, start_response)

    @staticmethod
    def _reject(environ, start_response):
        return Response('{"error":{"code":"invalid_proxy","message":"Pedido recusado."}}',
                        status=403, content_type="application/json",
                        headers={"Cache-Control": "no-store"})(environ, start_response)
