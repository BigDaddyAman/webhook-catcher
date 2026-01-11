from fastapi import FastAPI, Request, HTTPException, Query, Body, Depends
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import sqlite3
import json
import httpx
import os
import csv
import base64
from io import StringIO
from urllib.parse import urlparse
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Webhook Catcher")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.filters["tojson"] = lambda value, indent=2: json.dumps(value, indent=indent)

SENSITIVE_HEADERS = {'authorization', 'cookie', 'x-api-key', 'api-key'}
security = HTTPBasic()

FORWARD_WEBHOOK_URL = os.getenv("FORWARD_WEBHOOK_URL")
FORWARD_WEBHOOK_TOKEN = os.getenv("FORWARD_WEBHOOK_TOKEN")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
FRONTEND_PASSWORD = os.getenv("FRONTEND_PASSWORD")

# Database configuration - single source of truth for DB path
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "webhooks.db")

def verify_admin_token(request: Request) -> bool:
    """Verify admin token from header or query parameter"""
    if not ADMIN_TOKEN or ADMIN_TOKEN.strip() == "":
        logger.info("No ADMIN_TOKEN set or empty, allowing access")
        return True  
    
    token = request.headers.get("X-Admin-Token")
    if token and token == ADMIN_TOKEN:
        logger.info("Valid admin token from header")
        return True
    
    token = request.query_params.get("admin_token")
    if token and token == ADMIN_TOKEN:
        logger.info("Valid admin token from query")
        return True
    
    logger.warning("Admin token verification failed")
    return False

def require_admin(request: Request):
    """Dependency to require admin authentication"""
    if not verify_admin_token(request):
        logger.warning("Admin access denied")
        raise HTTPException(
            status_code=401,
            detail="Admin token required. Set X-Admin-Token header or admin_token query parameter.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return True

def get_optional_credentials(request: Request):
    """Get HTTP Basic credentials if provided, or None if not."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Basic "):
        return None
    try:
        credentials = base64.b64decode(auth_header[6:]).decode("utf-8")
        username, _, password = credentials.partition(":")
        return HTTPBasicCredentials(username=username, password=password)
    except Exception:
        return None

def verify_frontend_password(request: Request):
    """Dependency to require frontend password via HTTP Basic Auth.

    If FRONTEND_PASSWORD is not set, access is allowed without authentication.
    Username can be anything; only the password is checked.
    """
    if not FRONTEND_PASSWORD or FRONTEND_PASSWORD.strip() == "":
        return True  # No protection if password not set

    credentials = get_optional_credentials(request)
    if credentials and credentials.password == FRONTEND_PASSWORD:
        return True

    raise HTTPException(
        status_code=401,
        detail="Invalid password",
        headers={"WWW-Authenticate": "Basic realm=\"Webhook Catcher\""}
    )

def sanitize_headers(headers):
    """Redact sensitive header values"""
    return {k: '***REDACTED***' if k.lower() in SENSITIVE_HEADERS else v 
            for k, v in headers.items()}

def validate_url(url: str) -> bool:
    """Basic URL validation to prevent SSRF"""
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except:
        return False

def try_json(data: str):
    """Safely parse JSON data"""
    try:
        return json.loads(data)
    except:
        return None

def extract_metadata(headers: dict) -> dict:
    """Extract useful metadata from headers"""
    return {
        "ip": headers.get("x-real-ip") or headers.get("x-forwarded-for") or "Unknown",
        "user_agent": headers.get("user-agent", "Unknown"),
        "source": headers.get("x-webhook-source", "Unknown"),
        "timestamp": headers.get("x-request-start", None)
    }

def format_timestamp(timestamp):
    """Format timestamp consistently with relative time"""
    try:
        dt = datetime.fromisoformat(timestamp)
        return {
            "iso": dt.isoformat(),
            "display": dt.strftime("%Y-%m-%d %H:%M:%S")
        }
    except:
        return {
            "iso": timestamp,
            "display": timestamp
        }

def init_db():
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS webhooks
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         timestamp TEXT,
         headers TEXT,
         body TEXT)
    ''')
    conn.commit()
    conn.close()

@app.on_event("startup")
async def startup_event():
    init_db()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, _: bool = Depends(verify_frontend_password)):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/healthz")
async def health_check():
    """Simple health check endpoint"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.close()
        return {"status": "ok", "admin_protected": bool(ADMIN_TOKEN and ADMIN_TOKEN.strip())}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "error", "error": str(e)}

