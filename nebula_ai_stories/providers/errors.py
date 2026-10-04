class ProviderError(RuntimeError):
    """Base class for user-facing local AI provider failures."""


class ProviderConfigurationError(ProviderError):
    """Provider settings are incomplete or invalid for a request."""


class ProviderConnectionError(ProviderError):
    """The configured local AI server could not be reached."""


class ProviderResponseError(ProviderError):
    """The local AI server returned an invalid HTTP/JSON response."""


class ProviderOutputError(ProviderError):
    """The model output could not be converted into valid stories."""
