"""
Test full flow: Sales Order -> Delivery Note -> Sales Invoice
Chay: python /home/frappe/frappe-bench/apps/item_master/test_flow.py
"""
import sys
sys.path.insert(0, "/home/frappe/frappe-bench/apps/frappe")
sys.path.insert(0, "/home/frappe/frappe-bench/apps/erpnext")

import frappe
from frappe.utils import today, add_days

frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

CUSTOMER = "Test Customer VN"
ITEM_CODE = "TEST-SP-001"

print("\n=== KIEM TRA MASTER DATA ===")

# Warehouse
warehouses = frappe.get_all("Warehouse", filters={"is_group": 0}, pluck="name", limit=10)
print(f"Warehouses co san: {warehouses}")
# Uu tien Stores, bo qua Goods In Transit
WAREHOUSE = next((w for w in warehouses if "Stores" in w), warehouses[0] if warehouses else "Stores - F")

# Customer
if not frappe.db.exists("Customer", CUSTOMER):
    cg = frappe.get_all("Customer Group", filters={"is_group": 0}, pluck="name", limit=1)
    ter = frappe.get_all("Territory", filters={"is_group": 0}, pluck="name", limit=1)
    cust = frappe.new_doc("Customer")
    cust.customer_name = CUSTOMER
    cust.customer_type = "Company"
    cust.customer_group = cg[0] if cg else "Commercial"
    cust.territory = ter[0] if ter else "Rest Of The World"
    cust.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"[OK] Tao Customer: {CUSTOMER}")
else:
    print(f"[OK] Customer da ton tai: {CUSTOMER}")

# Item
if not frappe.db.exists("Item", ITEM_CODE):
    ig = frappe.get_all("Item Group", filters={"is_group": 0}, pluck="name", limit=1)
    item = frappe.new_doc("Item")
    item.item_code = ITEM_CODE
    item.item_name = "San pham Test"
    item.item_group = ig[0] if ig else "All Item Groups"
    item.stock_uom = "Nos"
    item.is_stock_item = 1
    item.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"[OK] Tao Item: {ITEM_CODE}")
else:
    print(f"[OK] Item da ton tai: {ITEM_CODE}")

# Nhap kho neu thieu hang
actual_qty = frappe.db.get_value("Bin", {"item_code": ITEM_CODE, "warehouse": WAREHOUSE}, "actual_qty") or 0
print(f"     Ton kho ({WAREHOUSE}): {actual_qty}")
if float(actual_qty) < 10:
    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Material Receipt"
    se.posting_date = today()
    se.append("items", {
        "item_code": ITEM_CODE,
        "qty": 100,
        "t_warehouse": WAREHOUSE,
        "basic_rate": 50000,
    })
    se.insert(ignore_permissions=True)
    se.submit()
    frappe.db.commit()
    print(f"[OK] Nhap kho 100 {ITEM_CODE}")

print("\n=== BUOC 1: SALES ORDER ===")
so = frappe.new_doc("Sales Order")
so.customer = CUSTOMER
so.transaction_date = today()
so.delivery_date = add_days(today(), 3)
so.append("items", {
    "item_code": ITEM_CODE,
    "qty": 5,
    "rate": 100000,
    "warehouse": WAREHOUSE,
})
so.insert(ignore_permissions=True)
so.submit()
frappe.db.commit()
print(f"[OK] {so.name}  trang thai={so.status}  tong={so.grand_total:,.0f}")

print("\n=== BUOC 2: DELIVERY NOTE (Xuat kho) ===")
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
dn = make_delivery_note(so.name)
dn.posting_date = today()
dn.insert(ignore_permissions=True)
dn.submit()
frappe.db.commit()
stock_after = frappe.db.get_value("Bin", {"item_code": ITEM_CODE, "warehouse": WAREHOUSE}, "actual_qty") or 0
print(f"[OK] {dn.name}  trang thai={dn.status}")
print(f"     Ton kho sau xuat: {stock_after}")

print("\n=== BUOC 3: SALES INVOICE (Hoa don) ===")
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
si = make_sales_invoice(dn.name)
si.posting_date = today()
si.due_date = add_days(today(), 30)
si.insert(ignore_permissions=True)
si.submit()
frappe.db.commit()
print(f"[OK] {si.name}  trang thai={si.status}  tong={si.grand_total:,.0f}")

print("\n=== KIEM TRA TRANG THAI CUOI ===")
so.reload()
print(f"Sales Order   : {so.name}  -> {so.status}")
print(f"Delivery Note : {dn.name}  -> {dn.status}")
print(f"Sales Invoice : {si.name}  -> {si.status}")

# Cong no
from erpnext.accounts.utils import get_balance_on
balance = get_balance_on(party_type="Customer", party=CUSTOMER, date=today())
print(f"Cong no {CUSTOMER}: {balance:,.0f}")

print("\n[PASS] Full flow Sales Order -> Delivery Note -> Sales Invoice THANH CONG")

frappe.db.close()
