# 任务信息编辑器 - 独立桌面工具 v2.2
# 新增：另存草稿、读取指定草稿、导入TXT
import sys
import os
import json
from PySide6 import QtWidgets, QtCore, QtGui

# 默认保存路径（用户可以通过对话框自己改）
DEFAULT_TXT_PATH = r"D:/VRED_Renders/batch_tasks.txt"
DEFAULT_DRAFT_PATH = r"D:/VRED_Renders/batch_tasks_draft.json"

COLUMNS = ["序号", "文件夹", "摄像机", "视点", "隔离", "变量"]
COL_WIDTHS = [50, 70, 120, 300, 200, 200] 

class TaskEditor(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VRED 批量渲染任务编辑器 v2.2")
        self.resize(1100, 600)

        layout = QtWidgets.QVBoxLayout(self)

        # ================= 工具栏 1：行操作 =================
        toolbar1 = QtWidgets.QHBoxLayout()
        
        self.btn_add = QtWidgets.QPushButton("添加1行")
        self.btn_add.clicked.connect(self.add_row)
        toolbar1.addWidget(self.btn_add)

        self.btn_add_10 = QtWidgets.QPushButton("批量添加10行")
        self.btn_add_10.clicked.connect(self.add_10_rows)
        toolbar1.addWidget(self.btn_add_10)

        self.btn_del = QtWidgets.QPushButton("删除选中行")
        self.btn_del.clicked.connect(self.delete_rows)
        toolbar1.addWidget(self.btn_del)

        self.btn_clear = QtWidgets.QPushButton("清空全部")
        self.btn_clear.clicked.connect(self.clear_all)
        toolbar1.addWidget(self.btn_clear)

        layout.addLayout(toolbar1)

        # ================= 工具栏 2：文件操作 =================
        toolbar2 = QtWidgets.QHBoxLayout()
        
        self.btn_save_draft = QtWidgets.QPushButton("保存内容到")
        self.btn_save_draft.clicked.connect(self.save_draft)
        toolbar2.addWidget(self.btn_save_draft)

        self.btn_load_draft = QtWidgets.QPushButton("读取草稿")
        self.btn_load_draft.clicked.connect(self.load_draft)
        toolbar2.addWidget(self.btn_load_draft)

        self.btn_import_txt = QtWidgets.QPushButton("导入 TXT")
        self.btn_import_txt.clicked.connect(self.import_txt)
        toolbar2.addWidget(self.btn_import_txt)

        toolbar2.addStretch() # 弹簧推挤

        self.btn_export_txt = QtWidgets.QPushButton("导出为 TXT")
        self.btn_export_txt.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_export_txt.clicked.connect(self.export_txt)
        toolbar2.addWidget(self.btn_export_txt)

        layout.addLayout(toolbar2)

        # ================= 表格区域 =================
        self.table = QtWidgets.QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        
        header = self.table.horizontalHeader()
        for i, width in enumerate(COL_WIDTHS):
            if i < 4:
                self.table.setColumnWidth(i, width)
            else:
                header.setSectionResizeMode(i, QtWidgets.QHeaderView.Stretch)
                
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ContiguousSelection)
        layout.addWidget(self.table)

        # ================= 状态栏 =================
        self.status = QtWidgets.QLabel("就绪。支持 Excel 多行复制粘贴 (Ctrl+V)。")
        self.status.setStyleSheet("color: #555;")
        layout.addWidget(self.status)

        for _ in range(10):
            self.add_row()

    # ================= 基础表格操作 =================
    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        defaults = ["", "", "无", "无", "无", "无"]
        for col, val in enumerate(defaults):
            item = QtWidgets.QTableWidgetItem(val)
            self.table.setItem(row, col, item)

    def add_10_rows(self):
        self.table.setUpdatesEnabled(False)
        for _ in range(10):
            self.add_row()
        self.table.setUpdatesEnabled(True)
        self.status.setText(f"已添加10行，当前共 {self.table.rowCount()} 行")

    def delete_rows(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def clear_all(self):
        self.table.setRowCount(0)
        self.status.setText("已清空全部内容")

    # ================= 支持从 Excel 直接粘贴 =================
    def keyPressEvent(self, event):
        if event.matches(QtGui.QKeySequence.Paste):
            self.paste_from_clipboard()
            event.accept()
        else:
            super().keyPressEvent(event)

    def paste_from_clipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()
        text = clipboard.text()
        if not text:
            return

        current = self.table.currentItem()
        if not current:
            start_row, start_col = 0, 0
        else:
            start_row, start_col = current.row(), current.column()

        lines = text.strip().split('\n')
        
        self.table.setUpdatesEnabled(False)
        for r_offset, line in enumerate(lines):
            cells = line.split('\t')
            target_row = start_row + r_offset
            
            if target_row >= self.table.rowCount():
                self.add_row()

            for c_offset, cell_text in enumerate(cells):
                target_col = start_col + c_offset
                if target_col < self.table.columnCount():
                    item = self.table.item(target_row, target_col)
                    if not item:
                        item = QtWidgets.QTableWidgetItem()
                        self.table.setItem(target_row, target_col, item)
                    item.setText(cell_text.strip())
                    
        self.table.setUpdatesEnabled(True)
        self.status.setText(f"成功粘贴 {len(lines)} 行数据")

    # ================= 草稿保存与读取 (JSON) =================
    def save_draft(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "保存草稿", DEFAULT_DRAFT_PATH, "JSON Files (*.json)")
        if not path:
            return
        try:
            dir_name = os.path.dirname(path)
            if dir_name: os.makedirs(dir_name, exist_ok=True)
            
            data = []
            for row in range(self.table.rowCount()):
                row_data = []
                is_empty = True
                for col in range(len(COLUMNS)):
                    item = self.table.item(row, col)
                    text = item.text() if item else ""
                    row_data.append(text)
                    if text.strip() and text != "无":
                        is_empty = False
                if not is_empty:
                    data.append(row_data)

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            self.status.setText(f"草稿已保存: {path}")
        except Exception as e:
            self.status.setText(f"草稿保存失败: {e}")

    def load_draft(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "读取草稿", DEFAULT_DRAFT_PATH, "JSON Files (*.json);;All Files (*)")
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.table.setRowCount(0)
            self.table.setUpdatesEnabled(False)
            for row_data in data:
                row = self.table.rowCount()
                self.table.insertRow(row)
                for col, val in enumerate(row_data):
                    if col < self.table.columnCount():
                        self.table.setItem(row, col, QtWidgets.QTableWidgetItem(val))
            for _ in range(10): self.add_row() # 补充空行
            self.table.setUpdatesEnabled(True)
            
            self.status.setText(f"已读取草稿: {path}")
        except Exception as e:
            self.status.setText(f"读取草稿失败: {e}")

    # ================= TXT 导入与导出 =================
    def import_txt(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "导入 TXT", DEFAULT_TXT_PATH, "Text Files (*.txt);;All Files (*)")
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                lines = [line.strip() for line in f if line.strip()]
            
            if not lines:
                self.status.setText("TXT 文件为空")
                return

            # 检查并跳过表头
            if lines[0].startswith("序号"):
                lines = lines[1:]
            
            self.table.setRowCount(0)
            self.table.setUpdatesEnabled(False)
            
            for line in lines:
                parts = [p.strip() for p in line.split("/")]
                # 补齐或截断为6列
                parts = (parts + ["无"] * len(COLUMNS))[:len(COLUMNS)]
                
                row = self.table.rowCount()
                self.table.insertRow(row)
                for col, val in enumerate(parts):
                    self.table.setItem(row, col, QtWidgets.QTableWidgetItem(val))
                    
            for _ in range(10): self.add_row()
            self.table.setUpdatesEnabled(True)
            
            self.status.setText(f"成功导入 {len(lines)} 条任务: {path}")
        except Exception as e:
            self.status.setText(f"导入失败: {e}")

    def export_txt(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出 TXT", DEFAULT_TXT_PATH, "Text Files (*.txt)")
        if not path:
            return

        try:
            dir_name = os.path.dirname(path)
            if dir_name: os.makedirs(dir_name, exist_ok=True)
                
            count = 0
            with open(path, 'w', encoding='utf-8-sig') as f:
                f.write("/".join(COLUMNS) + "\n")
                for row in range(self.table.rowCount()):
                    vals = []
                    is_empty = True
                    for col in range(len(COLUMNS)):
                        item = self.table.item(row, col)
                        text = item.text().strip() if item else ""
                        if text and text != "无": is_empty = False
                        vals.append(text if text else "无")
                    
                    if is_empty:
                        continue
                        
                    f.write("/".join(vals) + "\n")
                    count += 1
                    
            self.status.setText(f"成功导出 {count} 条任务: {path}")
        except Exception as e:
            self.status.setText(f"导出失败: {e}")


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = TaskEditor()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
