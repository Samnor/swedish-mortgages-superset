import json
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path


DB_PATH = Path("/app/superset_home/superset.db")
DATABASE_NAME = os.environ.get("SUPERSET_DATABASE_NAME", "Athena Swedish Mortgages")
MARTS_SCHEMA = os.environ.get("ATHENA_SCHEMA", "swedish_mortgages_dev_marts")
DASHBOARD_TITLE = "Swedish Mortgages Overview"
DASHBOARD_SLUG = "swedish-mortgages-overview"

LINE_CHART = "echarts_timeseries_line"
HEATMAP_CHART = "heatmap_v2"
DIST_BAR_CHART = "dist_bar"
TABLE_CHART = "table"
VIRTUAL_FRESHNESS_DATASET = "freshness_snapshot"

FRESHNESS_SQL = f"""
select
  'Riksbank market rates' as source_name,
  cast(max(rate_date) as varchar) as latest_observation,
  cast(date_diff('day', max(rate_date), current_date) as integer) as age_days,
  'daily' as cadence,
  case
    when date_diff('day', max(rate_date), current_date) <= 2 then 'fresh'
    when date_diff('day', max(rate_date), current_date) <= 7 then 'aging'
    else 'stale'
  end as freshness_status
from {MARTS_SCHEMA}.rates_daily

union all

select
  'Bank listed rates' as source_name,
  cast(max(scrape_date) as varchar) as latest_observation,
  cast(date_diff('day', max(scrape_date), current_date) as integer) as age_days,
  'daily' as cadence,
  case
    when date_diff('day', max(scrape_date), current_date) <= 1 then 'fresh'
    when date_diff('day', max(scrape_date), current_date) <= 3 then 'aging'
    else 'stale'
  end as freshness_status
from {MARTS_SCHEMA}.bank_margin_analysis

union all

select
  'Funding proxy curve' as source_name,
  cast(max(funding_date) as varchar) as latest_observation,
  cast(date_diff('day', max(funding_date), current_date) as integer) as age_days,
  'daily market proxy' as cadence,
  case
    when date_diff('day', max(funding_date), current_date) <= 2 then 'fresh'
    when date_diff('day', max(funding_date), current_date) <= 7 then 'aging'
    else 'stale'
  end as freshness_status
from {MARTS_SCHEMA}.bank_margin_analysis

union all

select
  'SCB market averages' as source_name,
  cast(max(cast(scb_period_month || '-01' as date)) as varchar) as latest_observation,
  cast(date_diff('day', max(cast(scb_period_month || '-01' as date)), current_date) as integer) as age_days,
  'monthly' as cadence,
  case
    when date_diff('day', max(cast(scb_period_month || '-01' as date)), current_date) <= 45 then 'fresh'
    when date_diff('day', max(cast(scb_period_month || '-01' as date)), current_date) <= 75 then 'aging'
    else 'stale'
  end as freshness_status
from {MARTS_SCHEMA}.bank_vs_market_analysis
""".strip()

