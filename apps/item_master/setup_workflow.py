"""
Cau hinh Roles + Workflow + Permissions cho quy trinh giao hang
Chay: cd /home/frappe/frappe-bench/sites && python ../apps/item_master/setup_workflow.py
"""
import sys
sys.path.insert(0, "/home/frappe/frappe-bench/apps/frappe")
sys.path.insert(0, "/home/frappe/frappe-bench/apps/erpnext")

import frappe
from frappe.utils import today

frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

# ─── 1. ROLES ─────────────────────────────────────────────────────────────────
print("\n=== BUOC 1: TAO ROLES ===")

ROLES = [
    "NVKD",         # Nhan vien Kinh doanh
    "Quan Ly Kho",  # Kho
    "Dieu Hanh",    # Van hanh / Dispatcher
    "Tai Xe",       # Tai xe
    "Ke Toan",      # Ke toan
]

for role_name in ROLES:
    if not frappe.db.exists("Role", role_name):
        r = frappe.new_doc("Role")
        r.role_name = role_name
        r.desk_access = 1
        r.insert(ignore_permissions=True)
        print(f"  [OK] Tao role: {role_name}")
    else:
        print(f"  [--] Da co role: {role_name}")

frappe.db.commit()

# ─── 2. WORKFLOW STATES ────────────────────────────────────────────────────────
print("\n=== BUOC 2: TAO WORKFLOW STATES ===")

# (state_name, style)
STATES = [
    ("Nhap",                  ""),
    ("Cho xac nhan",          "Warning"),
    ("Da xac nhan",           "Info"),
    ("Dang chuan bi hang",    "Warning"),
    ("Da phan cong tai xe",   "Primary"),
    ("Dang giao hang",        "Primary"),
    ("Da giao hang",          "Success"),
    ("Da lap hoa don",        "Inverse"),
]

for state_name, style in STATES:
    if not frappe.db.exists("Workflow State", state_name):
        ws = frappe.new_doc("Workflow State")
        ws.workflow_state_name = state_name
        ws.style = style
        ws.insert(ignore_permissions=True)
        print(f"  [OK] {state_name}")
    else:
        # cap nhat style
        frappe.db.set_value("Workflow State", state_name, "style", style)
        print(f"  [--] Da co: {state_name}")

frappe.db.commit()

# ─── 3. WORKFLOW ACTIONS ───────────────────────────────────────────────────────
print("\n=== BUOC 3: TAO WORKFLOW ACTIONS ===")

ACTIONS = [
    "Gui xac nhan",
    "Xac nhan don",
    "Tra ve chinh sua",
    "Bat dau chuan bi hang",
    "Phan cong tai xe",
    "Xuat phat giao hang",
    "Giao hang hoan tat",
    "Xac nhan lap hoa don",
]

for action_name in ACTIONS:
    if not frappe.db.exists("Workflow Action Master", action_name):
        wa = frappe.new_doc("Workflow Action Master")
        wa.workflow_action_name = action_name
        wa.insert(ignore_permissions=True)
        print(f"  [OK] {action_name}")
    else:
        print(f"  [--] Da co: {action_name}")

frappe.db.commit()

# ─── 4. WORKFLOW ON SALES ORDER ────────────────────────────────────────────────
print("\n=== BUOC 4: TAO WORKFLOW TREN SALES ORDER ===")

WORKFLOW_NAME = "Quy trinh Giao hang"

# Xoa workflow cu neu co
if frappe.db.exists("Workflow", WORKFLOW_NAME):
    frappe.delete_doc("Workflow", WORKFLOW_NAME, ignore_permissions=True, force=1)
    frappe.db.commit()
    print(f"  Xoa workflow cu: {WORKFLOW_NAME}")

wf = frappe.new_doc("Workflow")
wf.workflow_name  = WORKFLOW_NAME
wf.document_type  = "Sales Order"
wf.is_active      = 1
wf.send_email_alert = 0
wf.workflow_state_field = "workflow_state"

# States trong workflow
# doc_status: 0=Draft, 1=Submitted, 2=Cancelled
wf.append("states", {"state": "Nhap",               "doc_status": "0", "allow_edit": "NVKD",       "is_optional_state": 0})
wf.append("states", {"state": "Cho xac nhan",        "doc_status": "0", "allow_edit": "Dieu Hanh",  "is_optional_state": 0})
wf.append("states", {"state": "Da xac nhan",         "doc_status": "1", "allow_edit": "Quan Ly Kho","is_optional_state": 0})
wf.append("states", {"state": "Dang chuan bi hang",  "doc_status": "1", "allow_edit": "Dieu Hanh",  "is_optional_state": 0})
wf.append("states", {"state": "Da phan cong tai xe", "doc_status": "1", "allow_edit": "Tai Xe",     "is_optional_state": 0})
wf.append("states", {"state": "Dang giao hang",      "doc_status": "1", "allow_edit": "Dieu Hanh",  "is_optional_state": 0})
wf.append("states", {"state": "Da giao hang",        "doc_status": "1", "allow_edit": "Ke Toan",    "is_optional_state": 0})
wf.append("states", {"state": "Da lap hoa don",      "doc_status": "1", "allow_edit": "System Manager", "is_optional_state": 1})

