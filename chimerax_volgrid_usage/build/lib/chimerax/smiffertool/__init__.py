from chimerax.core.toolshed import BundleAPI

class _SmifferToolBundle(BundleAPI):

    api_version = 1

    @staticmethod
    def start_tool(session, bi, ti):
        # bi is a BundleInfo instance
        # ti is a ToolInfo instance
        from . import tool
        return tool.SmifferTool(session, ti.name)

bundle_api = _SmifferToolBundle()
