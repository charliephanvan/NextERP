/**
 * item_master/item_master/public/js/item_list.js
 * Client script — thêm nút "Tải lên Dữ liệu Gốc" vào Item List View.
 */

frappe.listview_settings['Item'] = frappe.listview_settings['Item'] || {};

frappe.listview_settings['Item'].onload = function (listview) {

    listview.page.add_inner_button(__('Tải lên Dữ liệu Gốc'), function () {
        show_upload_dialog();
    }, __('Nhập / Xuất'));

};

function show_upload_dialog() {
    const d = new frappe.ui.Dialog({
        title: __('Tải lên Dữ liệu Gốc — Sản phẩm'),
        size: 'large',
        fields: [
            // ── Hướng dẫn ────────────────────────────────────────────────
            {
                fieldtype: 'HTML',
                fieldname: 'instructions',
                options: `
                <div style="
                    background:#EBF3FB;
                    border-left:4px solid #2E75B6;
                    padding:12px 16px;
                    border-radius:4px;
                    margin-bottom:4px;
                ">
                    <div style="font-weight:600;color:#1F4E79;margin-bottom:6px;">
                        📋 Hướng dẫn nhập dữ liệu
                    </div>
                    <ol style="margin:0;padding-left:18px;color:#444;line-height:1.8;">
                        <li>Tải file mẫu Excel bằng nút bên dưới</li>
                        <li>Điền dữ liệu sản phẩm vào file (cột màu vàng là bắt buộc)</li>
                        <li>Tải file lên và nhấn <strong>Nhập dữ liệu</strong></li>
                    </ol>
                </div>`
            },
            { fieldtype: 'Column Break' },
            // ── Nút tải mẫu ──────────────────────────────────────────────
            {
                fieldtype: 'HTML',
                fieldname: 'download_section',
                options: `
                <div style="text-align:right;padding:8px 0;">
                    <button id="btn_download_template"
                        class="btn btn-default btn-sm"
                        style="color:#1F4E79;border-color:#1F4E79;">
                        ⬇&nbsp; Tải mẫu Excel
                    </button>
                </div>`
            },
            { fieldtype: 'Section Break' },
            // ── Upload file ───────────────────────────────────────────────
            {
                label: __('Chọn file dữ liệu (.xlsx)'),
                fieldname: 'data_file',
                fieldtype: 'Attach',
                reqd: 1,
                options: { restrictions: { allowed_file_types: ['.xlsx', '.xls'] } },
                description: __('Chỉ chấp nhận file Excel (.xlsx, .xls)'),
            },
            { fieldtype: 'Column Break' },
            // ── Tuỳ chọn ─────────────────────────────────────────────────
            {
                label: __('Cập nhật nếu sản phẩm đã tồn tại'),
                fieldname: 'update_existing',
                fieldtype: 'Check',
                default: 1,
            },
            {
                label: __('Bỏ qua dòng lỗi và tiếp tục'),
                fieldname: 'skip_errors',
                fieldtype: 'Check',
                default: 0,
            },
            { fieldtype: 'Section Break' },
            // ── Kết quả ───────────────────────────────────────────────────
            {
                fieldtype: 'HTML',
                fieldname: 'result_area',
                options: '',
            },
        ],

        primary_action_label: __('Nhập dữ liệu →'),
        primary_action: function (values) {
            if (!values.data_file) {
                frappe.msgprint(__('Vui lòng chọn file dữ liệu'));
                return;
            }
            run_import(d, values);
        },

        secondary_action_label: __('Đóng'),
        secondary_action: function () { d.hide(); },
    });

    d.show();

    // Gắn sự kiện nút tải mẫu sau khi dialog render
    d.$wrapper.find('#btn_download_template').on('click', function () {
        download_template();
    });
}


function download_template() {
    const url = '/api/method/item_master.api.download_template';
    const link = document.createElement('a');
    link.href = url;
    link.download = 'Template_SanPham.xlsx';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}