CHARTS = [
    {
        "slice_name": "Data Freshness Snapshot",
        "table_name": VIRTUAL_FRESHNESS_DATASET,
        "viz_type": TABLE_CHART,
        "columns": [
            "source_name",
            "latest_observation",
            "age_days",
            "cadence",
            "freshness_status",
        ],
        "order_by_cols": ['["age_days", false]'],
        "height": 22,
        "description_markdown": (
            "**Use:** Check this first before trusting the rest of the dashboard. "
            "It shows the latest available timestamp for each feed, how old it is in "
            "days, and whether the feed still looks fresh for its expected cadence.\n\n"
            "**Sources:** Derived directly from the live dbt marts for Riksbank rates, "
            "bank listed rates, funding proxy dates, and SCB market-average data."
        ),
    },
    {
        "slice_name": "Swedish Mortgage Rate Levels",
        "table_name": "rates_daily",
        "viz_type": LINE_CHART,
        "metrics": ["Policy Rate", "5Y Government Bond", "5Y Covered Bond"],
        "x_axis": "rate_date",
        "height": 42,
        "description_markdown": (
            "**Use:** Track the broad mortgage-rate regime over time. Compare "
            "the policy rate with 5Y government and covered-bond yields before "
            "checking bank pricing.\n\n"
            "**Sources:** Riksbank SWEA API series for policy and bond yields."
        ),
    },
    {
        "slice_name": "Covered Bond Spreads",
        "table_name": "rates_daily",
        "viz_type": LINE_CHART,
        "metrics": ["2Y Spread", "5Y Spread"],
        "x_axis": "rate_date",
        "height": 34,
        "description_markdown": (
            "**Use:** Isolate funding-market stress. Rising spreads mean covered "
            "bonds are getting more expensive relative to government bonds.\n\n"
            "**Sources:** Riksbank SWEA API series for government and covered-bond yields."
        ),
    },
    {
        "slice_name": "Gross Margin Heatmap",
        "table_name": "bank_margin_analysis",
        "viz_type": HEATMAP_CHART,
        "metric": "Gross Margin",
        "x_axis": "period_label_display",
        "groupby": "bank",
        "height": 32,
        "description_markdown": (
            "**Use:** Compare listed gross margin by bank and fixing period. "
            "Scan horizontally for each bank's maturity curve or vertically for "
            "same-bucket competition.\n\n"
            "**Sources:** Bank listed mortgage rates scraped from SBAB, Nordea, "
            "and Swedbank plus Riksbank SWEA funding proxies."
        ),
    },
    {
        "slice_name": "Funding Cost by Mortgage Term",
        "table_name": "bank_margin_analysis",
        "viz_type": DIST_BAR_CHART,
        "metric": "Funding Cost",
        "groupby": "period_label",
        "height": 30,
        "description_markdown": (
            "**Use:** Read this as the stylized funding-cost curve behind the margin model. "
            "Short fixing periods are not assumed to be funded with same-duration debt; "
            "they are modeled as longer covered-bond funding swapped into 3M money-market "
            "exposure. Fixed buckets use a covered-bond curve with interpolation between "
            "2Y and 5Y where needed.\n\n"
            "**Examples:**\n"
            "- A 3-month floating mortgage uses `policy rate + 3M SWESTR average spread + "
            "5Y covered-bond spread`.\n"
            "- A 3-year fixed mortgage uses an interpolated blend of the 2Y and 5Y "
            "government curve plus an interpolated covered-bond spread.\n\n"
            "**Sources:** Live Riksbank rates for policy, 3M compounded SWESTR averages, "
            "government bonds, and covered bonds. The funding structure is guided by "
            "Riksbank mortgage-funding commentary and SBAB disclosure as a transparent "
            "Swedish-bank proxy."
        ),
    },
    {
        "slice_name": "Funding Cost Components by Mortgage Term",
        "table_name": "bank_margin_analysis",
        "viz_type": DIST_BAR_CHART,
        "groupby": "period_label_display",
        "metrics": [
            "Policy Anchor",
            "3M SWESTR Spread",
            "Risk-Free Curve",
            "Covered Spread",
        ],
        "bar_stacked": True,
        "x_axis_label": "Mortgage term",
        "height": 34,
        "description_markdown": (
            "**Use:** Break the funding estimate into its visible building blocks by term. "
            "Short buckets should show policy and money-market carry, while fixed buckets "
            "shift toward the interpolated risk-free curve plus covered-bond spread.\n\n"
            "**Sources:** Live Riksbank SWEA rates transformed by dbt into component-level "
            "funding estimates."
        ),
    },
    {
        "slice_name": "3M Floating Mortgage Margin Breakdown",
        "table_name": "bank_margin_analysis",
        "viz_type": DIST_BAR_CHART,
        "groupby": "bank",
        "metrics": [
            "Policy Anchor",
            "3M SWESTR Spread",
            "Covered Spread",
            "Gross Margin",
        ],
        "bar_stacked": True,
        "x_axis_label": "Bank",
        "adhoc_filters": [
            {
                "clause": "WHERE",
                "subject": "period_label_display",
                "operator": "==",
                "comparator": "3M",
                "expressionType": "SIMPLE",
            }
        ],
        "height": 28,
        "description_markdown": (
            "**Use:** This is the concrete 3-month floating example. It shows the listed "
            "3M mortgage rate and the components used to explain it: policy anchor, 3M "
            "SWESTR spread, 5Y covered-bond spread, and implied gross margin. The stacked "
            "bar adds up to the listed rate.\n\n"
            "**Why the margin looks this way:** The model treats a floating mortgage as "
            "funded through longer covered bonds that are swapped into floating-rate exposure, "
            "so the margin is what remains after subtracting those short-rate and covered-spread "
            "components from the listed rate.\n\n"
            "**Sources:** SBAB, Nordea, and Swedbank listed rates plus live Riksbank "
            "policy, 3M compounded SWESTR average, and covered-bond data."
        ),
    },
    {
        "slice_name": "3Y Fixed Mortgage Margin Breakdown",
        "table_name": "bank_margin_analysis",
        "viz_type": DIST_BAR_CHART,
        "groupby": "bank",
        "metrics": [
            "Risk-Free Curve",
            "Covered Spread",
            "Gross Margin",
        ],
        "bar_stacked": True,
        "x_axis_label": "Bank",
        "adhoc_filters": [
            {
                "clause": "WHERE",
                "subject": "period_label_display",
                "operator": "==",
                "comparator": "3Y",
                "expressionType": "SIMPLE",
            }
        ],
        "height": 28,
        "description_markdown": (
            "**Use:** This is the concrete 3-year fixed example. It shows the listed 3Y "
            "mortgage rate, the interpolated risk-free curve, the covered-bond spread, "
            "and the implied gross margin for each bank. The stacked bar adds up to the "
            "listed rate.\n\n"
            "**Why the margin looks this way:** The model does not force 3Y loans onto a "
            "single 5Y funding point. Instead it blends the 2Y and 5Y curve and spread "
            "inputs, then treats the remainder of the listed rate as margin.\n\n"
            "**Sources:** SBAB, Nordea, and Swedbank listed rates plus live Riksbank SWEA "
            "government-bond and covered-bond data."
        ),
    },
    {
        "slice_name": "Listed vs Market Discount Heatmap",
        "table_name": "bank_vs_market_analysis",
        "viz_type": HEATMAP_CHART,
        "metric": "Listed vs Market Discount",
        "x_axis": "period_label_display",
        "groupby": "bank",
        "height": 32,
        "description_markdown": (
            "**Use:** Compare listed bank rates with the SCB market average. "
            "Higher values mean the bank is pricing further above market for "
            "that bucket.\n\n"
            "**Sources:** SBAB, Nordea, and Swedbank listed rates scraped daily; "
            "SCB table RantaT04N for market averages; Riksbank SWEA for funding context."
        ),
    },
]

