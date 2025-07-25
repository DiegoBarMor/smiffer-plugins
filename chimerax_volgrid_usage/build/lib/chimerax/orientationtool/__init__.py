from chimerax.core.toolshed import BundleAPI

class _OrientationToolBundle(BundleAPI):

    api_version = 1

    @staticmethod
    def start_tool(session, bi, ti):
        # bi is a BundleInfo instance
        # ti is a ToolInfo instance
        from . import tool
        return tool.OrientationTool(session, ti.name)

bundle_api = _OrientationToolBundle()
