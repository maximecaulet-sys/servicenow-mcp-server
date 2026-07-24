"""
Outil MCP d'agrégation ServiceNow (équivalent GlideAggregate), via l'Aggregate API
native de ServiceNow (/api/now/stats/{table}) plutôt que le Table API paginé.

Ce module n'exécute rien tout seul à l'import : il expose `register(mcp, sn_request,
check_table_allowed)`, appelé depuis servicenow_mcp_server.py une fois que ces trois
objets existent.
"""


def register(mcp, sn_request, check_table_allowed) -> None:

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

        Args:
            table:    nom de la table (ex: 'sc_req_item').
            group_by: champs de regroupement séparés par des virgules, dot-walk autorisé
                      (ex: 'cat_item,cat_item.category').
            query:    requête encodée ServiceNow optionnelle (ex: 'active=true').
            count:    inclut le COUNT par groupe (par défaut True).
        """
        check_table_allowed(table)
        params: dict = {
            "sysparm_group_by": group_by,
            "sysparm_display_value": "all",  # renvoie value ET display_value pour chaque champ groupé
        }
        if count:
            params["sysparm_count"] = "true"
        if query:
            params["sysparm_query"] = query

        data = sn_request("GET", f"/api/now/stats/{table}", params=params).get("result", [])

        # Aplati groupby_fields + stats en un dict par ligne, plus simple à consommer côté Claude
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