# Transitions
# NVKD: Nhap → Cho xac nhan
wf.append("transitions", {
    "state": "Nhap", "action": "Gui xac nhan", "next_state": "Cho xac nhan",
    "allowed": "NVKD", "allow_self_approval": 1,
})
# Dieu Hanh: duyet hoac tra lai
wf.append("transitions", {
    "state": "Cho xac nhan", "action": "Xac nhan don", "next_state": "Da xac nhan",
    "allowed": "Dieu Hanh", "allow_self_approval": 0,
})
wf.append("transitions", {
    "state": "Cho xac nhan", "action": "Tra ve chinh sua", "next_state": "Nhap",
    "allowed": "Dieu Hanh", "allow_self_approval": 0,
})
# Kho: bat dau pick
wf.append("transitions", {
    "state": "Da xac nhan", "action": "Bat dau chuan bi hang", "next_state": "Dang chuan bi hang",
    "allowed": "Quan Ly Kho", "allow_self_approval": 1,
})
# Dieu Hanh: phan cong tai xe
wf.append("transitions", {
    "state": "Dang chuan bi hang", "action": "Phan cong tai xe", "next_state": "Da phan cong tai xe",
    "allowed": "Dieu Hanh", "allow_self_approval": 1,
})
# Tai xe: xuat phat
wf.append("transitions", {
    "state": "Da phan cong tai xe", "action": "Xuat phat giao hang", "next_state": "Dang giao hang",
    "allowed": "Tai Xe", "allow_self_approval": 1,
})
# Tai xe: giao xong
wf.append("transitions", {
    "state": "Dang giao hang", "action": "Giao hang hoan tat", "next_state": "Da giao hang",
    "allowed": "Tai Xe", "allow_self_approval": 1,
})
# Ke toan: xac nhan hoa don
wf.append("transitions", {
    "state": "Da giao hang", "action": "Xac nhan lap hoa don", "next_state": "Da lap hoa don",
    "allowed": "Ke Toan", "allow_self_approval": 1,
})

wf.insert(ignore_permissions=True)
frappe.db.commit()
print(f"  [OK] Tao workflow: {WORKFLOW_NAME}")
print(f"       {len(wf.states)} states, {len(wf.transitions)} transitions")

# ─── 5. ROLE PERMISSIONS ──────────────────────────────────────────────────────
print("\n=== BUOC 5: PHAN QUYEN THEO ROLE ===")

def set_perms(doctype, role, perms: dict):
    """
    perms: dict voi cac key read/write/create/delete/submit/cancel/amend (0 hoac 1)
    """
    # Xoa ban ghi cu neu co
    old = frappe.db.sql(
        "SELECT name FROM `tabCustom DocPerm` WHERE parent=%s AND role=%s",
        (doctype, role), as_dict=True
    )
    for row in old:
        frappe.db.delete("Custom DocPerm", row.name)

    perm = frappe.new_doc("Custom DocPerm")
    perm.parent      = doctype
    perm.parenttype  = "DocType"
    perm.parentfield = "permissions"
    perm.role        = role
    perm.permlevel   = 0
    perm.read        = perms.get("read",   0)
    perm.write       = perms.get("write",  0)
    perm.create      = perms.get("create", 0)
    perm.delete      = perms.get("delete", 0)
    perm.submit      = perms.get("submit", 0)
    perm.cancel      = perms.get("cancel", 0)
    perm.amend       = perms.get("amend",  0)
    perm.insert(ignore_permissions=True)