DATASET_COLUMNS = {
    VIRTUAL_FRESHNESS_DATASET: {
        "source_name": ("STRING", False),
        "latest_observation": ("STRING", False),
        "age_days": ("BIGINT", False),
        "cadence": ("STRING", False),
        "freshness_status": ("STRING", False),
    },
    "rates_daily": {
        "rate_date": ("DATE", True),
        "policy_rate": ("DOUBLE", False),
        "govbond_5y": ("DOUBLE", False),
        "mortbond_5y": ("DOUBLE", False),
        "spread_2y": ("DOUBLE", False),
        "spread_5y": ("DOUBLE", False),
    },
    "bank_margin_analysis": {
        "bank": ("STRING", False),
        "period_label": ("STRING", False),
        "period_label_display": ("STRING", False),
        "funding_model": ("STRING", False),
        "funding_weight_2y": ("DOUBLE", False),
        "funding_weight_5y": ("DOUBLE", False),
        "list_rate": ("DOUBLE", False),
        "policy_anchor_component": ("DOUBLE", False),
        "short_rate_spread_component": ("DOUBLE", False),
        "risk_free_curve_component": ("DOUBLE", False),
        "covered_bond_spread_component": ("DOUBLE", False),
        "funding_cost": ("DOUBLE", False),
        "gross_margin": ("DOUBLE", False),
    },
    "bank_vs_market_analysis": {
        "bank": ("STRING", False),
        "period_label_display": ("STRING", False),
        "list_vs_mkt_discount": ("DOUBLE", False),
    },
}