function run_import(dialog, values) {
    const btn = dialog.get_primary_btn();
    btn.prop('disabled', true).text(__('Đang xử lý…'));

    // Hiện loading
    dialog.fields_dict.result_area.$wrapper.html(`
        <div style="text-align:center;padding:20px;color:#888;">
            <div class="frappe-loading" style="display:inline-block;"></div>
            <p style="margin-top:8px;">Đang nhập dữ liệu, vui lòng chờ…</p>
        </div>
    `);

    frappe.call({
        method: 'item_master.api.upload_master_data',
        args: {
            file_url:        values.data_file,
            update_existing: values.update_existing ? 1 : 0,
            skip_errors:     values.skip_errors     ? 1 : 0,
        },
        callback: function (r) {
            btn.prop('disabled', false).text(__('Nhập dữ liệu →'));

            if (r.exc) {
                show_error_result(dialog, r.exc);
                return;
            }

            const res = r.message;
            show_success_result(dialog, res);

            // Refresh list nếu có dữ liệu mới
            if ((res.created + res.updated) > 0) {
                cur_list && cur_list.refresh();
            }
        },
        error: function (r) {
            btn.prop('disabled', false).text(__('Nhập dữ liệu →'));
            show_error_result(dialog, r._server_messages || 'Lỗi không xác định');
        }
    });
}


function show_success_result(dialog, res) {
    const has_errors = res.errors && res.errors.length > 0;

    let errors_html = '';
    if (has_errors) {
        const error_items = res.errors.map(e =>
            `<li style="margin-bottom:4px;">${frappe.utils.escape_html(e)}</li>`
        ).join('');
        errors_html = `
        <div style="margin-top:12px;">
            <div style="font-weight:600;color:#C0392B;margin-bottom:6px;">
                ⚠ Các dòng bị bỏ qua (${res.errors.length}):
            </div>
            <ul style="
                background:#FFF5F5;
                border:1px solid #F1948A;
                border-radius:4px;
                padding:10px 10px 10px 28px;
                max-height:180px;
                overflow-y:auto;
                font-size:12px;
                color:#922B21;
            ">${error_items}</ul>
        </div>`;
    }

    dialog.fields_dict.result_area.$wrapper.html(`
        <div style="
            background:#EAF7F0;
            border:1px solid #A9DFBF;
            border-radius:6px;
            padding:16px;
        ">
            <div style="font-weight:700;font-size:15px;color:#1E8449;margin-bottom:12px;">
                ✅ Nhập dữ liệu hoàn tất
            </div>
            <div style="display:flex;gap:24px;">
                <div style="text-align:center;">
                    <div style="font-size:28px;font-weight:700;color:#1E8449;">${res.created}</div>
                    <div style="font-size:12px;color:#555;">Tạo mới</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:28px;font-weight:700;color:#2980B9;">${res.updated}</div>
                    <div style="font-size:12px;color:#555;">Cập nhật</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:28px;font-weight:700;color:#E67E22;">${res.skipped}</div>
                    <div style="font-size:12px;color:#555;">Bỏ qua</div>
                </div>
            </div>
            ${errors_html}
        </div>
    `);
}


function show_error_result(dialog, message) {
    const msg = typeof message === 'string'
        ? message
        : JSON.stringify(message, null, 2);

    dialog.fields_dict.result_area.$wrapper.html(`
        <div style="
            background:#FDF2F8;
            border:1px solid #F1948A;
            border-radius:6px;
            padding:16px;
        ">
            <div style="font-weight:700;font-size:15px;color:#C0392B;margin-bottom:8px;">
                ❌ Lỗi khi nhập dữ liệu
            </div>
            <pre style="
                font-size:12px;
                color:#922B21;
                white-space:pre-wrap;
                word-break:break-word;
                margin:0;
            ">${frappe.utils.escape_html(msg)}</pre>
        </div>
    `);
}
