
import importlib
import uuid as _stdlib_uuid


def get_uuid():
    """Return a UUID using uProtocol if available, else stdlib uuid4()."""
    try:
        # Most builds: function lives in uprotocol.uuid.factory
        uf = importlib.import_module("uprotocol.uuid.factory")
        # common names we've seen across versions
        for name in ("uuid", "uuid4", "random_uuid", "generate", "new"):
            if hasattr(uf, name) and callable(getattr(uf, name)):
                u = getattr(uf, name)()
                print(f"[uuid] used uprotocol.uuid.factory.{name}()")
                return u
    except Exception as e:
        print("[uuid] uprotocol.uuid.factory not usable:", e)

    # Fallback to Python stdlib
    u = _stdlib_uuid.uuid4()
    print("[uuid] fell back to stdlib uuid.uuid4()")
    return u


def build_uuri():
    """
    Try to build a uProtocol URI using known helper locations.
    Returns the URI value or a clear message if helpers aren't present.
    """
    candidates = (
        "uprotocol.uri",          # helpers might be exported at module level
        "uprotocol.uri.uri",      # helpers in a nested module
        "uprotocol.uri.builder",  # sometimes packaged as a builder/factory
        "uprotocol.uri.factory",
    )
    for mod_name in candidates:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        for fn_name in ("build", "of", "make", "create", "uuri"):
            if hasattr(mod, fn_name) and callable(getattr(mod, fn_name)):
                fn = getattr(mod, fn_name)
                try:
                    # try keyword style first
                    return fn(
                        ue_id="demo.app",
                        resource="/service/method",
                        authority="local",
                        version_major=1,
                    )
                except TypeError:
                    # some versions might be positional
                    return fn("demo.app", "/service/method", "local", 1)
                except Exception as e:
                    return f"[uri] {mod_name}.{fn_name}() existed but failed: {e}"
    return "[uri] No URI helpers found (tried uprotocol.uri[.uri|.builder|.factory])."


def main():
    u = get_uuid()
    print("Generated UUID:", u)
    uri_value = build_uuri()
    print("uProtocol URI:", uri_value)


if __name__ == "__main__":
    main()