async def forward_webhook(headers: dict, body: str, original_url: str) -> dict:
    """Forward webhook to configured endpoint if enabled"""
    if not FORWARD_WEBHOOK_URL:
        return {"status": "disabled", "message": "Forwarding not configured"}
    
    try:
        forward_headers = {
            "Content-Type": "application/json",
            "X-Forwarded-From": original_url,
            "X-Original-Timestamp": datetime.now().isoformat()
        }
        
        if FORWARD_WEBHOOK_TOKEN:
            forward_headers["Authorization"] = f"Bearer {FORWARD_WEBHOOK_TOKEN}"
        
        safe_headers = {k: v for k, v in headers.items() 
                       if k.lower() not in SENSITIVE_HEADERS}
        forward_headers.update({f"X-Original-{k}": v for k, v in safe_headers.items()})
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                FORWARD_WEBHOOK_URL,
                content=body,
                headers=forward_headers
            )
            
        return {
            "status": "success",
            "target_url": FORWARD_WEBHOOK_URL,
            "response_status": response.status_code,
            "response_time_ms": int(response.elapsed.total_seconds() * 1000)
        }
    except Exception as e:
        return {
            "status": "error",
            "target_url": FORWARD_WEBHOOK_URL,
            "error": str(e)
        }

@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.body()
        headers = dict(request.headers)
        
        body_str = ""
        if body:
            try:
                body_str = body.decode('utf-8')
            except UnicodeDecodeError:
                body_str = body.decode('utf-8', errors='replace')
        else:
            body_str = "{}"  
        
        parsed_json = None
        try:
            if body_str.strip():
                parsed_json = json.loads(body_str)
        except json.JSONDecodeError:
            pass
        
        print(f"Received webhook: {body_str}")
        print(f"Headers: {headers}")
        
        forward_task = None
        if FORWARD_WEBHOOK_URL:
            forward_task = asyncio.create_task(
                forward_webhook(headers, body_str, str(request.url))
            )
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        print("Inserting into database...")
        c.execute(
            "INSERT INTO webhooks (timestamp, headers, body) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), json.dumps(headers), body_str)
        )
        conn.commit()
        conn.close()
        print("Database insert complete")
        
        forwarding_result = None
        if forward_task:
            try:
                forwarding_result = await forward_task
                print(f"Forwarding result: {forwarding_result}")
            except Exception as e:
                print(f"Forwarding failed: {e}")
                forwarding_result = {"status": "error", "error": str(e)}
        
        response_data = {
            "status": "success", 
            "timestamp": datetime.now().isoformat(),
            "received_body": body_str,
            "is_json": parsed_json is not None,
            "forwarding": forwarding_result
        }
        
        return response_data
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}"
        )

