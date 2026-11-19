# 任务信息编辑器 - 独立桌面工具 v2.3
# 新增：修复Excel多行列粘贴、支持拖拽下拉自动填充递增序号、右键粘贴
import sys
import os
import json
import re
from PySide6 import QtWidgets, QtCore, QtGui

DEFAULT_TXT_PATH = r"D:/VRED_Renders/batch_tasks.txt"
DEFAULT_DRAFT_PATH = r"D:/VRED_Renders/batch_tasks_draft.json"

COLUMNS = ["序号", "文件夹", "摄像机", "视点", "隔离", "变量"]
COL_WIDTHS = [50, 70, 120, 300, 200, 200] 

class TaskEditor(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VRED 批量渲染任务编辑器 v2.3")
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

        toolbar2.addStretch()

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
        
        # 启用右键菜单
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # 核心优化：给表格安装事件过滤器，拦截Ctrl+V
        self.table.installEventFilter(self)
        
        layout.addWidget(self.table)

        # ================= 状态栏 =================
        self.status = QtWidgets.QLabel("就绪。支持 Excel 多行复制 (按Ctrl+V粘贴)，支持右下角下拉自动递增序号。")
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

    # ================= 事件过滤器：处理粘贴与下拉序号 =================
    def eventFilter(self, obj, event):
        # 1. 拦截表格的 Ctrl+V 粘贴
        if obj == self.table and event.type() == QtCore.QEvent.KeyPress:
            if event.matches(QtGui.QKeySequence.Paste):
                self.paste_from_clipboard()
                return True
                
        # 2. 拦截序号列的拖拽填充
        if obj == self.table and event.type() == QtCore.QEvent.KeyPress:
            pass # 预留位置

        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.matches(QtGui.QKeySequence.Paste):
            self.paste_from_clipboard()
            event.accept()
        else:
            super().keyPressEvent(event)

    # ================= 右键菜单 =================
    def show_context_menu(self, pos):
        menu = QtWidgets.QMenu()
        paste_action = menu.addAction("粘贴 (Ctrl+V)")
        delete_action = menu.addAction("删除选中行")
        
        action = menu.exec_(self.table.mapToGlobal(pos))
        
        if action == paste_action:
            self.paste_from_clipboard()
        elif action == delete_action:
            self.delete_rows()

    # ================= 核心优化：粘贴逻辑 =================
    def paste_from_clipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()
        text = clipboard.text()
        if not text.strip():
            return

        current = self.table.currentItem()
        if not current:
            start_row, start_col = 0, 0
        else:
            start_row, start_col = current.row(), current.column()

        lines = text.strip().split('\n')
        
        self.table.setUpdatesEnabled(False)
        for r_offset, line in enumerate(lines):
            # 处理 Excel 中的 tab 分隔符
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

    # ================= 表格下拉填充逻辑 (自动递增序号) =================
    def closeEditor(self, editor, hint):
        # 当单元格编辑完成时触发
        super().closeEditor(editor, hint)
        
    # 重写表格方法，捕获拖拽填充后的动作
    def on_table_data_changed(self, topLeft, bottomRight):
        # 只处理序号列 (第0列)
        if topLeft.column() == 0 and bottomRight.column() == 0:
            start_row = topLeft.row()
            end_row = bottomRight.row()
            
            if start_row == end_row:
                return # 没有拖拽多行

            # 获取起始行的数字
            start_text = self.table.item(start_row, 0).text().strip()
            if not start_text.isdigit():
                return # 如果第一行不是数字，不处理

            start_num = int(start_text)
            
            # 从第二行开始递增
            for row in range(start_row + 1, end_row + 1):
                item = self.table.item(row, 0)
                if not item:
                    item = QtWidgets.QTableWidgetItem()
                    self.table.setItem(row, 0, item)
                item.setText(str(start_num + (row - start_row)))

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
            for _ in range(10): self.add_row()
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

            if lines[0].startswith("序号"):
                lines = lines[1:]
            
            self.table.setRowCount(0)
            self.table.setUpdatesEnabled(False)
            
            for line in lines:
                parts = [p.strip() for p in line.split("/")]
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
    
    # ================= 绑定拖拽序号核心逻辑 =================
    # 当单元格数据发生变化时，触发递增计算
    w.table.itemChanged.connect(w.on_table_data_changed)
    
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