METRICS = {
    VIRTUAL_FRESHNESS_DATASET: [],
    "rates_daily": [
        ("Policy Rate", "AVG(policy_rate)", "Policy Rate"),
        ("5Y Government Bond", "AVG(govbond_5y)", "5Y Government Bond"),
        ("5Y Covered Bond", "AVG(mortbond_5y)", "5Y Covered Bond"),
        ("2Y Spread", "AVG(spread_2y)", "2Y Spread"),
        ("5Y Spread", "AVG(spread_5y)", "5Y Spread"),
    ],
    "bank_margin_analysis": [
        ("Listed Rate", "AVG(list_rate)", "Listed Rate"),
        ("Policy Anchor", "AVG(policy_anchor_component)", "Policy Anchor"),
        ("3M SWESTR Spread", "AVG(short_rate_spread_component)", "3M SWESTR Spread"),
        ("Risk-Free Curve", "AVG(risk_free_curve_component)", "Risk-Free Curve"),
        ("Covered Spread", "AVG(covered_bond_spread_component)", "Covered Spread"),
        ("Funding Cost", "AVG(funding_cost)", "Funding Cost"),
        ("Gross Margin", "AVG(gross_margin)", "Gross Margin"),
    ],
    "bank_vs_market_analysis": [
        ("Listed vs Market Discount", "AVG(list_vs_mkt_discount)", "Listed vs Market Discount"),
    ],
}


def _now() -> str:
    return datetime.utcnow().isoformat(sep=" ")


def _ensure_table_column(
    cur: sqlite3.Cursor,
    table_id: int,
    column_name: str,
    column_type: str,
    is_dttm: bool,
) -> None:
    now = _now()
    row = cur.execute(
        """
        SELECT id FROM table_columns
        WHERE table_id = ? AND column_name = ?
        """,
        (table_id, column_name),
    ).fetchone()
    if row is None:
        cur.execute(
            """
            INSERT INTO table_columns (
                created_on, changed_on, table_id, column_name, is_dttm,
                is_active, type, groupby, filterable, verbose_name, uuid
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, 1, 1, ?, ?)
            """,
            (
                now,
                now,
                table_id,
                column_name,
                1 if is_dttm else 0,
                column_type,
                column_name,
                uuid.uuid4().bytes,
            ),
        )
        return

    cur.execute(
        """
        UPDATE table_columns
        SET changed_on = ?, type = ?, is_dttm = ?, groupby = 1, filterable = 1,
            verbose_name = ?
        WHERE table_id = ? AND column_name = ?
        """,
        (now, column_type, 1 if is_dttm else 0, column_name, table_id, column_name),
    )


def _dataset_permissions(
    cur: sqlite3.Cursor,
    table_name: str,
    table_id: int,
    database_id: int,
    schema: str,
) -> tuple[str, str]:
    db_row = cur.execute(
        "SELECT database_name FROM dbs WHERE id = ?",
        (database_id,),
    ).fetchone()
    database_name = db_row[0] if db_row else DATABASE_NAME
    return (
        f"[{database_name}].[{table_name}](id:{table_id})",
        f"[{database_name}].[{schema}]",
    )


