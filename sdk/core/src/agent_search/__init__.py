__all__ = ["advanced_rag"]


def __getattr__(name: str):
    if name == "advanced_rag":
        from . import public_api

        return getattr(public_api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
