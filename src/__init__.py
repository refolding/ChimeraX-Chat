from chimerax.core.toolshed import BundleAPI

class _AIChatAPI(BundleAPI):
    # API version 1 passes the session, BundleInfo (bi), and ToolInfo (ti)
    api_version = 1

    @staticmethod
    def start_tool(session, bi, ti):
        # Import the tool class lazily so ChimeraX starts up faster
        from .tool import AIChatTool
        return AIChatTool(session, ti.name)

# ChimeraX looks for this exact variable name
bundle_api = _AIChatAPI()