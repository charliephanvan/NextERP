import sys
sys.path.insert(0, "/home/frappe/frappe-bench/apps/frappe")
sys.path.insert(0, "/home/frappe/frappe-bench/apps/erpnext")
import frappe
frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()

so = frappe.get_doc("Sales Order", "SAL-ORD-2026-00011")
print(f"workflow_state : {so.workflow_state}")
print(f"docstatus      : {so.docstatus}")

wf = frappe.get_doc("Workflow", "Quy trinh Giao hang")
print("\nWorkflow states (allow_edit):")
for s in wf.states:
    print(f"  {s.state!r:35s} doc_status={s.doc_status}  allow_edit={s.allow_edit!r}")

frappe.set_user("kho@yct.local")
roles = frappe.get_roles()
print(f"\nRoles kho@yct.local: {[r for r in roles if r not in ('Guest','All')]}")

print(f"has_permission read  : {frappe.has_permission('Sales Order', 'read',   so)}")
print(f"has_permission write : {frappe.has_permission('Sales Order', 'write',  so)}")
print(f"has_permission submit: {frappe.has_permission('Sales Order', 'submit', so)}")

# Thu simulate workflow action
from frappe.workflow.doctype.workflow.workflow import get_transitions
frappe.set_user("kho@yct.local")
try:
    transitions = get_transitions(so, workflow=wf)
    print(f"\nTransitions available for kho: {[(t.action, t.allowed) for t in transitions]}")
except Exception as e:
    print(f"\nget_transitions error: {e}")

frappe.db.close()
