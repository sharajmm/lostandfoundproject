from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.openapi.utils import get_openapi
from jose import JWTError, jwt
from db import get_connection
from models import UserLogin
from auth import create_access_token
from datetime import datetime
from fastapi.responses import RedirectResponse



app = FastAPI()

# Mount static and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SECRET_KEY = "your-strong-secret-key"
ALGORITHM = "HS256"

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/login")
# -------------------- LOGIN --------------------
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login-html", response_class=HTMLResponse)
def login_html_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...)
):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    conn.close()

    # Handle all three validation checks clearly
    if not user:
        error = "❌ Username not found."
    elif user["password"] != password:
        error = "❌ Incorrect password."
    elif user["role"] != role:
        error = f"❌ Incorrect role selected for this user."
    else:
        # If everything is fine: create token & redirect
        token = create_access_token({"sub": user["username"], "role": user["role"]})
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(key="access_token", value=token, httponly=True)
        return response

    # If login fails, return login page with error
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error
    })
# -------------------- DASHBOARD --------------------
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=302)

    try:
        user_data = jwt.decode(token, "your-strong-secret-key", algorithms=["HS256"])
    except JWTError:
        return RedirectResponse(url="/login", status_code=302)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT full_name, department FROM users_info WHERE username = %s", (user_data["sub"],))
    user_info = cursor.fetchone()
    conn.close()

    full_name = user_info["full_name"] if user_info else user_data["sub"]
    department = user_info["department"] if user_info else "Department Not Found"

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "username": user_data["sub"],
        "role": user_data["role"],
        "full_name": full_name,
        "department": department
    })

# -------------------- REPORT LOST ITEM --------------------
@app.get("/report", response_class=HTMLResponse)
def report_page(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("report.html", {"request": request})

@app.post("/report")
def report_item(
    request: Request,
    item_name: str = Form(...),
    description: str = Form(...),
    location: str = Form(...),
    date_reported: str = Form(...),
    status: str = Form(...)
):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)

    try:
        user = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse("/login", status_code=302)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO items (item_name, description, location, date_reported, status, reported_by)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (item_name, description, location, date_reported, status, user["sub"]))
    conn.commit()
    conn.close()

    return RedirectResponse("/items-html", status_code=302)


# -------------------- VIEW ALL ITEMS --------------------
from fastapi import Query

@app.get("/items-html", response_class=HTMLResponse)
def view_items(
    request: Request,
    q: str = Query(default=None),
    status_filter: str = Query(default=None),
    sort: str = Query(default="date")
):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)

    try:
        user = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse("/login", status_code=302)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Base query
    base_query = """
        SELECT i.*, u.full_name, u.email, u.department
        FROM items i
        LEFT JOIN users_info u ON i.reported_by = u.username
    """
    conditions = []
    params = []

    # Search (q)
    if q:
        conditions.append("(i.item_name LIKE %s OR i.location LIKE %s OR i.status LIKE %s)")
        search_term = f"%{q}%"
        params.extend([search_term, search_term, search_term])

    # Status filter
    if status_filter:
        conditions.append("i.status = %s")
        params.append(status_filter)

    # Combine WHERE conditions
    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    # Sorting
    if sort == "status":
        base_query += " ORDER BY i.status ASC"
    elif sort == "location":
        base_query += " ORDER BY i.location ASC"
    else:  # default to date
        base_query += " ORDER BY i.date_reported DESC"

    cursor.execute(base_query, params)
    items = cursor.fetchall()
    conn.close()

    for item in items:
        item["can_edit"] = item["reported_by"] == user["sub"] or user["role"] == "admin"

    return templates.TemplateResponse(
        "items.html",
        {
            "request": request,
            "items": items,
            "q": q,
            "status_filter": status_filter,
            "sort": sort
        }
    )

# -------------------- UPDATE ITEM --------------------
@app.get("/update/{sno}", response_class=HTMLResponse)
def update_item_form(request: Request, sno: int):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)

    try:
        user = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse("/login", status_code=302)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM items WHERE sno = %s", (sno,))
    item = cursor.fetchone()
    conn.close()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item["reported_by"] != user["sub"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    return templates.TemplateResponse("update.html", {
        "request": request,
        "item": item
    })

@app.post("/update/{sno}")
def update_item(
    sno: int,
    request: Request,
    item_name: str = Form(...),
    description: str = Form(...),
    location: str = Form(...),
    date_reported: str = Form(...),
    status: str = Form(...)
):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)

    try:
        user = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse("/login", status_code=302)

    conn = get_connection()
    cursor = conn.cursor()
    # Make sure the user is authorized
    cursor.execute("SELECT reported_by FROM items WHERE sno = %s", (sno,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        raise HTTPException(status_code=404, detail="Item not found")

    reported_by = result[0]
    if reported_by != user["sub"] and user["role"] != "admin":
        conn.close()
        raise HTTPException(status_code=403, detail="Not authorized")

    # Perform the update
    cursor.execute("""
        UPDATE items
        SET item_name = %s, description = %s, location = %s, date_reported = %s, status = %s
        WHERE sno = %s
    """, (item_name, description, location, date_reported, status, sno))

    conn.commit()
    conn.close()

    return RedirectResponse("/items-html", status_code=302)

# -------------------- DELETE ITEM --------------------
@app.post("/delete/{sno}")
def delete_item(sno: int, request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)

    try:
        user = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse("/login", status_code=302)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items WHERE sno=%s AND (reported_by=%s OR %s='admin')", (sno, user["sub"], user["role"]))
    conn.commit()
    conn.close()
    return RedirectResponse("/items-html", status_code=302)

# -------------------- SEARCH --------------------
@app.get("/search", response_class=HTMLResponse)
def search(request: Request, query: str = "", date_lost: str = "", category: str = ""):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse("/login", status_code=302)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    q = "SELECT * FROM items WHERE 1=1"
    params = []

    if query:
        q += " AND (item_name LIKE %s OR location LIKE %s)"
        params.extend([f"%{query}%", f"%{query}%"])
    if date_lost:
        q += " AND date_reported = %s"
        params.append(date_lost)
    if category:
        q += " AND status = %s"
        params.append(category)

    cursor.execute(q, tuple(params))
    results = cursor.fetchall()
    conn.close()

    return templates.TemplateResponse("search.html", {"request": request, "results": results})

# -------------------- MARK AS RETURNED --------------------
@app.get("/mark-returned/{sno}", response_class=HTMLResponse)
def mark_returned_form(request: Request, sno: int):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse("/login", status_code=302)

    return templates.TemplateResponse("mark_returned.html", {"request": request, "sno": sno})

@app.post("/mark-returned/{sno}")
def mark_returned(sno: int, request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse("/login", status_code=302)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE items SET status='Returned' WHERE sno=%s", (sno,))
    conn.commit()
    conn.close()
    return RedirectResponse("/items-html", status_code=302)

# -------------------- MY ITEMS --------------------
@app.get("/my-items", response_class=HTMLResponse)
def my_items(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)
    try:
        user = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse("/login", status_code=302)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM items WHERE reported_by=%s ORDER BY date_reported DESC", (user["sub"],))
    items = cursor.fetchall()
    conn.close()
    return templates.TemplateResponse("my_items.html", {"request": request, "items": items})


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response