def _sync_dataset_schema(cur: sqlite3.Cursor, table_name: str) -> tuple[int, int]:
    if table_name == VIRTUAL_FRESHNESS_DATASET:
        return _ensure_virtual_freshness_dataset(cur)

    row = cur.execute(
        """
        SELECT id, database_id FROM tables
        WHERE table_name = ?
          AND schema = ?
        """,
        (table_name, MARTS_SCHEMA),
    ).fetchone()
    if row is None:
        row = cur.execute(
            """
            SELECT id, database_id FROM tables
            WHERE table_name = ?
            """,
            (table_name,),
        ).fetchone()
    if row is None:
        raise SystemExit(f"Expected dataset {table_name!r} was not found in Superset")

    table_id = int(row[0])
    database_id = int(row[1])
    perm, schema_perm = _dataset_permissions(
        cur, table_name, table_id, database_id, MARTS_SCHEMA
    )
    cur.execute(
        """
        UPDATE tables
        SET schema = ?, perm = ?, schema_perm = ?, changed_on = ?
        WHERE id = ?
        """,
        (MARTS_SCHEMA, perm, schema_perm, _now(), table_id),
    )

    for column_name, (column_type, is_dttm) in DATASET_COLUMNS[table_name].items():
        _ensure_table_column(cur, table_id, column_name, column_type, is_dttm)

    return table_id, database_id


def _ensure_virtual_freshness_dataset(cur: sqlite3.Cursor) -> tuple[int, int]:
    now = _now()
    db_row = cur.execute(
        "SELECT id FROM dbs WHERE database_name = ?",
        (DATABASE_NAME,),
    ).fetchone()
    if db_row is None:
        raise SystemExit(f"Expected Superset database {DATABASE_NAME!r} was not found")
    database_id = int(db_row[0])
    row = cur.execute(
        """
        SELECT id FROM tables
        WHERE table_name = ?
        """,
        (VIRTUAL_FRESHNESS_DATASET,),
    ).fetchone()

    if row is None:
        cur.execute(
            """
            INSERT INTO tables (
                created_on, changed_on, table_name, main_dttm_col, database_id,
                created_by_fk, changed_by_fk, schema, sql, params, perm,
                is_sqllab_view, schema_perm, uuid, catalog
            )
            VALUES (?, ?, ?, NULL, ?, 1, 1, ?, ?, '{}', ?, 1, ?, ?, ?)
            """,
            (
                now,
                now,
                VIRTUAL_FRESHNESS_DATASET,
                database_id,
                MARTS_SCHEMA,
                FRESHNESS_SQL,
                f"[{DATABASE_NAME}].[{VIRTUAL_FRESHNESS_DATASET}](id:virtual)",
                f"[{DATABASE_NAME}].[{MARTS_SCHEMA}]",
                uuid.uuid4().bytes,
                "awsdatacatalog",
            ),
        )
        table_id = int(cur.lastrowid)
    else:
        table_id = int(row[0])
        cur.execute(
            """
            UPDATE tables
            SET changed_on = ?, schema = ?, sql = ?, is_sqllab_view = 1, catalog = ?
            WHERE id = ?
            """,
            (now, MARTS_SCHEMA, FRESHNESS_SQL, "awsdatacatalog", table_id),
        )

    perm, schema_perm = _dataset_permissions(
        cur, VIRTUAL_FRESHNESS_DATASET, table_id, database_id, MARTS_SCHEMA
    )
    cur.execute(
        """
        UPDATE tables
        SET perm = ?, schema_perm = ?, changed_on = ?
        WHERE id = ?
        """,
        (perm, schema_perm, now, table_id),
    )

    for column_name, (column_type, is_dttm) in DATASET_COLUMNS[VIRTUAL_FRESHNESS_DATASET].items():
        _ensure_table_column(cur, table_id, column_name, column_type, is_dttm)

    return table_id, database_id


