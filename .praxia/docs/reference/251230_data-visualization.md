# Data Visualization

Praxis provides built-in data visualization for protocol outputs using Plotly.

## Overview

After a protocol runs, any returned data can be visualized:

- **Time series**: Measurements over time
- **Plate heatmaps**: Well-by-well data
- **Scatter plots**: Correlations and distributions
- **Bar charts**: Categorical comparisons

## Accessing Visualizations

### From Run History

1. Navigate to **Protocols**
2. Click on a protocol
3. Select a run from the **History** tab
4. Click **View Data**

### From Dashboard

1. Navigate to **Home**
2. Find recent runs in the activity feed
3. Click the chart icon to visualize

## Chart Types

### Time Series

For measurements collected over time:

```python
@protocol(...)
async def kinetic_assay(ctx):
    readings = []
    for t in range(0, 3600, 60):  # Every minute for 1 hour
        await asyncio.sleep(60)
        reading = await reader.measure(plate["A1:A12"])
        readings.append({
            "time": t,
            "values": reading
        })

    return {"timeseries": readings}
```

The visualization shows:
- X-axis: Time
- Y-axis: Measurement values
- Multiple traces for different wells/conditions

### Plate Heatmaps

For well-by-well data:

```python
@protocol(...)
async def endpoint_assay(ctx):
    readings = await reader.measure_all(plate)

    return {
        "heatmap": {
            "data": readings,  # 2D array [8][12]
            "plate_format": 96
        }
    }
```

The visualization shows:
- 8x12 grid (or 16x24 for 384-well)
- Color intensity for values
- Hover for exact values

### Scatter Plots

For correlations:

```python
@protocol(...)
async def correlation_study(ctx):
    method_a = await reader_a.measure_all(plate)
    method_b = await reader_b.measure_all(plate)

    return {
        "scatter": {
            "x": method_a.flatten(),
            "y": method_b.flatten(),
            "labels": generate_well_labels(96)
        }
    }
```

### Bar Charts

For categorical data:

```python
@protocol(...)
async def sample_comparison(ctx):
    return {
        "bars": {
            "categories": ["Control", "Treatment A", "Treatment B"],
            "values": [1.2, 3.4, 2.8],
            "errors": [0.1, 0.3, 0.2]
        }
    }
```

## Customizing Charts

### In the UI

- **Zoom**: Click and drag to zoom, double-click to reset
- **Pan**: Shift + drag to pan
- **Export**: Download as PNG or SVG
- **Traces**: Click legend to show/hide traces

### In Protocol Code

Return Plotly-compatible configurations:

```python
return {
    "chart": {
        "data": [
            {
                "type": "scatter",
                "x": times,
                "y": values,
                "name": "Sample A",
                "mode": "lines+markers"
            }
        ],
        "layout": {
            "title": "Growth Curve",
            "xaxis": {"title": "Time (min)"},
            "yaxis": {"title": "OD600"},
            "template": "plotly_dark"
        }
    }
}
```

## Data Export

### From Visualization

1. Click the **Download** icon
2. Choose format:
   - **CSV**: Raw data
   - **JSON**: Structured data
   - **PNG/SVG**: Chart image

### Via API

```bash
# Get run outputs as JSON
curl http://localhost:8000/api/v1/outputs?run_id=xyz

# Get specific output
curl http://localhost:8000/api/v1/outputs/abc123
```

## Protocol Output Best Practices

### 1. Structure Your Data

```python
# Good: Structured and labeled
return {
    "readings": {
        "raw": raw_values,
        "normalized": normalized_values,
        "blanked": blanked_values
    },
    "metadata": {
        "plate_id": plate.accession_id,
        "read_time": datetime.now().isoformat(),
        "settings": reader_settings
    }
}

# Bad: Flat and unlabeled
return values  # What are these?
```

### 2. Include Metadata

```python
return {
    "data": measurements,
    "units": "OD600",
    "protocol_params": ctx.params,
    "timestamp": datetime.now().isoformat()
}
```

### 3. Use Standard Formats

For plate data, use consistent well ordering:

```python
# Row-major order (A1, A2, ... A12, B1, B2, ...)
data_2d = [[row_a], [row_b], ...]  # 8 rows x 12 cols

# Or with well labels
data_labeled = {
    "A1": 0.123,
    "A2": 0.234,
    ...
}
```

### 4. Emit During Execution

For real-time visualization:

```python
async def my_protocol(ctx):
    for i, timepoint in enumerate(timepoints):
        reading = await measure()

        # Emit for live chart
        ctx.emit_data({
            "type": "timeseries_point",
            "time": timepoint,
            "value": reading
        })

        await asyncio.sleep(interval)
```

## Browser Mode Data

In browser mode, protocols generate deterministic sample data:

```python
# Demo mode detection
if ctx.is_browser:
    # Return sample data for visualization testing
    return generate_sample_growth_curve()
```

This allows testing the visualization pipeline without real experiments.
