import os

from superset import app, db, security_manager
from superset.models.dashboard import Dashboard


DASHBOARD_SLUG = os.environ.get(
    "PUBLIC_DASHBOARD_SLUG", "swedish-mortgages-overview"
)


def _grant_permission(role, permission_name: str, view_menu_name: str) -> None:
    pvm = security_manager.add_permission_view_menu(permission_name, view_menu_name)
    if pvm not in role.permissions:
        security_manager.add_permission_role(role, pvm)


def _remove_permission(role, permission_name: str, view_menu_name: str) -> None:
    pvm = security_manager.find_permission_view_menu(permission_name, view_menu_name)
    if pvm and pvm in role.permissions:
        role.permissions.remove(pvm)


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

        # Guard against accidental broad public data access.
        _remove_permission(public_role, "all_datasource_access", "all_datasource_access")
        _remove_permission(public_role, "all_database_access", "all_database_access")

        for chart in dashboard.slices:
            dataset = chart.table
            if dataset is None:
                continue
            _grant_permission(public_role, "datasource_access", dataset.get_perm())

        db.session.commit()
        print(f"Public role can read dashboard {dashboard.slug!r}")


if __name__ == "__main__":
    main()