PERM_MAP = {
    # (doctype, role): {perms}

    # NVKD: tao SO, bao gia, doc DN/SI
    ("Sales Order",   "NVKD"):       {"read":1,"write":1,"create":1,"submit":1},
    ("Quotation",     "NVKD"):       {"read":1,"write":1,"create":1,"submit":1},
    ("Customer",      "NVKD"):       {"read":1,"write":1,"create":1},
    ("Item",          "NVKD"):       {"read":1},
    ("Delivery Note", "NVKD"):       {"read":1},
    ("Sales Invoice", "NVKD"):       {"read":1},

    # Quan Ly Kho: doc SO, tao Pick List, Delivery Note, Stock Entry
    ("Sales Order",   "Quan Ly Kho"): {"read":1},
    ("Pick List",     "Quan Ly Kho"): {"read":1,"write":1,"create":1,"submit":1},
    ("Delivery Note", "Quan Ly Kho"): {"read":1,"write":1,"create":1,"submit":1},
    ("Stock Entry",   "Quan Ly Kho"): {"read":1,"write":1,"create":1,"submit":1},
    ("Bin",           "Quan Ly Kho"): {"read":1},
    ("Item",          "Quan Ly Kho"): {"read":1},

    # Dieu Hanh: doc tat ca, phe duyet SO, tao Delivery Trip
    ("Sales Order",   "Dieu Hanh"):   {"read":1,"write":1,"submit":1,"cancel":1},
    ("Delivery Note", "Dieu Hanh"):   {"read":1},
    ("Pick List",     "Dieu Hanh"):   {"read":1},
    ("Delivery Trip", "Dieu Hanh"):   {"read":1,"write":1,"create":1,"submit":1},
    ("Driver",        "Dieu Hanh"):   {"read":1,"write":1,"create":1},
    ("Vehicle",       "Dieu Hanh"):   {"read":1,"write":1,"create":1},

    # Tai Xe: doc Delivery Trip, cap nhat Delivery Stop
    ("Delivery Trip", "Tai Xe"):      {"read":1,"write":1},
    ("Delivery Note", "Tai Xe"):      {"read":1},

    # Ke Toan: tao SI, Payment, doc tat ca
    ("Sales Order",   "Ke Toan"):     {"read":1},
    ("Delivery Note", "Ke Toan"):     {"read":1},
    ("Sales Invoice", "Ke Toan"):     {"read":1,"write":1,"create":1,"submit":1,"cancel":1,"amend":1},
    ("Payment Entry", "Ke Toan"):     {"read":1,"write":1,"create":1,"submit":1,"cancel":1},
    ("Journal Entry", "Ke Toan"):     {"read":1,"write":1,"create":1,"submit":1,"cancel":1},
    ("Customer",      "Ke Toan"):     {"read":1},
}

for (doctype, role), perms in PERM_MAP.items():
    set_perms(doctype, role, perms)
    print(f"  [OK] {role:20s} → {doctype}")

frappe.db.commit()

# ─── 6. SETUP USER NHOM (tuy chon: tao user mau) ─────────────────────────────
print("\n=== BUOC 6: TAO USER MAU ===")

SAMPLE_USERS = [
    ("nvkd@yct.local",       "Nguyen Van Kinh Doanh", "NVKD"),
    ("kho@yct.local",        "Tran Thi Kho",          "Quan Ly Kho"),
    ("dieuhhanh@yct.local",  "Le Van Dieu Hanh",      "Dieu Hanh"),
    ("taixe@yct.local",      "Pham Van Tai Xe",       "Tai Xe"),
    ("ketoan@yct.local",     "Vu Thi Ke Toan",        "Ke Toan"),
]

for email, fullname, role in SAMPLE_USERS:
    if not frappe.db.exists("User", email):
        u = frappe.new_doc("User")
        u.email       = email
        u.first_name  = fullname.split()[-1]
        u.last_name   = " ".join(fullname.split()[:-1])
        u.enabled     = 1
        u.new_password = "Abc@12345"
        u.send_welcome_email = 0
        u.append("roles", {"role": role})
        u.append("roles", {"role": "All"})
        u.insert(ignore_permissions=True)
        print(f"  [OK] User: {email}  role={role}  pass=Abc@12345")
    else:
        print(f"  [--] User da ton tai: {email}")

frappe.db.commit()

# ─── TONG KET ─────────────────────────────────────────────────────────────────
print("\n=== TONG KET ===")
print(f"  Roles       : {len(ROLES)}")
print(f"  States      : {len(STATES)}")
print(f"  Actions     : {len(ACTIONS)}")
print(f"  Transitions : {len(wf.transitions)}")
print(f"  Permissions : {len(PERM_MAP)} entries")
print(f"  Sample users: {len(SAMPLE_USERS)}")
print("""
Workflow: Sales Order
  NVKD         Nhap → [Gui xac nhan] → Cho xac nhan
  Dieu Hanh    Cho xac nhan → [Xac nhan don] → Da xac nhan
               Cho xac nhan → [Tra ve chinh sua] → Nhap
  Quan Ly Kho  Da xac nhan → [Bat dau chuan bi hang] → Dang chuan bi hang
  Dieu Hanh    Dang chuan bi hang → [Phan cong tai xe] → Da phan cong tai xe
  Tai Xe       Da phan cong tai xe → [Xuat phat giao hang] → Dang giao hang
  Tai Xe       Dang giao hang → [Giao hang hoan tat] → Da giao hang
  Ke Toan      Da giao hang → [Xac nhan lap hoa don] → Da lap hoa don
""")
print("[PASS] Setup hoan tat!")
frappe.db.close()
