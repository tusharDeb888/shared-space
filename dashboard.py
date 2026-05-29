"""
dashboard.py — A/B Testing Observability Dashboard

Streamlit + Plotly dashboard that races the zero-copy Arrow IPC pipeline
against a traditional JSON/REST baseline and visualizes the results.

Usage:
    streamlit run dashboard.py --server.port 8501
"""

import time

import plotly.graph_objects as go
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PRODUCER_URL = "http://localhost:8000"

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Zero-Copy IPC — A/B Benchmark Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — dark, premium aesthetic
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif;
    }

    .main-header {
        text-align: center;
        padding: 1.5rem 0 0.5rem 0;
    }
    .main-header h1 {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #00d2ff, #7b2ff7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .main-header p {
        font-size: 1rem;
        color: #8899aa;
        font-weight: 400;
    }

    .kpi-card {
        background: linear-gradient(145deg, #1a1f2e 0%, #0f1318 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .kpi-card .label {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #667788;
        margin-bottom: 0.5rem;
    }
    .kpi-card .value {
        font-size: 2.6rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    .kpi-card .unit {
        font-size: 0.9rem;
        color: #889aab;
        font-weight: 400;
    }

    .kpi-json .value { color: #ff6b6b; }
    .kpi-arrow .value { color: #51cf66; }
    .kpi-speedup .value {
        background: linear-gradient(135deg, #ffd43b, #ff922b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #ccd6e0;
        margin: 2rem 0 0.8rem 0;
        padding-bottom: 0.4rem;
        border-bottom: 2px solid rgba(123, 47, 247, 0.3);
    }

    .stSidebar [data-testid="stSidebarContent"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## Benchmark Configuration")
    st.markdown("---")

    payload_size = st.slider(
        "📐 Payload Size (Vector Embeddings)",
        min_value=10_000,
        max_value=1_000_000,
        value=100_000,
        step=10_000,
        format="%d",
        help="Number of float32 elements to test with",
    )

    iterations = st.radio(
        "🔄 Iterations (averaged)",
        options=[1, 3, 5],
        index=0,
        horizontal=True,
    )

    st.markdown("---")
    run_benchmark = st.button(
        "🚀 Run Benchmark Race",
        type="primary",
        use_container_width=True,
    )

    st.markdown("---")
    st.markdown("#### 📊 Payload Info")
    payload_kb = payload_size * 4 / 1024
    payload_mb = payload_kb / 1024
    st.markdown(f"- **Elements:** `{payload_size:,}`")
    st.markdown(f"- **Raw size:** `{payload_kb:,.1f} KB` ({payload_mb:.2f} MB)")
    st.markdown(f"- **Dtype:** `float32`")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="main-header">
    <h1>⚡ Zero-Copy IPC vs JSON/REST — Live A/B Benchmark</h1>
    <p>Apache Arrow Shared Memory &nbsp;│&nbsp; POSIX mmap &nbsp;│&nbsp; PyTorch Inference Pipeline</p>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helper: run a single benchmark call
# ---------------------------------------------------------------------------
def _run_single(endpoint: str, size: int) -> dict:
    """Call a benchmark endpoint and return the JSON response."""
    resp = requests.post(
        f"{PRODUCER_URL}/{endpoint}",
        json={"size": size},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()


def run_full_benchmark(size: int, iters: int) -> tuple[list[dict], list[dict]]:
    """Run both pipelines for `iters` iterations and return (arrow_results, json_results)."""
    arrow_results = []
    json_results = []

    for _ in range(iters):
        arrow_results.append(_run_single("benchmark_arrow", size))
        json_results.append(_run_single("benchmark_json", size))

    return arrow_results, json_results


def avg(results: list[dict], key: str) -> float:
    vals = [r[key] for r in results]
    return sum(vals) / len(vals)


# ---------------------------------------------------------------------------
# Main: Run benchmark and render results
# ---------------------------------------------------------------------------
if run_benchmark:
    # Health check
    try:
        requests.get(f"{PRODUCER_URL}/health", timeout=5)
    except requests.ConnectionError:
        st.error("❌ **Producer not reachable** at `localhost:8000`. Start the backend first.")
        st.stop()

    try:
        requests.get("http://localhost:8001/health", timeout=5)
    except requests.ConnectionError:
        st.error("❌ **Consumer not reachable** at `localhost:8001`. Start the consumer first.")
        st.stop()

    # Progress bar
    progress = st.progress(0, text="🏁 Racing pipelines...")

    try:
        arrow_results, json_results = [], []
        for i in range(iterations):
            progress.progress(
                int((i / iterations) * 100),
                text=f"🏎️ Iteration {i + 1}/{iterations}..."
            )
            a = _run_single("benchmark_arrow", payload_size)
            j = _run_single("benchmark_json", payload_size)
            arrow_results.append(a)
            json_results.append(j)

        progress.progress(100, text="✅ Benchmark complete!")
        time.sleep(0.5)
        progress.empty()

    except Exception as exc:
        st.error(f"❌ Benchmark failed: {exc}")
        st.stop()

    # Compute averages
    arrow_e2e = avg(arrow_results, "total_e2e_ms")
    json_e2e = avg(json_results, "total_e2e_ms")
    speedup = json_e2e / arrow_e2e if arrow_e2e > 0 else float("inf")

    # -------------------------------------------------------------------
    # KPI Cards
    # -------------------------------------------------------------------
    st.markdown('<div class="section-title">📈 Key Performance Indicators</div>', unsafe_allow_html=True)

    k1, k2, k3 = st.columns(3)

    with k1:
        st.markdown(f"""
        <div class="kpi-card kpi-json">
            <div class="label">Traditional JSON/REST</div>
            <div class="value">{json_e2e:,.2f}</div>
            <div class="unit">milliseconds (E2E)</div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
        <div class="kpi-card kpi-arrow">
            <div class="label">Zero-Copy Arrow IPC</div>
            <div class="value">{arrow_e2e:,.2f}</div>
            <div class="unit">milliseconds (E2E)</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        st.markdown(f"""
        <div class="kpi-card kpi-speedup">
            <div class="label">Arrow Speedup Factor</div>
            <div class="value">{speedup:,.1f}×</div>
            <div class="unit">faster than JSON/REST</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------------
    # Latency Breakdown Bar Chart
    # -------------------------------------------------------------------
    st.markdown('<div class="section-title">⏱️ Latency Breakdown Comparison</div>', unsafe_allow_html=True)

    # Arrow breakdown
    arrow_ser = avg(arrow_results, "serialization_ms")
    arrow_write = avg(arrow_results, "write_ms")
    arrow_c_read = avg(arrow_results, "consumer_read_ms")
    arrow_c_conv = avg(arrow_results, "consumer_convert_ms")

    # JSON breakdown
    json_ser = avg(json_results, "json_serialize_ms")
    json_http = avg(json_results, "http_transfer_ms")
    json_c_deser = avg(json_results, "consumer_deserialize_ms")
    json_c_conv = avg(json_results, "consumer_convert_ms")

    fig_latency = go.Figure()

    # Arrow bars
    fig_latency.add_trace(go.Bar(
        name="Arrow: Serialize",
        x=["Arrow IPC (Zero-Copy)"],
        y=[arrow_ser],
        marker_color="#2ecc71",
        text=[f"{arrow_ser:.2f}ms"],
        textposition="auto",
    ))
    fig_latency.add_trace(go.Bar(
        name="Arrow: SHM Write",
        x=["Arrow IPC (Zero-Copy)"],
        y=[arrow_write],
        marker_color="#27ae60",
        text=[f"{arrow_write:.2f}ms"],
        textposition="auto",
    ))
    fig_latency.add_trace(go.Bar(
        name="Arrow: Consumer Read",
        x=["Arrow IPC (Zero-Copy)"],
        y=[arrow_c_read],
        marker_color="#1abc9c",
        text=[f"{arrow_c_read:.2f}ms"],
        textposition="auto",
    ))
    fig_latency.add_trace(go.Bar(
        name="Arrow: Consumer Convert",
        x=["Arrow IPC (Zero-Copy)"],
        y=[arrow_c_conv],
        marker_color="#16a085",
        text=[f"{arrow_c_conv:.2f}ms"],
        textposition="auto",
    ))

    # JSON bars
    fig_latency.add_trace(go.Bar(
        name="JSON: Serialize",
        x=["Traditional JSON/REST"],
        y=[json_ser],
        marker_color="#e74c3c",
        text=[f"{json_ser:.2f}ms"],
        textposition="auto",
    ))
    fig_latency.add_trace(go.Bar(
        name="JSON: HTTP Transfer",
        x=["Traditional JSON/REST"],
        y=[json_http],
        marker_color="#c0392b",
        text=[f"{json_http:.2f}ms"],
        textposition="auto",
    ))
    fig_latency.add_trace(go.Bar(
        name="JSON: Consumer Deserialize",
        x=["Traditional JSON/REST"],
        y=[json_c_deser],
        marker_color="#e67e22",
        text=[f"{json_c_deser:.2f}ms"],
        textposition="auto",
    ))
    fig_latency.add_trace(go.Bar(
        name="JSON: Consumer Convert",
        x=["Traditional JSON/REST"],
        y=[json_c_conv],
        marker_color="#d35400",
        text=[f"{json_c_conv:.2f}ms"],
        textposition="auto",
    ))

    fig_latency.update_layout(
        barmode="stack",
        template="plotly_dark",
        height=450,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=13),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.35,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        yaxis_title="Latency (ms)",
        margin=dict(l=50, r=20, t=30, b=100),
    )

    st.plotly_chart(fig_latency, use_container_width=True)

    # -------------------------------------------------------------------
    # Memory Footprint Comparison
    # -------------------------------------------------------------------
    st.markdown('<div class="section-title">💾 Memory Footprint Comparison</div>', unsafe_allow_html=True)

    arrow_bytes = arrow_results[-1].get("arrow_bytes", 0)
    json_bytes = json_results[-1].get("json_bytes", 0)

    arrow_kb = arrow_bytes / 1024
    json_kb = json_bytes / 1024
    mem_ratio = json_bytes / arrow_bytes if arrow_bytes > 0 else 0

    col_mem1, col_mem2 = st.columns([2, 1])

    with col_mem1:
        fig_mem = go.Figure()
        fig_mem.add_trace(go.Bar(
            name="Arrow IPC Buffer",
            x=["Memory Footprint"],
            y=[arrow_kb],
            marker_color="#51cf66",
            text=[f"{arrow_kb:,.1f} KB"],
            textposition="auto",
            width=0.3,
        ))
        fig_mem.add_trace(go.Bar(
            name="JSON String",
            x=["Memory Footprint"],
            y=[json_kb],
            marker_color="#ff6b6b",
            text=[f"{json_kb:,.1f} KB"],
            textposition="auto",
            width=0.3,
        ))
        fig_mem.update_layout(
            barmode="group",
            template="plotly_dark",
            height=350,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", size=13),
            yaxis_title="Size (KB)",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.25,
                xanchor="center",
                x=0.5,
            ),
            margin=dict(l=50, r=20, t=20, b=80),
        )
        st.plotly_chart(fig_mem, use_container_width=True)

    with col_mem2:
        st.markdown(f"""
        <div class="kpi-card" style="margin-top: 1rem;">
            <div class="label">JSON Bloat Factor</div>
            <div class="value kpi-speedup" style="
                background: linear-gradient(135deg, #ff6b6b, #ff922b);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-size: 2.4rem;
            ">{mem_ratio:.1f}×</div>
            <div class="unit">larger than Arrow buffer</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="kpi-card" style="margin-top: 1rem;">
            <div class="label">Space Saved</div>
            <div class="value" style="color: #51cf66; font-size: 2.2rem;">
                {(json_kb - arrow_kb):,.0f} KB
            </div>
            <div class="unit">({(1 - arrow_bytes/json_bytes)*100:.0f}% reduction)</div>
        </div>
        """, unsafe_allow_html=True)

    # -------------------------------------------------------------------
    # Raw Data Table
    # -------------------------------------------------------------------
    st.markdown('<div class="section-title">📋 Raw Iteration Data</div>', unsafe_allow_html=True)

    col_t1, col_t2 = st.columns(2)

    with col_t1:
        st.markdown("**Arrow IPC (Zero-Copy)**")
        table_data_arrow = []
        for i, r in enumerate(arrow_results, 1):
            table_data_arrow.append({
                "Iter": i,
                "Serialize (ms)": round(r["serialization_ms"], 3),
                "SHM Write (ms)": round(r["write_ms"], 3),
                "Consumer (ms)": round(r["consumer_total_ms"], 3),
                "E2E (ms)": round(r["total_e2e_ms"], 3),
            })
        st.dataframe(table_data_arrow, use_container_width=True, hide_index=True)

    with col_t2:
        st.markdown("**Traditional JSON/REST**")
        table_data_json = []
        for i, r in enumerate(json_results, 1):
            table_data_json.append({
                "Iter": i,
                "JSON Ser. (ms)": round(r["json_serialize_ms"], 3),
                "HTTP Xfer (ms)": round(r["http_transfer_ms"], 3),
                "Consumer (ms)": round(r["consumer_total_ms"], 3),
                "E2E (ms)": round(r["total_e2e_ms"], 3),
            })
        st.dataframe(table_data_json, use_container_width=True, hide_index=True)

else:
    # -------------------------------------------------------------------
    # Landing state (no benchmark run yet)
    # -------------------------------------------------------------------
    st.markdown("---")

    lc1, lc2, lc3 = st.columns(3)
    with lc1:
        st.markdown("""
        ### Traditional Pipeline
        ```
        Producer → json.dumps()
               → HTTP POST body
               → json.loads()
               → np.array(copy)
               → torch.Tensor
        ```
        **Problem:** O(N) serialization, full memory copy, string bloat.
        """)
    with lc2:
        st.markdown("""
        ### Zero-Copy Pipeline
        ```
        Producer → pa.array()
               → Arrow IPC → mmap
               → pa.OSFile read
               → .to_numpy(zero_copy_only=True)
               → torch.from_numpy()
        ```
        **Advantage:** O(1) serialization, zero memory copies.
        """)
    with lc3:
        st.markdown("""
        ### How to Use
        1. Set **Payload Size** in the sidebar
        2. Select **Iterations** for averaging
        3. Click **Run Benchmark Race**
        4. Watch the results appear live!

        *Backend must be running on ports 8000 & 8001.*
        """)

    st.markdown("---")
    st.info("**Configure payload size in the sidebar and click 'Run Benchmark Race' to start.**")
