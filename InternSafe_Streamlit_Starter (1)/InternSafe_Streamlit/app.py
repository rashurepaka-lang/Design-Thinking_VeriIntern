import streamlit as st
import sqlite3
import hashlib
import secrets
import string
import re
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path

# ============================================================
# InternSafe — Verify Before You Apply
# Streamlit + SQLite, single-file demo application
# ============================================================

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "internsafe.db"

st.set_page_config(page_title="InternSafe | Verify Before You Apply",
                   page_icon="🛡️", layout="wide")

# ---------- Styling ----------
st.markdown("""
<style>
:root { --ink:#172033; --muted:#64748b; --blue:#3157d5; }
.block-container {padding-top: 1.5rem; max-width: 1200px;}
.hero {padding: 1.6rem 1.8rem; border-radius: 18px;
       background: linear-gradient(120deg,#14213d,#3157d5); color:white; margin-bottom:1.2rem;}
.hero h1 {color:white; margin:0 0 .35rem 0;}
.hero p {color:#e7edff; margin:0;}
.small-muted {color:#64748b; font-size:.9rem;}
div[data-testid="stMetric"] {background:#f6f8fc; padding:14px; border-radius:12px;}
</style>
""", unsafe_allow_html=True)

# ---------- Database ----------
def db():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS colleges(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            official_email TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS officers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            college_id INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(college_id) REFERENCES colleges(id)
        );
        CREATE TABLE IF NOT EXISTS requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT NOT NULL UNIQUE,
            student_name TEXT NOT NULL,
            student_email TEXT NOT NULL,
            college_id INTEGER NOT NULL,
            company_name TEXT NOT NULL,
            role TEXT NOT NULL,
            recruiter_email TEXT NOT NULL,
            offer_url TEXT,
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'Pending',
            officer_note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(college_id) REFERENCES colleges(id)
        );
        CREATE TABLE IF NOT EXISTS scans(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            company_name TEXT,
            website_url TEXT,
            recruiter_email TEXT,
            payment_requested INTEGER,
            findings TEXT,
            risk_label TEXT
        );
        """)
init_db()

# ---------- Helpers ----------
STATUSES = ["Pending", "Verified by Placement Cell",
            "Not authorised by this college", "Unable to verify"]

def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 180000).hex()
    return f"{salt}${digest}"

def check_password(password, stored):
    try:
        salt, digest = stored.split("$", 1)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 180000).hex()
        return secrets.compare_digest(candidate, digest)
    except Exception:
        return False

def ref_code():
    alphabet = string.ascii_uppercase + string.digits
    return "IS-" + "".join(secrets.choice(alphabet) for _ in range(8))

def valid_email(value):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value or ""))

def colleges():
    with db() as con:
        return con.execute("SELECT id,name,official_email FROM colleges ORDER BY name").fetchall()

def scan_offer(company, url, recruiter, payment):
    findings = []
    score = 0
    if not company.strip():
        findings.append("Company name is missing.")
        score += 2
    if not recruiter.strip():
        findings.append("Recruiter email is missing.")
        score += 2
    elif re.search(r"@(gmail|yahoo|outlook|hotmail)\.", recruiter.lower()):
        findings.append("Recruiter uses a public email provider; independently confirm their identity.")
        score += 1
    if url.strip():
        parsed = urlparse(url if "://" in url else "https://" + url)
        if parsed.scheme != "https":
            findings.append("Website URL does not use HTTPS.")
            score += 1
        if not parsed.netloc or "." not in parsed.netloc:
            findings.append("Website URL looks incomplete.")
            score += 1
    else:
        findings.append("No company website was provided.")
        score += 1
    if payment:
        findings.append("A payment or fee was requested. Do not pay to obtain an internship.")
        score += 3
    if not findings:
        findings.append("No basic warning indicators were detected. This is not proof of legitimacy.")
    label = "High caution" if score >= 4 else ("Review carefully" if score >= 2 else "Fewer basic warning signs")
    return findings, label, score

def get_request(reference, email):
    with db() as con:
        return con.execute("""
            SELECT r.*, c.name AS college_name FROM requests r
            JOIN colleges c ON c.id=r.college_id
            WHERE r.reference=? AND lower(r.student_email)=lower(?)
        """, (reference.strip().upper(), email.strip())).fetchone()

def hero():
    st.markdown("""
    <div class="hero">
      <h1>🛡️ InternSafe</h1>
      <p>Verify before you apply. A college-assisted internship offer verification platform.</p>
    </div>""", unsafe_allow_html=True)

hero()

# ---------- Sidebar navigation ----------
pages = ["Home & Dashboard", "Student Portal", "Placement Cell Portal",
         "Admin Portal", "Track Request", "Smart Scan", "About & Safety"]
with st.sidebar:
    st.markdown("## 🛡️ InternSafe")
    page = st.radio("Navigate", pages, label_visibility="collapsed")
    st.divider()
    st.caption("Demo application • Use dummy data")
    st.caption("College verification is limited to participating colleges.")

# ---------- HOME / DASHBOARD ----------
if page == "Home & Dashboard":
    st.subheader("Dashboard")
    with db() as con:
        total = con.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        pending = con.execute("SELECT COUNT(*) FROM requests WHERE status='Pending'").fetchone()[0]
        verified = con.execute("SELECT COUNT(*) FROM requests WHERE status='Verified by Placement Cell'").fetchone()[0]
        college_count = con.execute("SELECT COUNT(*) FROM colleges").fetchone()[0]
        rows = con.execute("""
            SELECT r.reference,r.student_name,r.company_name,r.role,r.status,r.created_at,c.name college
            FROM requests r JOIN colleges c ON c.id=r.college_id
            ORDER BY r.id DESC LIMIT 10
        """).fetchall()
    a,b,c,d = st.columns(4)
    a.metric("Verification requests", total)
    b.metric("Pending", pending)
    c.metric("Verified by college", verified)
    d.metric("Participating colleges", college_count)
    st.markdown("### Recent requests")
    if rows:
        st.dataframe([dict(x) for x in rows], use_container_width=True, hide_index=True)
    else:
        st.info("No requests yet. Start by submitting an offer in the Student Portal.")
    st.markdown("### How InternSafe works")
    x,y,z = st.columns(3)
    x.markdown("**1. Student submits**\n\nShare internship and recruiter details.")
    y.markdown("**2. College checks**\n\nThe registered placement officer reviews the request.")
    z.markdown("**3. Student tracks**\n\nUse the reference number to view the latest status.")

# ---------- STUDENT PORTAL ----------
elif page == "Student Portal":
    st.subheader("Student Portal")
    st.write("Submit an internship offer so your college placement cell can check its records.")
    college_list = colleges()
    if not college_list:
        st.warning("No colleges have been registered yet. Ask the InternSafe administrator to add your college.")
    else:
        college_map = {f"{r['name']} — {r['official_email']}": r["id"] for r in college_list}
        with st.form("student_submission"):
            c1,c2 = st.columns(2)
            with c1:
                student_name = st.text_input("Student full name *")
                student_email = st.text_input("Student college email *")
                selected_college = st.selectbox("College *", list(college_map))
            with c2:
                company = st.text_input("Company name *")
                role = st.text_input("Internship role / designation *")
                recruiter_email = st.text_input("Recruiter email *")
            offer_url = st.text_input("Company website / offer link (optional)")
            notes = st.text_area("Additional details (optional)", placeholder="Offer date, department, or any context...")
            consent = st.checkbox("I confirm these details are accurate and consent to sharing them with my selected college placement cell.")
            submitted = st.form_submit_button("Submit for college verification", type="primary", use_container_width=True)
        if submitted:
            if not all([student_name.strip(), valid_email(student_email), company.strip(), role.strip(), valid_email(recruiter_email)]):
                st.error("Please complete all required fields and enter valid email addresses.")
            elif not consent:
                st.error("Please provide consent before submitting.")
            else:
                reference = ref_code()
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with db() as con:
                    con.execute("""INSERT INTO requests
                    (reference,student_name,student_email,college_id,company_name,role,recruiter_email,offer_url,notes,status,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,'Pending',?,?)""",
                    (reference,student_name.strip(),student_email.strip(),college_map[selected_college],
                     company.strip(),role.strip(),recruiter_email.strip(),offer_url.strip(),notes.strip(),now,now))
                st.success("Your request has been submitted.")
                st.markdown(f"### Your reference number: `{reference}`")
                st.warning("Save this reference number. You will need it with your student email to track the request.")

# ---------- PLACEMENT CELL PORTAL ----------
elif page == "Placement Cell Portal":
    st.subheader("Placement Cell Portal")
    st.write("Placement officers can review requests assigned to their registered college only.")
    if "officer_id" not in st.session_state:
        with st.form("officer_login"):
            username = st.text_input("Officer username")
            password = st.text_input("Password", type="password")
            login = st.form_submit_button("Officer login", type="primary")
        if login:
            with db() as con:
                officer = con.execute("""SELECT o.*,c.name college_name FROM officers o
                    JOIN colleges c ON c.id=o.college_id
                    WHERE lower(o.username)=lower(?) AND o.active=1""", (username.strip(),)).fetchone()
            if officer and check_password(password, officer["password_hash"]):
                st.session_state.officer_id = officer["id"]
                st.session_state.officer_college_id = officer["college_id"]
                st.session_state.officer_college_name = officer["college_name"]
                st.rerun()
            else:
                st.error("Invalid username or password, or account is inactive.")
    else:
        st.success(f"Logged in: {st.session_state.get('officer_college_name','Placement Cell')}")
        if st.button("Log out"):
            for key in ["officer_id","officer_college_id","officer_college_name"]:
                st.session_state.pop(key, None)
            st.rerun()
        with db() as con:
            requests = con.execute("""SELECT * FROM requests WHERE college_id=?
                ORDER BY CASE status WHEN 'Pending' THEN 0 ELSE 1 END, id DESC""",
                (st.session_state.officer_college_id,)).fetchall()
        st.markdown("### Requests for your college")
        if not requests:
            st.info("No student requests have been submitted to your college yet.")
        for req in requests:
            with st.expander(f"{req['reference']} · {req['student_name']} · {req['company_name']} · {req['status']}"):
                left,right = st.columns(2)
                with left:
                    st.write(f"**Student:** {req['student_name']} ({req['student_email']})")
                    st.write(f"**Company:** {req['company_name']}")
                    st.write(f"**Role:** {req['role']}")
                    st.write(f"**Recruiter:** {req['recruiter_email']}")
                    st.write(f"**Offer link:** {req['offer_url'] or 'Not provided'}")
                    st.write(f"**Submitted:** {req['created_at']}")
                    st.write(f"**Student notes:** {req['notes'] or 'None'}")
                with right:
                    new_status = st.selectbox("Verification status", STATUSES,
                        index=STATUSES.index(req["status"]), key=f"status_{req['id']}")
                    officer_note = st.text_area("Placement cell note", value=req["officer_note"] or "",
                        key=f"note_{req['id']}")
                    if st.button("Save verification update", key=f"save_{req['id']}", type="primary"):
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        with db() as con:
                            con.execute("UPDATE requests SET status=?,officer_note=?,updated_at=? WHERE id=? AND college_id=?",
                                (new_status,officer_note,now,req["id"],st.session_state.officer_college_id))
                        st.success("Request updated.")
                        st.rerun()

# ---------- ADMIN PORTAL ----------
elif page == "Admin Portal":
    st.subheader("Admin Portal")
    st.write("Register participating colleges and create placement officer accounts.")
    st.info("Demo admin password: `InternSafeDemo2026!`  ·  Change this before any public deployment.")
    admin_secret = st.text_input("Admin password", type="password")
    expected_admin = st.secrets.get("ADMIN_PASSWORD", "InternSafeDemo2026!")
    if not secrets.compare_digest(admin_secret, str(expected_admin)):
        st.caption("Enter the admin password to manage colleges and officer accounts.")
    else:
        st.success("Administrator access granted.")
        tab1,tab2,tab3 = st.tabs(["Register college","Create officer account","Manage colleges"])
        with tab1:
            with st.form("add_college"):
                cname = st.text_input("College / institution name")
                cemail = st.text_input("Official placement cell email")
                add = st.form_submit_button("Register college", type="primary")
            if add:
                if not cname.strip() or not valid_email(cemail):
                    st.error("Enter a college name and valid official email.")
                else:
                    try:
                        with db() as con:
                            con.execute("INSERT INTO colleges(name,official_email) VALUES(?,?)",(cname.strip(),cemail.strip()))
                        st.success("College registered.")
                    except sqlite3.IntegrityError:
                        st.error("That college is already registered.")
        with tab2:
            college_list = colleges()
            if not college_list:
                st.warning("Register a college first.")
            else:
                cmap = {r["name"]:r["id"] for r in college_list}
                with st.form("create_officer"):
                    oname = st.text_input("Officer username")
                    oc = st.selectbox("Assign officer to college", list(cmap))
                    opass = st.text_input("Temporary password", type="password")
                    opass2 = st.text_input("Confirm temporary password", type="password")
                    create = st.form_submit_button("Create officer account", type="primary")
                if create:
                    if len(oname.strip()) < 3 or len(opass) < 8:
                        st.error("Username must have at least 3 characters and password at least 8.")
                    elif opass != opass2:
                        st.error("Passwords do not match.")
                    else:
                        try:
                            with db() as con:
                                con.execute("INSERT INTO officers(username,password_hash,college_id) VALUES(?,?,?)",
                                    (oname.strip(),hash_password(opass),cmap[oc]))
                            st.success("Officer account created. Share the username and temporary password securely.")
                        except sqlite3.IntegrityError:
                            st.error("That username already exists.")
        with tab3:
            with db() as con:
                data = con.execute("""SELECT c.id,c.name,c.official_email,COUNT(r.id) request_count
                    FROM colleges c LEFT JOIN requests r ON r.college_id=c.id
                    GROUP BY c.id ORDER BY c.name""").fetchall()
                officer_data = con.execute("""SELECT o.username,c.name college,o.active
                    FROM officers o JOIN colleges c ON c.id=o.college_id ORDER BY c.name,o.username""").fetchall()
            st.markdown("**Registered colleges**")
            st.dataframe([dict(x) for x in data], use_container_width=True, hide_index=True)
            st.markdown("**Placement officers**")
            if officer_data:
                st.dataframe([dict(x) for x in officer_data], use_container_width=True, hide_index=True)
            else:
                st.caption("No officer accounts created yet.")

# ---------- TRACK REQUEST ----------
elif page == "Track Request":
    st.subheader("Track your verification request")
    st.write("Enter the reference number shown after submission and the same student email address.")
    with st.form("track_form"):
        ref = st.text_input("Reference number", placeholder="IS-XXXXXXXX")
        email = st.text_input("Student email")
        go = st.form_submit_button("Check status", type="primary")
    if go:
        if not ref.strip() or not valid_email(email):
            st.error("Enter a reference number and valid student email.")
        else:
            result = get_request(ref,email)
            if not result:
                st.error("No matching request found. Check the reference number and email.")
            else:
                st.markdown(f"### {result['company_name']} — {result['role']}")
                st.write(f"**Reference:** `{result['reference']}`")
                st.write(f"**College:** {result['college_name']}")
                st.write(f"**Submitted:** {result['created_at']}")
                st.write(f"**Last updated:** {result['updated_at']}")
                st.markdown(f"**Current status:** `{result['status']}`")
                if result["officer_note"]:
                    st.info(f"Placement cell note: {result['officer_note']}")
                if result["status"] == "Pending":
                    st.caption("Your request is waiting for review by the college placement cell.")

# ---------- SMART SCAN ----------
elif page == "Smart Scan":
    st.subheader("Smart Scan")
    st.write("A basic rule-based check that highlights details worth reviewing before you respond to an offer.")
    with st.form("smart_scan"):
        company = st.text_input("Company name")
        website = st.text_input("Company website URL", placeholder="https://example.com")
        recruiter = st.text_input("Recruiter email")
        payment = st.checkbox("The recruiter / company asked me to pay a fee, deposit, or training charge.")
        run_scan = st.form_submit_button("Scan offer details", type="primary")
    if run_scan:
        findings,label,score = scan_offer(company,website,recruiter,payment)
        with db() as con:
            con.execute("INSERT INTO scans(created_at,company_name,website_url,recruiter_email,payment_requested,findings,risk_label) VALUES(?,?,?,?,?,?,?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),company,website,recruiter,int(payment),"\n".join(findings),label))
        st.markdown(f"### Result: {label}")
        for item in findings:
            st.write(("⚠️ " if "No basic" not in item else "ℹ️ ") + item)
        st.caption("This scan is a checklist, not a fraud score, background check, or confirmation that a company is genuine.")
    with st.expander("Recent Smart Scan history"):
        with db() as con:
            history = con.execute("SELECT created_at,company_name,website_url,risk_label FROM scans ORDER BY id DESC LIMIT 20").fetchall()
        if history:
            st.dataframe([dict(x) for x in history], use_container_width=True, hide_index=True)
        else:
            st.caption("No scans yet.")

# ---------- ABOUT & SAFETY ----------
elif page == "About & Safety":
    st.subheader("About InternSafe")
    st.write("InternSafe is a college-assisted platform designed to help students request a placement-cell check of internship offers before sharing sensitive information or accepting an offer.")
    st.markdown("### What each status means")
    st.markdown("""
    - **Pending:** The placement cell has not completed its review.
    - **Verified by Placement Cell:** A registered officer marked the request as checked against the college's available records.
    - **Not authorised by this college:** The college did not authorise or recognise the offer in its records. This does **not** by itself prove employer fraud.
    - **Unable to verify:** The officer could not reach a reliable conclusion.
    """)
    st.markdown("### Important safety limits")
    st.warning("""
    - A college verification is not a global certification or a guarantee of employment.
    - Smart Scan uses simple rules and user-provided details. It does not independently verify a company, recruiter, domain, or offer letter.
    - Never pay a fee to secure an internship without independently checking the organisation and the request.
    - Do not share passwords, OTPs, banking PINs, or identity documents with an unverified recruiter.
    """)
    st.markdown("### Demo and deployment notes")
    st.markdown("""
    - This demo stores data in a local SQLite database (`internsafe.db`).
    - A local SQLite file on a hosted app may be temporary and is not suitable for reliable multi-user production storage.
    - For production, use a managed database such as PostgreSQL, secure admin secrets, HTTPS, access controls, backups, and an audit log.
    - Email notifications are not configured in this version.
    """)

st.divider()
st.caption("InternSafe • Verify Before You Apply • Educational prototype")
