class ComfyUIError(RuntimeError):
    """Base class for user-facing ComfyUI integration failures."""


class ComfyUIConnectionError(ComfyUIError):
    """The configured ComfyUI server could not be reached."""


class ComfyUIResponseError(ComfyUIError):
    """ComfyUI returned an invalid HTTP or JSON response."""


class WorkflowFormatError(ComfyUIError):
    """A workflow file is not valid ComfyUI API prompt JSON."""


class WorkflowBindingError(ComfyUIError):
    """A binding profile references a missing workflow node or input."""


class RenderTimeoutError(ComfyUIError):
    """A queued prompt did not finish before the configured timeout."""


class RenderExecutionError(ComfyUIError):
    """ComfyUI reported a workflow execution failure."""
