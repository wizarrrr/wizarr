from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render

try:
    from .error import RenderError
    from .validations import valid_device_cgroup_rule_or_raise
except ImportError:
    from error import RenderError
    from validations import valid_device_cgroup_rule_or_raise


class DeviceCGroupRule:
    def __init__(self, rule: str):
        rule = valid_device_cgroup_rule_or_raise(rule)
        parts = rule.split(" ")
        major, minor = parts[1].split(":")

        self._type = parts[0]
        self._major = major
        self._minor = minor
        self._permissions = parts[2]

    def get_key(self):
        return f"{self._type}_{self._major}_{self._minor}"

    def render(self):
        return f"{self._type} {self._major}:{self._minor} {self._permissions}"


class DeviceCGroupRules:
    def __init__(self, render_instance: "Render"):
        self._render_instance = render_instance
        self._rules: set[DeviceCGroupRule] = set()
        self._track_rule_combos: set[str] = set()

    def add_rule(self, rule: str):
        dev_group_rule = DeviceCGroupRule(rule)
        if dev_group_rule in self._rules:
            raise RenderError(f"Device Group Rule [{rule}] already added")

        rule_key = dev_group_rule.get_key()
        if rule_key in self._track_rule_combos:
            raise RenderError(f"Device Group Rule [{rule}] has already been added for this device group")

        self._rules.add(dev_group_rule)
        self._track_rule_combos.add(rule_key)

    def has_rules(self):
        return len(self._rules) > 0

    def render(self):
        return sorted([rule.render() for rule in self._rules])
