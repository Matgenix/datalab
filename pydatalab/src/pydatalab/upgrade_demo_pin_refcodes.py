"""DEMONSTRATION upgrade: pin mutable ``item_id`` references to immutable refcodes.

This is a *standalone, demonstration-only* module showing how a migration would
be written on top of the existing upgrade framework. It does not touch
:mod:`pydatalab.upgrade` or ``tasks.py``. To wire it in for real, the registered
function would be moved into the "Registered upgrades" section of
:mod:`pydatalab.upgrade`.

Issue
-----
Relationships used to refer to other items by ``item_id``, which has since
become mutable. Those references can therefore go stale if an ``item_id``
changes.

Remedy
------
Resolve each relationship's ``item_id`` to the target item's ``refcode``
(immutable and unique). If no matching item is found, deprecate the relationship.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydatalab.upgrade import DatabaseUpgrader, UpgradeAction

if TYPE_CHECKING:
    import pymongo.database
    from pymongo.client_session import ClientSession


@DatabaseUpgrader.register_upgrade("0.8.0")
def pin_item_id_references_to_refcodes(
    db: pymongo.database.Database,
    session: ClientSession | None = None,
    dry_run: bool = False,
) -> list[UpgradeAction]:
    """Pin ``item_id``-based relationships to immutable refcodes.

    Follows the upgrade-function contract: takes ``(db, session, dry_run)`` and
    returns the list of :class:`~pydatalab.upgrade.UpgradeAction` describing the
    overall changes made (or that would be made, when ``dry_run`` is set).
    """
    # Build a lookup from item_id to refcode
    item_id_to_refcode = {
        doc["item_id"]: doc["refcode"]
        for doc in db.items.find(
            {"item_id": {"$ne": None}, "refcode": {"$ne": None}},
            projection={"item_id": 1, "refcode": 1},
            session=session,
        )
    }

    pinned = 0
    deprecated = 0

    for item in db.items.find({}, projection={"_id": 1, "relationships": 1}, session=session):
        relationships = item.get("relationships") or []

        changed = False
        for rel in relationships:
            # Skip relationships that are already pinned or don't use an item_id.
            if rel.get("refcode") or not rel.get("item_id"):
                continue

            refcode = item_id_to_refcode.get(rel["item_id"])
            if refcode is not None:
                rel["refcode"] = refcode
                pinned += 1
            else:
                # Deprecate when no item matches
                rel["deprecated"] = True
                deprecated += 1
            changed = True

        if changed and not dry_run:
            db.items.update_one(
                {"_id": item["_id"]},
                {"$set": {"relationships": relationships}},
                session=session,
            )

    return [
        UpgradeAction(
            description=f"Pin {pinned} item_id reference(s) to their refcode",
            collection="items",
            action_type="update",
            details={"pinned": pinned},
        ),
        UpgradeAction(
            description=f"Deprecate {deprecated} unresolvable item_id reference(s)",
            collection="items",
            action_type="update",
            details={"deprecated": deprecated},
        ),
    ]
