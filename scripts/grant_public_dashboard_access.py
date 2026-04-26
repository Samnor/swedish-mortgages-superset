import os

from superset import app, db, security_manager
from superset.models.dashboard import Dashboard


DASHBOARD_SLUG = os.environ.get(
    "PUBLIC_DASHBOARD_SLUG", "swedish-mortgages-overview"
)

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


def _remove_permission(role, permission_name: str, view_menu_name: str) -> None:
    pvm = security_manager.find_permission_view_menu(permission_name, view_menu_name)
    if pvm and pvm in role.permissions:
        role.permissions.remove(pvm)


def _permission_pair(permission_view) -> tuple[str, str]:
    return (
        permission_view.permission.name,
        permission_view.view_menu.name,
    )


def main() -> None:
    with app.app_context():
        public_role = security_manager.find_role(
            app.config.get("AUTH_ROLE_PUBLIC", "Public")
        )
        if public_role is None:
            raise RuntimeError("Public role was not found")

        dashboard = (
            db.session.query(Dashboard)
            .filter(Dashboard.slug == DASHBOARD_SLUG)
            .one_or_none()
        )
        if dashboard is None:
            print(f"Public dashboard {DASHBOARD_SLUG!r} not found; skipping grants")
            return

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