def get_webhook_logs(offset: int = 0, limit: int = 20, search: str = None):
    """Helper function to fetch webhook logs"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        if search:
            search = search.strip()
            search_terms = [f"%{term}%" for term in search.split()]
            where_clauses = []
            params = []
            
            for term in search_terms:
                where_clauses.extend([
                    "body LIKE ?",
                    "headers LIKE ?",
                    "timestamp LIKE ?"
                ])
                params.extend([term, term, term])
            
            where_sql = " OR ".join(where_clauses)
            
            c.execute(f"SELECT COUNT(*) FROM webhooks WHERE {where_sql}", params)
            total_count = c.fetchone()[0]
            
            c.execute(f"""
                SELECT * FROM webhooks 
                WHERE {where_sql}
                ORDER BY timestamp DESC LIMIT ? OFFSET ?
            """, params + [limit, offset])
        else:
            c.execute("SELECT COUNT(*) FROM webhooks")
            total_count = c.fetchone()[0]
            c.execute("""
                SELECT * FROM webhooks 
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
        
        logs = [
            {
                "id": row[0],
                "timestamp": format_timestamp(row[1]),  
                "headers": sanitize_headers(json.loads(row[2])),
                "metadata": extract_metadata(json.loads(row[2])),
                "body": row[3],
                "parsed_body": try_json(row[3]),
                "matches": highlight_search_matches(row[3], search) if search else None
            } 
            for row in c.fetchall()
        ]
        
        return logs, total_count, (offset + len(logs)) < total_count
        
    finally:
        conn.close()

def highlight_search_matches(text: str, search: str) -> list:
    """Find and highlight search matches in text"""
    if not search:
        return []
    
    matches = []
    try:
        search_terms = search.lower().split()
        text_lower = text.lower()
        
        for term in search_terms:
            start = 0
            while True:
                pos = text_lower.find(term, start)
                if pos == -1:
                    break
                    
                context_start = max(0, pos - 20)
                context_end = min(len(text), pos + len(term) + 20)
                
                matches.append({
                    "term": term,
                    "context": f"...{text[context_start:context_end]}..."
                })
                
                start = pos + len(term)
                
        return matches
    except:
        return []

@app.get("/logs/view", response_class=HTMLResponse)
async def view_logs(request: Request, _: bool = Depends(verify_frontend_password)):
    """Full logs page view"""
    logs, total_count, has_more = get_webhook_logs(limit=10)  
    return templates.TemplateResponse("logs.html", {
        "request": request,
        "logs": logs,
        "count": len(logs),
        "total_count": total_count,
        "has_more": has_more,
        "offset": 0,
        "limit": 10
    })

@app.get("/logs")
async def get_logs(
    request: Request,
    search: str = Query(None),
    offset: int = Query(0),
    limit: int = Query(20),
    _: bool = Depends(verify_frontend_password)
):
    """Partial logs view for HTMX updates"""
    try:
        logs, total_count, has_more = get_webhook_logs(offset, limit, search)
        print(f"Retrieved logs: count={len(logs)}, total={total_count}")  
        
        template_data = {
            "request": request,
            "logs": logs,
            "count": total_count,
            "total_count": total_count,
            "has_more": has_more,
            "offset": offset,
            "limit": limit,
            "empty": len(logs) == 0
        }

        if "application/json" in request.headers.get("accept", ""):
            return {
                "logs": logs,
                "count": total_count,
                "total_count": total_count,
                "has_more": has_more,
                "empty": len(logs) == 0
            }
        
        return templates.TemplateResponse("logs_list.html", template_data)
    except Exception as e:
        print(f"Error retrieving logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export")
async def export_logs(request: Request, format: str = Query("json", enum=["json", "csv"]), _: bool = Depends(verify_frontend_password)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM webhooks ORDER BY timestamp DESC")
    logs = [{"id": row[0], "timestamp": row[1], "headers": json.loads(row[2]), "body": row[3]} 
            for row in c.fetchall()]
    conn.close()

    if format == "csv":
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["id", "timestamp", "headers", "body"])
        writer.writeheader()
        writer.writerows(logs)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=webhooks.csv"}
        )
    
    return Response(
        content=json.dumps(logs, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={
            "Content-Disposition": "attachment; filename=webhooks.json",
            "X-Total-Count": str(len(logs))
        }
    )

@app.post("/test")
async def test_webhook(request: Request):
    try:
        body = await request.body()
        
        if not body or body == b'{}':
            payload = {
                "event": "test",
                "timestamp": datetime.now().isoformat(),
                "message": "Test webhook payload"
            }
        else:
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON payload. Example: {'event': 'test', 'message': 'Hello'}"
                )

        base_url = str(request.base_url)
        if base_url.startswith('http:'):
            base_url = 'https:' + base_url[5:]
        webhook_url = base_url + "webhook"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
        return {
            "status": "sent", 
            "response_status": response.status_code,
            "url": webhook_url,
            "payload": payload
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to send test webhook: {str(e)}"
        )

