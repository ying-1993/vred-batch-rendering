# 任务信息编辑器 - 独立桌面工具（支持草稿保存、Excel粘贴、自定义列宽）
import sys
import os
import json
from PySide6 import QtWidgets, QtCore, QtGui

OUTPUT_TXT_PATH = r"D:/VRED_Renders/batch_tasks.txt"
DRAFT_JSON_PATH = r"D:/VRED_Renders/batch_tasks_draft.json"

COLUMNS = ["序号", "文件夹", "摄像机", "视点", "隔离", "变量"]
# 根据要求设定的列宽（大约换算成像素）
COL_WIDTHS = [50, 70, 120, 300, 200, 200] 

class TaskEditor(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VRED 批量渲染任务编辑器 v2.1")
        self.resize(1100, 600) # 加宽窗口以容纳较宽的列

        layout = QtWidgets.QVBoxLayout(self)

        # ================= 工具栏 =================
        toolbar = QtWidgets.QHBoxLayout()
        
        self.btn_add = QtWidgets.QPushButton("添加1行")
        self.btn_add.clicked.connect(self.add_row)
        toolbar.addWidget(self.btn_add)

        self.btn_add_10 = QtWidgets.QPushButton("批量添加10行")
        self.btn_add_10.clicked.connect(self.add_10_rows)
        toolbar.addWidget(self.btn_add_10)

        self.btn_del = QtWidgets.QPushButton("删除选中行")
        self.btn_del.clicked.connect(self.delete_rows)
        toolbar.addWidget(self.btn_del)

        self.btn_clear = QtWidgets.QPushButton("清空全部")
        self.btn_clear.clicked.connect(self.clear_all)
        toolbar.addWidget(self.btn_clear)

        toolbar.addStretch() # 弹簧，把后面的按钮推到右边

        self.btn_save_draft = QtWidgets.QPushButton("保存草稿")
        self.btn_save_draft.clicked.connect(self.save_draft)
        toolbar.addWidget(self.btn_save_draft)

        self.btn_load_draft = QtWidgets.QPushButton("读取草稿")
        self.btn_load_draft.clicked.connect(self.load_draft)
        toolbar.addWidget(self.btn_load_draft)

        self.btn_save = QtWidgets.QPushButton("导出为 TXT")
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_txt)
        toolbar.addWidget(self.btn_save)

        layout.addLayout(toolbar)

        # ================= 表格区域 =================
        self.table = QtWidgets.QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        
        # 设置自定义列宽
        header = self.table.horizontalHeader()
        for i, width in enumerate(COL_WIDTHS):
            if i < 4:
                self.table.setColumnWidth(i, width)
            else:
                # 最后两列（隔离、变量）自动拉伸填满剩余空间
                header.setSectionResizeMode(i, QtWidgets.QHeaderView.Stretch)
                
        # 允许选择多个单元格
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ContiguousSelection)
        layout.addWidget(self.table)

        # ================= 状态栏 =================
        self.status = QtWidgets.QLabel("就绪。支持从Excel直接复制多行多列，点击表格后按 Ctrl+V 粘贴。")
        self.status.setStyleSheet("color: #555;")
        layout.addWidget(self.status)

        # 默认加几行方便填写
        for _ in range(10):
            self.add_row()

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        defaults = ["", "", "无", "无", "无", "无"]
        for col, val in enumerate(defaults):
            item = QtWidgets.QTableWidgetItem(val)
            self.table.setItem(row, col, item)

    def add_10_rows(self):
        self.table.setUpdatesEnabled(False) # 暂停刷新，加速插入
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

    # ================= 核心功能：支持从Excel多行粘贴 =================
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

        # 获取当前选中的起始单元格
        current = self.table.currentItem()
        if not current:
            start_row = 0
            start_col = 0
        else:
            start_row = current.row()
            start_col = current.column()

        # 按行拆分（处理不同系统的换行符）
        lines = text.strip().split('\n')
        
        self.table.setUpdatesEnabled(False)
        for r_offset, line in enumerate(lines):
            # Excel复制出来的列之间是制表符 \t
            cells = line.split('\t')
            
            target_row = start_row + r_offset
            
            # 如果行数不够，自动增加
            if target_row >= self.table.rowCount():
                self.add_row()

            for c_offset, cell_text in enumerate(cells):
                target_col = start_col + c_offset
                # 如果列数超出，忽略多余的列
                if target_col < self.table.columnCount():
                    item = self.table.item(target_row, target_col)
                    if not item:
                        item = QtWidgets.QTableWidgetItem()
                        self.table.setItem(target_row, target_col, item)
                    item.setText(cell_text.strip())
                    
        self.table.setUpdatesEnabled(True)
        self.status.setText(f"成功粘贴 {len(lines)} 行数据")

    # ================= 数据保存与加载 =================
    def save_draft(self):
        """保存为 JSON 格式，下次可以继续编辑"""
        try:
            dir_name = os.path.dirname(DRAFT_JSON_PATH)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            
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
                if not is_empty: # 只保存非空行
                    data.append(row_data)

            with open(DRAFT_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            self.status.setText(f"草稿已保存: {DRAFT_JSON_PATH}")
        except Exception as e:
            self.status.setText(f"草稿保存失败: {e}")

    def load_draft(self):
        """读取 JSON 草稿"""
        if not os.path.exists(DRAFT_JSON_PATH):
            self.status.setText("未找到草稿文件，请先保存草稿。")
            return
        try:
            with open(DRAFT_JSON_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.table.setRowCount(0)
            self.table.setUpdatesEnabled(False)
            for row_data in data:
                row = self.table.rowCount()
                self.table.insertRow(row)
                for col, val in enumerate(row_data):
                    if col < self.table.columnCount():
                        self.table.setItem(row, col, QtWidgets.QTableWidgetItem(val))
            # 补一点空行方便继续写
            for _ in range(10): self.add_row()
            self.table.setUpdatesEnabled(True)
            
            self.status.setText(f"已读取草稿，共 {self.table.rowCount()} 行")
        except Exception as e:
            self.status.setText(f"读取草稿失败: {e}")

    def save_txt(self):
        """导出供 VRED 插件读取的 TXT"""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出任务 TXT", OUTPUT_TXT_PATH, "Text Files (*.txt)")
        if not path:
            return

        try:
            dir_name = os.path.dirname(path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
                
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
                        continue # 跳过全空行
                        
                    f.write("/".join(vals) + "\n")
                    count += 1
                    
            self.status.setText(f"成功导出 {count} 条任务到: {path}")
        except Exception as e:
            self.status.setText(f"导出失败: {e}")


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = TaskEditor()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
