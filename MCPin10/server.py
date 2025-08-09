from mcp.server.fastmcp import FastMCP
from mcp import tool

# Create server instance
mcp = FastMCP("Halo Background Provider")


@tool()
def get_background_image() -> str:
    """
    Returns the file path to the background image of Halo Reach.
    This should be used when the agent needs to overlay SVG elements onto a map.
    """
    return "data/halo-reach-map.png"


if __name__ == "__main__":
    mcp.run(transport="stdio")
