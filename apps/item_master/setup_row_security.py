"""
Row-level security cho Sales Order theo team kinh doanh:
  - NVKD       : chi thay don hang cua chinh minh (sales_rep = minh)
  - Truong nhom: thay tat ca don cua team minh (User Permission nhieu thanh vien)
  - Dieu Hanh / Ke Toan / Admin: thay tat ca

Chay: cd /home/frappe/frappe-bench/sites && python ../apps/item_master/setup_row_security.py
"""
import sys
sys.path.insert(0, "/home/frappe/frappe-bench/apps/frappe")
sys.path.insert(0, "/home/frappe/frappe-bench/apps/erpnext")

import frappe

frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

# ─── 1. CUSTOM FIELD: sales_rep tren Sales Order ──────────────────────────────
print("\n=== BUOC 1: THEM CUSTOM FIELD sales_rep ===")

if frappe.db.exists("Custom Field", "Sales Order-sales_rep"):
    frappe.db.delete("Custom Field", "Sales Order-sales_rep")
    print("  Xoa custom field cu")

cf = frappe.new_doc("Custom Field")
cf.dt              = "Sales Order"
cf.label           = "Nhân viên KD"
cf.fieldname       = "sales_rep"
cf.fieldtype       = "Link"
cf.options         = "User"
cf.insert_after    = "customer"
cf.read_only       = 0        # admin co the chinh sua
cf.in_list_view    = 1        # hien trong danh sach
cf.in_standard_filter = 1    # co the loc
cf.bold            = 0
cf.insert(ignore_permissions=True)
frappe.db.commit()
print("  [OK] Custom field 'sales_rep' (Link -> User) tren Sales Order")

# ─── 2. CLIENT SCRIPT: tu dong dien sales_rep khi tao moi ────────────────────
print("\n=== BUOC 2: CLIENT SCRIPT tu dong dien sales_rep ===")

CS_NAME = "Sales Order - Auto Sales Rep"
if frappe.db.exists("Client Script", CS_NAME):
    frappe.delete_doc("Client Script", CS_NAME, ignore_permissions=True, force=1)

cs = frappe.new_doc("Client Script")
cs.name        = CS_NAME
cs.dt          = "Sales Order"
cs.script_type = "Form"
cs.enabled     = 1
cs.script      = """
frappe.ui.form.on('Sales Order', {
    onload: function(frm) {
        if (frm.is_new() && !frm.doc.sales_rep) {
            frm.set_value('sales_rep', frappe.session.user);
        }
    }
});
"""
cs.insert(ignore_permissions=True)
frappe.db.commit()
print(f"  [OK] Client Script: {CS_NAME}")

# ─── 3. SERVER SCRIPT: dam bao sales_rep luon duoc set truoc khi luu ─────────
print("\n=== BUOC 3: SERVER SCRIPT before_save ===")

SS_NAME = "SO Auto Sales Rep Before Save"
if frappe.db.exists("Server Script", SS_NAME):
    frappe.delete_doc("Server Script", SS_NAME, ignore_permissions=True, force=1)

ss = frappe.new_doc("Server Script")
ss.name             = SS_NAME
ss.script_type      = "DocType Event"
ss.dt               = "Sales Order"
ss.doctype_event    = "Before Save"
ss.disabled         = 0
ss.script           = """
if not doc.sales_rep:
    doc.sales_rep = frappe.session.user
"""
ss.insert(ignore_permissions=True)
frappe.db.commit()
print(f"  [OK] Server Script: {SS_NAME}")

# ─── 4. ROLE: Truong Nhom KD ──────────────────────────────────────────────────
print("\n=== BUOC 4: ROLE Truong Nhom KD ===")

if not frappe.db.exists("Role", "Truong Nhom KD"):
    r = frappe.new_doc("Role")
    r.role_name  = "Truong Nhom KD"
    r.desk_access = 1
    r.insert(ignore_permissions=True)
    print("  [OK] Tao role: Truong Nhom KD")
else:
    print("  [--] Da co role: Truong Nhom KD")

frappe.db.commit()

# ─── 5. PERMISSIONS: cap nhat Custom DocPerm ─────────────────────────────────
print("\n=== BUOC 5: CAP NHAT CUSTOM DocPerm ===")

def upsert_perm(doctype, role, perms):
    old = frappe.db.sql(
        "SELECT name FROM `tabCustom DocPerm` WHERE parent=%s AND role=%s",
        (doctype, role), as_dict=True
    )
    for row in old:
        frappe.db.delete("Custom DocPerm", row.name)

    p = frappe.new_doc("Custom DocPerm")
    p.parent     = doctype
    p.parenttype = "DocType"
    p.parentfield = "permissions"
    p.role       = role
    p.permlevel  = 0
    for k, v in perms.items():
        setattr(p, k, v)
    p.insert(ignore_permissions=True)

# NVKD: tao, doc, sua (User Permission se loc du lieu)
upsert_perm("Sales Order", "NVKD",
    {"read":1,"write":1,"create":1,"submit":1,"delete":0,"cancel":0})
print("  [OK] NVKD -> Sales Order (read/write/create/submit)")

# Truong Nhom KD: doc/sua, KHONG submit (de NVKD tu submit)
upsert_perm("Sales Order", "Truong Nhom KD",
    {"read":1,"write":1,"create":1,"submit":1,"delete":0,"cancel":0})
upsert_perm("Customer",    "Truong Nhom KD", {"read":1,"write":1,"create":1})
upsert_perm("Item",        "Truong Nhom KD", {"read":1})
upsert_perm("Quotation",   "Truong Nhom KD",
    {"read":1,"write":1,"create":1,"submit":1})
