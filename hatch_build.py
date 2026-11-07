"""Hatch build hook: a package without the compiled UI must never be built."""

from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class StaticBundleHook(BuildHookInterface):
    def initialize(self, version, build_data):
        if version == "editable":
            return
        index = Path(self.root) / "src" / "notmuch_browser" / "static" / "index.html"
        if not index.is_file():
            raise RuntimeError(
                f"{index} is missing. Run `npm ci && npm run build` before building "
                "the package (see scripts/release.sh)."
            )
