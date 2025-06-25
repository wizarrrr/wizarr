from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render

try:
    from .error import RenderError
    from .validations import allowed_dns_opt_or_raise
except ImportError:
    from error import RenderError
    from validations import allowed_dns_opt_or_raise


class Dns:
    def __init__(self, render_instance: "Render"):
        self._render_instance = render_instance
        self._dns_options: set[str] = set()
        self._dns_searches: set[str] = set()
        self._dns_nameservers: set[str] = set()

        self._auto_add_dns_opts_from_values()
        self._auto_add_dns_searches_from_values()
        self._auto_add_dns_nameservers_from_values()

    def _get_dns_opt_keys(self):
        return [self._get_key_from_opt(opt) for opt in self._dns_options]

    def _get_key_from_opt(self, opt):
        return opt.split(":")[0]

    def _auto_add_dns_opts_from_values(self):
        values = self._render_instance.values
        for dns_opt in values.get("network", {}).get("dns_opts", []):
            self.add_dns_opt(dns_opt)

    def _auto_add_dns_searches_from_values(self):
        values = self._render_instance.values
        for dns_search in values.get("network", {}).get("dns_searches", []):
            self.add_dns_search(dns_search)

    def _auto_add_dns_nameservers_from_values(self):
        values = self._render_instance.values
        for dns_nameserver in values.get("network", {}).get("dns_nameservers", []):
            self.add_dns_nameserver(dns_nameserver)

    def add_dns_search(self, dns_search):
        if dns_search in self._dns_searches:
            raise RenderError(f"DNS Search [{dns_search}] already added")
        self._dns_searches.add(dns_search)

    def add_dns_nameserver(self, dns_nameserver):
        if dns_nameserver in self._dns_nameservers:
            raise RenderError(f"DNS Nameserver [{dns_nameserver}] already added")
        self._dns_nameservers.add(dns_nameserver)

    def add_dns_opt(self, dns_opt):
        # eg attempts:3
        key = allowed_dns_opt_or_raise(self._get_key_from_opt(dns_opt))
        if key in self._get_dns_opt_keys():
            raise RenderError(f"DNS Option [{key}] already added")
        self._dns_options.add(dns_opt)

    def has_dns_opts(self):
        return len(self._dns_options) > 0

    def has_dns_searches(self):
        return len(self._dns_searches) > 0

    def has_dns_nameservers(self):
        return len(self._dns_nameservers) > 0

    def render_dns_searches(self):
        return sorted(self._dns_searches)

    def render_dns_opts(self):
        return sorted(self._dns_options)

    def render_dns_nameservers(self):
        return sorted(self._dns_nameservers)