def _ensure_metric(
    cur: sqlite3.Cursor,
    table_id: int,
    metric_name: str,
    expression: str,
    verbose_name: str,
) -> None:
    now = _now()
    row = cur.execute(
        """
        SELECT id FROM sql_metrics
        WHERE table_id = ? AND metric_name = ?
        """,
        (table_id, metric_name),
    ).fetchone()
    if row is None:
        cur.execute(
            """
            INSERT INTO sql_metrics (
                created_on, changed_on, metric_name, verbose_name, metric_type,
                table_id, expression, created_by_fk, changed_by_fk, uuid
            )
            VALUES (?, ?, ?, ?, 'expression', ?, ?, 1, 1, ?)
            """,
            (
                now,
                now,
                metric_name,
                verbose_name,
                table_id,
                expression,
                uuid.uuid4().bytes,
            ),
        )
        return

    cur.execute(
        """
        UPDATE sql_metrics
        SET changed_on = ?, verbose_name = ?, expression = ?
        WHERE table_id = ? AND metric_name = ?
        """,
        (now, verbose_name, expression, table_id, metric_name),
    )


def _ensure_metrics(cur: sqlite3.Cursor, table_name: str, table_id: int) -> None:
    for metric_name, expression, verbose_name in METRICS[table_name]:
        _ensure_metric(cur, table_id, metric_name, expression, verbose_name)


def _line_chart_params(table_id: int, chart: dict[str, object]) -> str:
    params = {
        "datasource": f"{table_id}__table",
        "viz_type": LINE_CHART,
        "x_axis": chart["x_axis"],
        "time_grain_sqla": "P1D",
        "x_axis_sort_asc": True,
        "x_axis_sort_series": "name",
        "x_axis_sort_series_ascending": True,
        "metrics": chart["metrics"],
        "groupby": [],
        "adhoc_filters": [
            {
                "clause": "WHERE",
                "subject": chart["x_axis"],
                "operator": "TEMPORAL_RANGE",
                "comparator": "No filter",
                "expressionType": "SIMPLE",
            }
        ],
        "order_desc": False,
        "row_limit": 10000,
        "truncate_metric": True,
        "show_empty_columns": False,
        "comparison_type": "values",
        "annotation_layers": [],
        "forecastPeriods": 0,
        "forecastInterval": 0.8,
        "x_axis_title_margin": 15,
        "y_axis_title_margin": 15,
        "y_axis_title_position": "Left",
        "sort_series_type": "sum",
        "color_scheme": "supersetColors",
        "seriesType": "line",
        "only_total": False,
        "opacity": 0.25,
        "markerSize": 4,
        "show_legend": True,
        "legendType": "scroll",
        "legendOrientation": "top",
        "x_axis_time_format": "smart_date",
        "rich_tooltip": True,
        "tooltipTimeFormat": "smart_date",
        "y_axis_format": "SMART_NUMBER",
        "truncateXAxis": True,
        "y_axis_bounds": [None, None],
        "extra_form_data": {},
    }
    return json.dumps(params)


def _heatmap_params(table_id: int, chart: dict[str, object]) -> str:
    params = {
        "datasource": f"{table_id}__table",
        "viz_type": HEATMAP_CHART,
        "x_axis": chart["x_axis"],
        "time_grain_sqla": "P1D",
        "groupby": chart["groupby"],
        "metric": chart["metric"],
        "adhoc_filters": [],
        "row_limit": 10000,
        "sort_x_axis": "alpha_asc",
        "sort_y_axis": "alpha_asc",
        "normalize_across": "heatmap",
        "legend_type": "continuous",
        "linear_color_scheme": "superset_seq_1",
        "xscale_interval": -1,
        "yscale_interval": -1,
        "left_margin": "auto",
        "bottom_margin": "auto",
        "value_bounds": [None, None],
        "y_axis_format": ".2f",
        "x_axis_time_format": "smart_date",
        "show_legend": True,
        "show_percentage": False,
        "show_values": True,
        "extra_form_data": {},
    }
    return json.dumps(params)