@app.post("/replay/{webhook_id}")
async def replay_webhook(webhook_id: int, request: Request, target_url: str = Query(None)):
    """Replay webhook with optional admin protection - accepts target_url from query or body"""
    if ADMIN_TOKEN and not verify_admin_token(request):
        raise HTTPException(
            status_code=401,
            detail="Admin token required for replay operations",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not target_url:
        try:
            body = await request.body()
            if body:
                body_data = json.loads(body)
                target_url = body_data.get("target_url")
        except (json.JSONDecodeError, AttributeError):
            pass
    
    if not target_url:
        raise HTTPException(
            status_code=400,
            detail="target_url is required. Provide it as a query parameter (?target_url=...) or in request body as JSON {\"target_url\": \"...\"}"
        )
    
    if not validate_url(target_url):
        raise HTTPException(
            status_code=400,
            detail="Invalid target URL. Must be http(s)://..."
        )
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT headers, body FROM webhooks WHERE id = ?", (webhook_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Webhook {webhook_id} not found")
        
    headers = json.loads(row[0])
    body = row[1]
    
    replay_headers = {k: v for k, v in headers.items() 
                     if k.lower() not in ['host', 'content-length', 'connection']}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                target_url, 
                headers=replay_headers, 
                content=body
            )
        
        return {
            "status": "replayed", 
            "response_status": response.status_code,
            "target_url": target_url,
            "webhook_id": webhook_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to replay webhook: {str(e)}"
        )

@app.post("/clear")
async def clear_logs(request: Request):
    """Clear logs with optional admin protection"""
    if ADMIN_TOKEN and not verify_admin_token(request):
        raise HTTPException(
            status_code=401,
            detail="Admin token required for clear operations",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM webhooks")
    conn.commit()
    conn.close()
    return {"status": "cleared"}

@app.get("/config")
async def get_config():
    """Get current configuration status"""
    return {
        "forwarding_enabled": bool(FORWARD_WEBHOOK_URL),
        "forwarding_url": FORWARD_WEBHOOK_URL if FORWARD_WEBHOOK_URL else None,
        "authentication_enabled": bool(FORWARD_WEBHOOK_TOKEN),
        "admin_protection_enabled": bool(ADMIN_TOKEN and ADMIN_TOKEN.strip()),
        "total_webhooks": get_total_webhook_count()
    }

def get_total_webhook_count():
    """Get total count of webhooks received"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM webhooks")
        count = c.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

@app.get("/webhooks")
async def list_webhooks(request: Request, limit: int = Query(50), _: bool = Depends(verify_frontend_password)):
    """List available webhooks for replay testing"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM webhooks")
    total_count = c.fetchone()[0]
    
    c.execute("""
        SELECT id, timestamp, body, headers 
        FROM webhooks 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (limit,))
    
    webhooks = []
    for row in c.fetchall():
        webhook_id, timestamp, body, headers = row
        
        body_preview = body[:100] + "..." if len(body) > 100 else body
        
        headers_dict = json.loads(headers)
        content_type = headers_dict.get("content-type", "unknown")
        
        webhooks.append({
            "id": webhook_id,
            "timestamp": timestamp,
            "body_preview": body_preview,
            "content_type": content_type,
            "size_bytes": len(body)
        })
    
    conn.close()
    
    return {
        "webhooks": webhooks,
        "count": len(webhooks),
        "total_count": total_count
    }
