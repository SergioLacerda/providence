"""Single-line Prometheus text format formatting helper."""

from __future__ import annotations


def _metric_line(
    name: str,
    value: float | int,
    labels: dict[str, str] | None = None,
) -> str:
    """Format a single metric line with optional label set.

    Follows Prometheus text format 0.0.4: metric_name{label="val",...} value

    Parameters
    ----------
    name:
        Metric name (e.g., "sdd_tokens_input_total").
    value:
        Numeric value (int or float).
    labels:
        Optional dict of label name -> label value. Values are escaped.

    Returns
    -------
    Single line of Prometheus text format, no trailing newline.
    """
    label_str = ""
    if labels:
        label_parts = []
        for k, v in sorted(labels.items()):
            # Escape: \, ", \n in label values
            escaped = v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            label_parts.append(f'{k}="{escaped}"')
        label_str = "{" + ",".join(label_parts) + "}"

    return f"{name}{label_str} {value}"
