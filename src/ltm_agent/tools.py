import importlib
import importlib.util
import inspect
import logging
import sys
import uuid
from pathlib import Path
from typing import Callable, Dict, Optional

from google.adk.tools import google_search

logger = logging.getLogger(__name__)


DEFAULT_TOOLS = {
    "google_search": google_search,
}


class ToolProxy:
    """Proxy class that wraps Tool objects and adds logging."""

    def __init__(self, tool, tool_name: str):
        self._tool = tool
        self._tool_name = tool_name
        self._is_tool_object = hasattr(tool, "_get_declaration")

        if callable(tool) and not self._is_tool_object:
            if hasattr(tool, "__doc__"):
                self.__doc__ = tool.__doc__
            if hasattr(tool, "__name__"):
                self.__name__ = tool.__name__
            if hasattr(tool, "__annotations__"):
                self.__annotations__ = tool.__annotations__
            if hasattr(tool, "__module__"):
                self.__module__ = tool.__module__
            if hasattr(tool, "__qualname__"):
                self.__qualname__ = tool.__qualname__

            try:
                self.__signature__ = inspect.signature(tool)
            except (ValueError, TypeError):
                pass

    @property
    def name(self) -> str:
        """Return the name of the wrapped tool."""
        if self._is_tool_object and hasattr(self._tool, "name"):
            return self._tool.name

        return str(self._tool_name)

    @property
    def __class__(self):
        """Return the class of the wrapped tool for isinstance checks."""
        return self._tool.__class__

    def __call__(self, *args, **kwargs):
        """Make the proxy callable. For Tool objects, delegate to run method."""
        logger.info(f"Calling tool: {self._tool_name}")
        if self._is_tool_object:
            if hasattr(self._tool, "run"):
                return self._tool.run(*args, **kwargs)
            raise TypeError(f"Tool {self._tool_name} is not callable and has no run method")
        return self._tool(*args, **kwargs)

    def __getattr__(self, name):
        """Delegate all attribute access to the wrapped tool."""
        attr = getattr(self._tool, name)

        if name == "run" and callable(attr):

            def run_wrapper(*args, **kwargs):
                logger.debug(f"Calling tool: {self._tool_name}")
                return attr(*args, **kwargs)

            return run_wrapper
        elif name == "run_async" and callable(attr):

            async def run_async_wrapper(*args, **kwargs):
                logger.debug(f"Calling tool: {self._tool_name}")
                return await attr(*args, **kwargs)

            return run_async_wrapper

        return attr


class ToolRegistry:
    """Registry for managing tools with automatic proxying."""

    def __init__(self):
        self._tools: Dict[str, ToolProxy] = {}

    def register(self, name: str, tool: Callable) -> None:
        """Register a tool with logging via ToolProxy.

        Args:
            name: Name of the tool
            tool: Callable tool function or Tool object
        """
        self._tools[name] = ToolProxy(tool, name)
        logger.debug(f"Registered tool: {name}")

    def get(self, name: str) -> Optional[ToolProxy]:
        """Get a tool by name.

        Args:
            name: Name of the tool

        Returns:
            ToolProxy if found, None otherwise
        """
        return self._tools.get(name)

    def __contains__(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def __getitem__(self, name: str) -> ToolProxy:
        """Get a tool by name using subscript notation."""
        return self._tools[name]

    def load_defaults(self) -> None:
        """Load default tools into registry."""
        for tool_name, tool_func in DEFAULT_TOOLS.items():
            self.register(tool_name, tool_func)
            logger.debug(f"Loaded default tool: {tool_name}")

    def load_external_tools(self, external_tools: Dict[str, str]) -> None:
        """Load external tools from config.

        Args:
            external_tools: Dict mapping tool names to tool specs (module:function format)

        Raises:
            ValueError: If tool loading fails
        """
        for tool_name, tool_spec in external_tools.items():
            try:
                tool_func = load_external_tool(tool_spec)
                self.register(tool_name, tool_func)
                logger.debug(f"Loaded external tool: {tool_name} from {tool_spec}")
            except Exception as e:
                raise ValueError(f"Failed to load external tool '{tool_name}': {e}")


def load_external_tool(tool_spec: str) -> Callable:
    """Load external tool from module.

    Args:
        tool_spec: Tool specification in format "module.path:function.name"
                  or "file/path.py:function.name"

    Returns:
        Callable tool function

    Raises:
        ValueError: If tool spec is invalid or tool cannot be loaded
    """
    if ":" not in tool_spec:
        raise ValueError(f"Invalid tool spec '{tool_spec}'")

    module_path, func_path = tool_spec.rsplit(":", 1)

    if module_path.endswith(".py") or "/" in module_path or "\\" in module_path:
        file_path = Path(module_path)
        if not file_path.exists():
            raise ValueError(f"Tool file not found: {file_path}")

        module_name = f"external_tool_{uuid.uuid4().hex[:8]}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Could not load module from {file_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    else:
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ValueError(f"Could not import module '{module_path}': {e}")

    obj = module
    for attr in func_path.split("."):
        try:
            obj = getattr(obj, attr)
        except AttributeError:
            raise ValueError(f"Attribute '{attr}' not found in '{tool_spec}'")

    if not callable(obj):
        raise ValueError(f"Tool '{tool_spec}' is not callable")

    return obj
