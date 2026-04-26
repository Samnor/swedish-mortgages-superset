import os
import json
import uuid

from superset import app, db, security_manager
from superset.connectors.sqla.models import SqlaTable
from superset.models.dashboard import Dashboard
from superset.models.slice import Slice


DASHBOARD_SLUG = os.environ.get(
    "PUBLIC_DASHBOARD_SLUG", "swedish-mortgages-overview"
)
DASHBOARD_TITLE = "Swedish Mortgages Overview"
CHART_NAME = "Mortgage Market Rates Snapshot"

SAFE_BASE_PERMISSIONS = {
    ("can_dashboard", "Superset"),
    ("can_dashboard_permalink", "Superset"),
    ("can_explore", "Superset"),
    ("can_explore_json", "Superset"),
    ("can_fetch_datasource_metadata", "Superset"),
    ("can_log", "Superset"),
    ("can_read", "Dashboard"),
    ("can_read", "Chart"),
    ("can_read", "Dataset"),
    ("can_get", "Datasource"),
    ("can_external_metadata", "Datasource"),
    ("can_external_metadata_by_name", "Datasource"),
    ("can_query", "Api"),
    ("can_query_form_data", "Api"),
    ("can_time_range", "Api"),
    ("can_read", "DashboardFilterStateRestApi"),
    ("can_write", "DashboardFilterStateRestApi"),
    ("can_read", "DashboardPermalinkRestApi"),
    ("can_write", "DashboardPermalinkRestApi"),
    ("can_read", "ExploreFormDataRestApi"),
    ("can_write", "ExploreFormDataRestApi"),
    ("can_read", "ExplorePermalinkRestApi"),
    ("can_write", "ExplorePermalinkRestApi"),
    ("menu_access", "Dashboards"),
}


def _grant_permission(role, permission_name: str, view_menu_name: str) -> None:
    pvm = security_manager.add_permission_view_menu(permission_name, view_menu_name)
    if pvm not in role.permissions:
        security_manager.add_permission_role(role, pvm)


def _permission_pair(permission_view) -> tuple[str, str]:
    return (
        permission_view.permission.name,
        permission_view.view_menu.name,
    )


def _dashboard_layout(chart: Slice) -> str:
    return json.dumps(
        {
            "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
            "GRID_ID": {
                "type": "GRID",
                "id": "GRID_ID",
                "children": ["HEADER_ID", "ROW-1", "ROW-2"],
            },
            "HEADER_ID": {
                "type": "HEADER",
                "id": "HEADER_ID",
                "meta": {"text": DASHBOARD_TITLE},
            },
            "ROW-1": {
                "type": "ROW",
                "id": "ROW-1",
                "children": ["CHART-1"],
                "meta": {"background": "BACKGROUND_TRANSPARENT"},
            },
            "CHART-1": {
                "type": "CHART",
                "id": "CHART-1",
                "children": [],
                "meta": {
                    "chartId": chart.id,
                    "sliceName": chart.slice_name,
                    "width": 12,
                    "height": 50,
                },
            },
            "ROW-2": {
                "type": "ROW",
                "id": "ROW-2",
                "children": ["MARKDOWN-1"],
                "meta": {"background": "BACKGROUND_TRANSPARENT"},
            },
            "MARKDOWN-1": {
                "type": "MARKDOWN",
                "id": "MARKDOWN-1",
                "children": [],
                "meta": {
                    "width": 12,
                    "height": 18,
                    "code": (
                        "Public preview dashboard for Swedish mortgage market "
                        "context. The full Superset instance remains private "
                        "except for this published dashboard."
                    ),
                },
            },
        }
    )


def _chart_params(dataset: SqlaTable) -> str:
    return json.dumps(
        {
            "datasource": f"{dataset.id}__table",
            "viz_type": "table",
            "query_mode": "raw",
            "columns": [
                "rate_date",
                "policy_rate",
                "government_bond_5y",
                "covered_bond_5y",
                "covered_bond_spread_5y",
            ],
            "adhoc_filters": [],
            "row_limit": 100,
            "order_by_cols": ['["rate_date", false]'],
            "page_length": 20,
            "show_cell_bars": False,
            "include_search": False,
            "allow_rearrange_columns": True,
            "time_range": "No filter",
            "table_timestamp_format": "smart_date",
        }
    )


def _ensure_public_dashboard() -> Dashboard:
    dataset = (
        db.session.query(SqlaTable)
        .filter(SqlaTable.table_name == "rates_daily")
        .one_or_none()
    )
    if dataset is None:
        raise RuntimeError("Expected rates_daily dataset was not found")

    chart = (
        db.session.query(Slice)
        .filter(Slice.slice_name == CHART_NAME)
        .one_or_none()
    )
    if chart is None:
        chart = Slice(
            slice_name=CHART_NAME,
            viz_type="table",
            datasource_id=dataset.id,
            datasource_type="table",
            datasource_name=dataset.table_name,
            params=_chart_params(dataset),
            perm=dataset.get_perm(),
            schema_perm=dataset.get_schema_perm(),
            uuid=uuid.uuid4(),
        )
        db.session.add(chart)
        db.session.flush()
    else:
        chart.viz_type = "table"
        chart.datasource_id = dataset.id
        chart.datasource_type = "table"
        chart.datasource_name = dataset.table_name
        chart.params = _chart_params(dataset)
        chart.perm = dataset.get_perm()
        chart.schema_perm = dataset.get_schema_perm()

    dashboard = (
        db.session.query(Dashboard)
        .filter(Dashboard.slug == DASHBOARD_SLUG)
        .one_or_none()
    )
    if dashboard is None:
        dashboard = Dashboard(
            dashboard_title=DASHBOARD_TITLE,
            slug=DASHBOARD_SLUG,
            published=True,
            position_json="{}",
            json_metadata="{}",
            css="",
            uuid=uuid.uuid4(),
        )
        db.session.add(dashboard)
        db.session.flush()

    dashboard.dashboard_title = DASHBOARD_TITLE
    dashboard.published = True
    dashboard.position_json = _dashboard_layout(chart)
    dashboard.json_metadata = "{}"
    dashboard.css = ""
    if chart not in dashboard.slices:
        dashboard.slices.append(chart)
    return dashboard


def main() -> None:
    with app.app_context():
        public_role = security_manager.find_role(
            app.config.get("AUTH_ROLE_PUBLIC", "Public")
        )
        if public_role is None:
            raise RuntimeError("Public role was not found")

        dashboard = _ensure_public_dashboard()

        allowed_permissions = set(SAFE_BASE_PERMISSIONS)

        for chart in dashboard.slices:
            dataset = chart.table
            if dataset is None:
                continue
            dataset_perm = dataset.get_perm()
            allowed_permissions.add(("datasource_access", dataset_perm))
            _grant_permission(public_role, "datasource_access", dataset_perm)

        for permission_name, view_menu_name in SAFE_BASE_PERMISSIONS:
            _grant_permission(public_role, permission_name, view_menu_name)

        # Prune anything broader than the public dashboard needs. This removes
        # permissions copied from Gamma by older releases.
        public_role.permissions = [
            pvm
            for pvm in public_role.permissions
            if _permission_pair(pvm) in allowed_permissions
        ]

        db.session.commit()
        print(f"Public role can read dashboard {dashboard.slug!r}")


if __name__ == "__main__":
    main()
