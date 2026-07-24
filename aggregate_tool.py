AGGREGATE_ALLOWED_TABLES = {
    "sc_req_item", "sc_request", "sc_task",
    "incident", "incident_task",
    "change_request", "change_task",
    "problem", "problem_task",
}


def check_aggregate_table_allowed(table: str) -> None:
    if table not in AGGREGATE_ALLOWED_TABLES:
        raise ValueError(
            f"Table '{table}' non autorisée pour l'agrégation. "
            f"Tables disponibles : {sorted(AGGREGATE_ALLOWED_TABLES)}"
        )


def register(mcp, sn_request) -> None:

    @mcp.tool()
    def aggregate_records(
        table: str,
        group_by: str,
        query: str = "",
        count: bool = True,
    ) -> list[dict]:
        """
        Agrège des enregistrements ServiceNow (équivalent GlideAggregate) via l'Aggregate API.
        Lecture seule. Le comptage est fait côté serveur ServiceNow, pas de pagination nécessaire.
        Restreint à un sous-ensemble de tables de volumétrie (voir AGGREGATE_ALLOWED_TABLES).

        Args:
            table:    nom de la table (ex: 'sc_req_item').
            group_by: champs de regroupement séparés par des virgules, dot-walk autorisé
                      (ex: 'cat_item,cat_item.category').
            query:    requête encodée ServiceNow optionnelle (ex: 'active=true').
            count:    inclut le COUNT par groupe (par défaut True).
        """
        check_aggregate_table_allowed(table)
        params: dict = {
            "sysparm_group_by": group_by,
            "sysparm_display_value": "all",
        }
        if count:
            params["sysparm_count"] = "true"
        if query:
            params["sysparm_query"] = query

        data = sn_request("GET", f"/api/now/stats/{table}", params=params).get("result", [])

        rows = []
        for entry in data:
            row: dict = {}
            for gb in entry.get("groupby_fields", []):
                field = gb.get("field")
                row[field] = gb.get("value")
                row[f"{field}_display"] = gb.get("display_value")
            row.update(entry.get("stats", {}))
            rows.append(row)
        return rows