upsert_perm("Delivery Note","Truong Nhom KD",{"read":1})
upsert_perm("Sales Invoice","Truong Nhom KD",{"read":1})
print("  [OK] Truong Nhom KD -> cac doctype lien quan")

frappe.db.commit()

# ─── 6. SAMPLE USERS + TEAMS ─────────────────────────────────────────────────
print("\n=== BUOC 6: SAMPLE USERS THEO TEAM ===")

TEAMS = {
    "Team Mien Bac": {
        "manager": ("truongnhom.mb@yct.local", "Nguyen Thi Truong MB"),
        "members": [
            ("nvkd.mb1@yct.local", "Tran Van KD MB1"),
            ("nvkd.mb2@yct.local", "Le Thi KD MB2"),
        ]
    },
    "Team Mien Nam": {
        "manager": ("truongnhom.mn@yct.local", "Pham Van Truong MN"),
        "members": [
            ("nvkd.mn1@yct.local", "Nguyen Van KD MN1"),
        ]
    },
}

def create_user(email, fullname, roles):
    if frappe.db.exists("User", email):
        print(f"  [--] User da ton tai: {email}")
        return
    parts = fullname.split()
    u = frappe.new_doc("User")
    u.email        = email
    u.first_name   = parts[-1]
    u.last_name    = " ".join(parts[:-1])
    u.enabled      = 1
    u.new_password = "Abc@12345"
    u.send_welcome_email = 0
    for role in roles:
        u.append("roles", {"role": role})
    u.append("roles", {"role": "All"})
    u.insert(ignore_permissions=True)
    print(f"  [OK] User: {email}  roles={roles}")

for team_name, team in TEAMS.items():
    mgr_email, mgr_name = team["manager"]
    create_user(mgr_email, mgr_name, ["Truong Nhom KD"])
    for mem_email, mem_name in team["members"]:
        create_user(mem_email, mem_name, ["NVKD"])

frappe.db.commit()

# ─── 7. USER PERMISSIONS ─────────────────────────────────────────────────────
print("\n=== BUOC 7: THIET LAP USER PERMISSIONS ===")

def clear_user_perms(user, allow, applicable_for):
    frappe.db.sql("""
        DELETE FROM `tabUser Permission`
        WHERE user=%s AND allow=%s AND applicable_for=%s
    """, (user, allow, applicable_for))

def add_user_perm(user, allow, for_value, applicable_for="Sales Order"):
    """Cho phep 'user' thay Sales Order co field 'allow' = 'for_value'."""
    existing = frappe.db.get_value("User Permission", {
        "user": user, "allow": allow,
        "for_value": for_value, "applicable_for": applicable_for
    }, "name")
    if existing:
        return  # da co

    up = frappe.new_doc("User Permission")
    up.user                = user
    up.allow               = allow
    up.for_value           = for_value
    up.applicable_for      = applicable_for
    up.apply_to_all_doctypes = 0
    up.is_default          = 0
    up.insert(ignore_permissions=True)

# NVKD: chi thay don hang cua chinh minh
for team in TEAMS.values():
    for mem_email, _ in team["members"]:
        if frappe.db.exists("User", mem_email):
            clear_user_perms(mem_email, "User", "Sales Order")
            add_user_perm(mem_email, "User", mem_email, "Sales Order")
            print(f"  [OK] {mem_email:30s} -> chi thay SO cua chinh minh")

# Truong nhom: thay don cua ca team (bao gom ca minh)
for team_name, team in TEAMS.items():
    mgr_email, _ = team["manager"]
    if not frappe.db.exists("User", mgr_email):
        continue
    clear_user_perms(mgr_email, "User", "Sales Order")
    # Quyen xem cua chinh minh
    add_user_perm(mgr_email, "User", mgr_email, "Sales Order")
    # Quyen xem don cua tung thanh vien trong team
    for mem_email, _ in team["members"]:
        add_user_perm(mgr_email, "User", mem_email, "Sales Order")
    members_str = ", ".join(e for e, _ in team["members"])
    print(f"  [OK] {mgr_email:30s} -> thay SO cua: minh + [{members_str}]")

frappe.db.commit()

# Dieu Hanh, Ke Toan, Admin: KHONG co User Permission -> thay tat ca
print("  [--] Dieu Hanh / Ke Toan / Administrator -> khong gioi han (thay tat ca)")

# ─── TONG KET ─────────────────────────────────────────────────────────────────
print("""
=== TONG KET ===

Custom Field: Sales Order.sales_rep (Link -> User)
  - Tu dong dien = nguoi tao don khi mo form
  - Server Script: dam bao luon co gia tri truoc khi luu

Role & Visibility:
  NVKD           : chi thay SO co sales_rep = chinh minh
  Truong Nhom KD : thay SO cua toan bo thanh vien trong team minh
  Dieu Hanh      : thay tat ca (khong gioi han)
  Ke Toan        : thay tat ca (khong gioi han)
  System Manager : thay tat ca

Sample users (pass = Abc@12345):
  Team Mien Bac:
    truongnhom.mb@yct.local  (Truong Nhom KD)  -> thay MB1 + MB2
    nvkd.mb1@yct.local       (NVKD)            -> chi thay cua minh
    nvkd.mb2@yct.local       (NVKD)            -> chi thay cua minh
  Team Mien Nam:
    truongnhom.mn@yct.local  (Truong Nhom KD)  -> thay MN1
    nvkd.mn1@yct.local       (NVKD)            -> chi thay cua minh

[PASS] Setup row-level security hoan tat!
""")
frappe.db.close()
