from ulid import ULID


def new_id(prefix: str = "") -> str:
    """Generate a sortable unique ID, optionally prefixed (e.g. 'org_01H...')."""
    ulid_str = str(ULID())
    return f"{prefix}_{ulid_str}" if prefix else ulid_str
