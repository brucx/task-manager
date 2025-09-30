"""Simple metrics dashboard."""
import logging
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
from src.monitoring.metrics import task_metrics

logger = logging.getLogger(__name__)

dashboard_app = FastAPI(title="Task Manager Metrics")


@dashboard_app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=task_metrics.export_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@dashboard_app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Simple HTML dashboard."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Task Manager Dashboard</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 40px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                border-bottom: 2px solid #4CAF50;
                padding-bottom: 10px;
            }
            .section {
                margin: 30px 0;
            }
            .metric-card {
                background-color: #f9f9f9;
                padding: 20px;
                margin: 10px 0;
                border-radius: 4px;
                border-left: 4px solid #4CAF50;
            }
            .metric-title {
                font-weight: bold;
                color: #666;
                margin-bottom: 10px;
            }
            .metric-value {
                font-size: 24px;
                color: #333;
            }
            a {
                color: #4CAF50;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
        </style>
        <script>
            // Auto-refresh every 5 seconds
            setTimeout(() => location.reload(), 5000);
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Task Manager Dashboard</h1>

            <div class="section">
                <h2>📊 Metrics</h2>
                <p>View raw Prometheus metrics at <a href="/metrics">/metrics</a></p>
                <p>This dashboard auto-refreshes every 5 seconds.</p>
            </div>

            <div class="section">
                <h2>🎮 GPU Workers</h2>
                <div class="metric-card">
                    <div class="metric-title">GPU Configuration</div>
                    <div class="metric-value">16 GPUs × 2 tasks = 32 parallel slots</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">Models Preloaded</div>
                    <div class="metric-value">General, Portrait, Landscape (1GB each)</div>
                </div>
            </div>

            <div class="section">
                <h2>⚙️ Worker Pools</h2>
                <div class="metric-card">
                    <div class="metric-title">IO Workers</div>
                    <div class="metric-value">20 workers (download/upload)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">CPU Workers</div>
                    <div class="metric-value">10 classify + 10 encode = 20 workers</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">GPU Workers</div>
                    <div class="metric-value">32 workers (16 containers × 2 concurrency)</div>
                </div>
            </div>

            <div class="section">
                <h2>🔧 Configuration</h2>
                <div class="metric-card">
                    <div class="metric-title">Queue Timeout</div>
                    <div class="metric-value">30 seconds (with admin notification)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">Shared Storage</div>
                    <div class="metric-value">/tmp/shared/tasks</div>
                </div>
            </div>

            <div class="section">
                <h2>📖 API Endpoints</h2>
                <ul>
                    <li><code>POST /api/v1/tasks</code> - Submit task</li>
                    <li><code>GET /api/v1/tasks/{task_id}</code> - Get task status</li>
                    <li><code>GET /metrics</code> - Prometheus metrics</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@dashboard_app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "task-manager"}