def _dist_bar_params(table_id: int, chart: dict[str, object]) -> str:
    metrics = chart["metrics"] if "metrics" in chart else [chart["metric"]]
    params = {
        "datasource": f"{table_id}__table",
        "viz_type": DIST_BAR_CHART,
        "groupby": [chart["groupby"]],
        "metrics": metrics,
        "columns": [],
        "adhoc_filters": chart.get("adhoc_filters", []),
        "bar_stacked": chart.get("bar_stacked", False),
        "color_scheme": "supersetColors",
        "contribution": False,
        "order_desc": True,
        "queryFields": {
            "columns": "groupby",
            "groupby": "groupby",
            "metrics": "metrics",
        },
        "row_limit": None,
        "show_bar_value": True,
        "show_controls": False,
        "show_legend": len(metrics) > 1,
        "time_range": "No filter",
        "viz_type": DIST_BAR_CHART,
        "x_axis_label": chart.get("x_axis_label", "Fixing period"),
        "x_ticks_layout": "flat",
        "y_axis_format": ".2f",
    }
    return json.dumps(params)


def _table_chart_params(table_id: int, chart: dict[str, object]) -> str:
    params = {
        "datasource": f"{table_id}__table",
        "viz_type": TABLE_CHART,
        "query_mode": "raw",
        "columns": chart["columns"],
        "adhoc_filters": [],
        "row_limit": 100,
        "order_by_cols": chart["order_by_cols"],
        "page_length": 10,
        "show_cell_bars": False,
        "include_search": False,
        "allow_rearrange_columns": True,
        "time_range": "No filter",
        "table_timestamp_format": "smart_date",
    }
    return json.dumps(params)


def _chart_params(table_id: int, chart: dict[str, object]) -> str:
    if chart["viz_type"] == TABLE_CHART:
        return _table_chart_params(table_id, chart)
    if chart["viz_type"] == LINE_CHART:
        return _line_chart_params(table_id, chart)
    if chart["viz_type"] == HEATMAP_CHART:
        return _heatmap_params(table_id, chart)
    if chart["viz_type"] == DIST_BAR_CHART:
        return _dist_bar_params(table_id, chart)
    raise SystemExit(f"Unsupported viz type {chart['viz_type']!r}")


def _ensure_chart(cur: sqlite3.Cursor, chart: dict[str, object]) -> int:
    table_name = str(chart["table_name"])
    table_id, database_id = _sync_dataset_schema(cur, table_name)
    _ensure_metrics(cur, table_name, table_id)

    now = _now()
    perm, schema_perm = _dataset_permissions(
        cur, table_name, table_id, database_id, MARTS_SCHEMA
    )
    params = _chart_params(table_id, chart)

    row = cur.execute(
        "SELECT id FROM slices WHERE slice_name = ?",
        (chart["slice_name"],),
    ).fetchone()
    if row is None:
        cur.execute(
            """
            INSERT INTO slices (
                created_on, changed_on, slice_name, datasource_type, viz_type,
                params, created_by_fk, changed_by_fk, datasource_id, perm,
                schema_perm, uuid, last_saved_at, last_saved_by_fk,
                is_managed_externally
            )
            VALUES (?, ?, ?, 'table', ?, ?, 1, 1, ?, ?, ?, ?, ?, 1, 0)
            """,
            (
                now,
                now,
                chart["slice_name"],
                chart["viz_type"],
                params,
                table_id,
                perm,
                schema_perm,
                uuid.uuid4().bytes,
                now,
            ),
        )
        return int(cur.lastrowid)

    chart_id = int(row[0])
    cur.execute(
        """
        UPDATE slices
        SET changed_on = ?, datasource_type = 'table', viz_type = ?,
            datasource_id = ?, params = ?, perm = ?, schema_perm = ?,
            last_saved_at = ?, last_saved_by_fk = 1
        WHERE id = ?
        """,
        (now, chart["viz_type"], table_id, params, perm, schema_perm, now, chart_id),
    )
    return chart_id


