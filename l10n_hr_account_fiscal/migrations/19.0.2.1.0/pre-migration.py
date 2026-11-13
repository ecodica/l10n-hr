#  Copyright 2025 Ecodica d.o.o
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def _columns(cr, table):
    cr.execute(
        "SELECT oid, relkind FROM pg_catalog.pg_class "
        "WHERE oid = pg_catalog.to_regclass(%s)",
        [table],
    )
    relation = cr.fetchone()
    if relation is None:
        return None
    if relation[1] not in ("r", "p"):
        raise RuntimeError("Cannot migrate fiscal schedules: %s is not a table" % table)
    cr.execute(
        "SELECT attname FROM pg_catalog.pg_attribute "
        "WHERE attrelid = %s AND attnum > 0 AND NOT attisdropped",
        [relation[0]],
    )
    return {row[0] for row in cr.fetchall()}


def migrate(cr, version):
    parent = "l10n_hr_working_hours_schedule"
    line = "l10n_hr_working_hours_schedule_line"
    tables = {
        parent: "l10n_hr.working.hours.schedule",
        line: "l10n_hr.working.hours.schedule.line",
    }
    columns = {table: _columns(cr, table) for table in tables}
    # Earlier 19.0 revisions already stored persistent audit snapshots. Never
    # clear these, even if ir_model still has stale transient metadata.
    if "company_id" in (columns[parent] or set()):
        cr.execute("SELECT EXISTS (SELECT 1 FROM %s WHERE company_id IS NULL)" % parent)
        if cr.fetchone()[0]:
            raise RuntimeError(
                "Cannot migrate fiscal schedules: persistent rows have ambiguous "
                "ownership (missing company_id). Review the data before upgrading."
            )
        return

    populated = []
    for table in tables:
        if columns[table] is not None:
            # All interpolated identifiers are fixed names from the mapping.
            cr.execute("SELECT EXISTS (SELECT 1 FROM %s)" % table)
            if cr.fetchone()[0]:
                populated.append(table)
    if not populated:
        return

    metadata_columns = _columns(cr, "ir_model")
    transient = {}
    if metadata_columns and {"model", "transient"} <= metadata_columns:
        cr.execute(
            "SELECT model, transient FROM ir_model WHERE model IN %s",
            [tuple(tables.values())],
        )
        transient = dict(cr.fetchall())
    # Validate BOTH tables before deleting either. Missing metadata is not
    # evidence that unowned rows are disposable; stop rather than let Odoo
    # default their company_id to the company performing the upgrade.
    for table in populated:
        if "company_id" in columns[table] or transient.get(tables[table]) is not True:
            raise RuntimeError(
                "Cannot migrate fiscal schedules: nonempty %s has ambiguous "
                "ownership; expected legacy transient metadata. Review the "
                "data before upgrading." % table
            )

    # The original transient schema had no company_id. These ephemeral rows
    # are regenerable, but cannot safely be assigned to any upgrade company.
    # Keep tables, views and FKs: DROP ... CASCADE would remove dependencies,
    # including the premise relation's FK. Delete children before parents.
    for table in (line, parent):
        if table in populated:
            cr.execute("DELETE FROM %s" % table)
