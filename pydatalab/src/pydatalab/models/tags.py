from typing import Literal

from pydatalab.models.entries import Entry
from pydatalab.models.traits import HasOwner


class Tag(Entry, HasOwner):
    """A tag that can be associated to other entities.

    A tag with no owner is global, otherwise it is owned by the user(s)
    in `creator_ids` and optionally read-shared with the groups in `group_ids`.
    """

    type: Literal["tags"] = "tags"

    name: str
    """A short, human-readable label for the tag."""

    description: str | None = None
    """An optional description of the tag, either in plain-text or a markup language."""

    color: str | None = None
    """An optional display color for the tag (e.g. a CSS hex string like `#f1c40f`)."""
