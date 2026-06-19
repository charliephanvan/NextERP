"""
Test full flow: Sales Order → Delivery Note → Sales Invoice
Chạy: bench --site frontend execute /home/frappe/frappe-bench/test_flow.py
"""
import frappe
from frappe.utils import today, add_days

frappe.set_user("Administrator")

CUSTOMER = "Test Customer VN"
ITEM_CODE = "TEST-SP-001"
WAREHOUSE = "Stores - F"

print("\n=== KIỂM TRA MASTER DATA ===")

# 1. Tìm warehouse hợp lệ
warehouses = frappe.get_all("Warehouse", filters={"is_group": 0}, pluck="name", limit=3)
print(f"Warehouses: {warehouses}")
if warehouses:
    WAREHOUSE = warehouses[0]

# 2. Tìm hoặc tạo Customer
if not frappe.db.exists("Customer", CUSTOMER):
    cust = frappe.new_doc("Customer")
    cust.customer_name = CUSTOMER
    cust.customer_type = "Company"
    cust.customer_group = frappe.get_all("Customer Group", filters={"is_group": 0}, pluck="name", limit=1)[0]
    cust.territory = frappe.get_all("Territory", filters={"is_group": 0}, pluck="name", limit=1)[0]
    cust.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"✓ Tạo Customer: {CUSTOMER}")
else:
    print(f"✓ Customer đã tồn tại: {CUSTOMER}")

# 3. Tìm hoặc tạo Item
if not frappe.db.exists("Item", ITEM_CODE):
    item_groups = frappe.get_all("Item Group", filters={"is_group": 0}, pluck="name", limit=1)
    item = frappe.new_doc("Item")
    item.item_code = ITEM_CODE
    item.item_name = "Sản phẩm Test"
    item.item_group = item_groups[0] if item_groups else "All Item Groups"
    item.stock_uom = "Nos"
    item.is_stock_item = 1
    item.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"✓ Tạo Item: {ITEM_CODE}")
else:
    print(f"✓ Item đã tồn tại: {ITEM_CODE}")

# 4. Tạo Stock Entry để có tồn kho
existing_stock = frappe.db.get_value("Bin", {"item_code": ITEM_CODE, "warehouse": WAREHOUSE}, "actual_qty") or 0
print(f"  Tồn kho hiện tại ({WAREHOUSE}): {existing_stock}")

if float(existing_stock) < 10:
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
    print(f"✓ Nhập kho 100 {ITEM_CODE} vào {WAREHOUSE}")

print("\n=== BƯỚC 1: TẠO SALES ORDER ===")
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
print(f"✓ Sales Order: {so.name}  |  Trạng thái: {so.status}  |  Tổng: {so.grand_total:,.0f}")

print("\n=== BƯỚC 2: TẠO DELIVERY NOTE (Xuất kho) ===")
from erpnext.stock.doctype.delivery_note.delivery_note import make_delivery_note
dn = make_delivery_note(so.name)
dn.posting_date = today()
dn.insert(ignore_permissions=True)
dn.submit()
frappe.db.commit()
print(f"✓ Delivery Note: {dn.name}  |  Trạng thái: {dn.status}")

# Kiểm tra tồn kho sau xuất
stock_after = frappe.db.get_value("Bin", {"item_code": ITEM_CODE, "warehouse": WAREHOUSE}, "actual_qty") or 0
print(f"  Tồn kho sau xuất ({WAREHOUSE}): {stock_after}")

print("\n=== BƯỚC 3: TẠO SALES INVOICE (Hóa đơn) ===")
from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_invoice
si = make_sales_invoice(dn.name)
si.posting_date = today()
si.due_date = add_days(today(), 30)
si.insert(ignore_permissions=True)
si.submit()
frappe.db.commit()
print(f"✓ Sales Invoice: {si.name}  |  Trạng thái: {si.status}  |  Tổng: {si.grand_total:,.0f}")

print("\n=== KẾT QUẢ ===")
# Kiểm tra trạng thái SO sau khi có DN + SI
so.reload()
print(f"Sales Order    : {so.name}  → {so.status}")
print(f"Delivery Note  : {dn.name}  → {dn.status}")
print(f"Sales Invoice  : {si.name}  → {si.status}")

# Kiểm tra công nợ
from erpnext.accounts.utils import get_balance_on
balance = get_balance_on(party_type="Customer", party=CUSTOMER, date=today())
print(f"Công nợ {CUSTOMER}: {balance:,.0f}")

print("\n✅ Full flow PASS")