def _ensure_dashboard(cur: sqlite3.Cursor) -> int:
    row = cur.execute(
        "SELECT id FROM dashboards WHERE slug = ?",
        (DASHBOARD_SLUG,),
    ).fetchone()
    if row is not None:
        return int(row[0])

    now = _now()
    cur.execute(
        """
        INSERT INTO dashboards (
            created_on, changed_on, dashboard_title, position_json,
            description, css, json_metadata, slug, published,
            created_by_fk, changed_by_fk, uuid, is_managed_externally
        )
        VALUES (?, ?, ?, '{}', '', '', '{}', ?, 1, 1, 1, ?, 0)
        """,
        (now, now, DASHBOARD_TITLE, DASHBOARD_SLUG, uuid.uuid4().bytes),
    )
    return int(cur.lastrowid)


def _ensure_dashboard_slice(cur: sqlite3.Cursor, dashboard_id: int, chart_id: int) -> None:
    row = cur.execute(
        """
        SELECT id FROM dashboard_slices
        WHERE dashboard_id = ? AND slice_id = ?
        """,
        (dashboard_id, chart_id),
    ).fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO dashboard_slices (dashboard_id, slice_id) VALUES (?, ?)",
            (dashboard_id, chart_id),
        )


def _prune_dashboard_slices(
    cur: sqlite3.Cursor, dashboard_id: int, chart_ids: list[int]
) -> None:
    placeholders = ",".join("?" for _ in chart_ids)
    cur.execute(
        f"""
        DELETE FROM dashboard_slices
        WHERE dashboard_id = ?
          AND slice_id NOT IN ({placeholders})
        """,
        [dashboard_id, *chart_ids],
    )


def _dashboard_layout(chart_ids: list[int]) -> str:
    row_ids = []
    for idx in range(len(chart_ids)):
        row_ids.extend([f"ROW-{idx}-chart", f"ROW-{idx}-note"])
    position = {
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {
            "type": "GRID",
            "id": "GRID_ID",
            "children": ["HEADER_ID"] + row_ids,
        },
        "HEADER_ID": {
            "type": "HEADER",
            "id": "HEADER_ID",
            "meta": {"text": DASHBOARD_TITLE},
        },
    }

    for idx, chart in enumerate(CHARTS):
        chart_row_id = f"ROW-{idx}-chart"
        note_row_id = f"ROW-{idx}-note"
        chart_key = f"CHART-{idx + 1}"
        note_key = f"MARKDOWN-{idx + 1}"
        position[chart_row_id] = {
            "type": "ROW",
            "id": chart_row_id,
            "children": [chart_key],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        position[note_row_id] = {
            "type": "ROW",
            "id": note_row_id,
            "children": [note_key],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        position[chart_key] = {
            "type": "CHART",
            "id": chart_key,
            "children": [],
            "meta": {
                "chartId": chart_ids[idx],
                "sliceName": chart["slice_name"],
                "width": 12,
                "height": chart["height"],
            },
        }
        position[note_key] = {
            "type": "MARKDOWN",
            "id": note_key,
            "children": [],
            "meta": {
                "code": chart["description_markdown"],
                "width": 12,
                "height": 14,
            },
        }

    return json.dumps(position)


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    dashboard_id = _ensure_dashboard(cur)
    chart_ids = []
    for chart in CHARTS:
        chart_id = _ensure_chart(cur, chart)
        _ensure_dashboard_slice(cur, dashboard_id, chart_id)
        chart_ids.append(chart_id)
    _prune_dashboard_slices(cur, dashboard_id, chart_ids)

    cur.execute(
        """
        UPDATE dashboards
        SET dashboard_title = ?, slug = ?, published = 1, position_json = ?,
            changed_on = ?
        WHERE id = ?
        """,
        (DASHBOARD_TITLE, DASHBOARD_SLUG, _dashboard_layout(chart_ids), _now(), dashboard_id),
    )
    conn.commit()
    conn.close()
    print(f"Dashboard {dashboard_id} ready with charts {chart_ids}")


if __name__ == "__main__":
    main()
