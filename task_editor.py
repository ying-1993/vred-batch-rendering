# 任务信息编辑器 - 独立桌面工具（断网可用）
import sys
import os
from PySide6 import QtWidgets, QtCore

OUTPUT_TXT_PATH = r"D:/VRED_Renders/batch_tasks.txt"

COLUMNS = ["序号", "文件夹", "摄像机", "视点", "隔离", "变量"]

class TaskEditor(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VRED 批量渲染任务编辑器")
        self.resize(900, 500)

        layout = QtWidgets.QVBoxLayout(self)

        # 表格
        self.table = QtWidgets.QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        layout.addWidget(self.table)

        # 按钮区
        btn_layout = QtWidgets.QHBoxLayout()

        self.btn_add = QtWidgets.QPushButton("添加行")
        self.btn_add.clicked.connect(self.add_row)
        btn_layout.addWidget(self.btn_add)

        self.btn_del = QtWidgets.QPushButton("删除选中行")
        self.btn_del.clicked.connect(self.delete_rows)
        btn_layout.addWidget(self.btn_del)

        self.btn_clear = QtWidgets.QPushButton("清空全部")
        self.btn_clear.clicked.connect(self.clear_all)
        btn_layout.addWidget(self.btn_clear)

        self.btn_save = QtWidgets.QPushButton("保存为 TXT")
        self.btn_save.clicked.connect(self.save_txt)
        btn_layout.addWidget(self.btn_save)

        self.btn_load = QtWidgets.QPushButton("加载 TXT")
        self.btn_load.clicked.connect(self.load_txt)
        btn_layout.addWidget(self.btn_load)

        layout.addLayout(btn_layout)

        # 状态栏
        self.status = QtWidgets.QLabel("就绪。默认值：隔离和变量填“无”可跳过。")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        # 默认加几行方便填写
        for _ in range(3):
            self.add_row()

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        defaults = ["", "", "无", "无", "无", "无"]
        for col, val in enumerate(defaults):
            item = QtWidgets.QTableWidgetItem(val)
            self.table.setItem(row, col, item)

    def delete_rows(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def clear_all(self):
        self.table.setRowCount(0)

    def save_txt(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "保存任务文件", OUTPUT_TXT_PATH, "Text Files (*.txt)")
        if not path:
            return

        try:
            dir_name = os.path.dirname(path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(path, 'w', encoding='utf-8-sig') as f:
                f.write("/".join(COLUMNS) + "\n")
                for row in range(self.table.rowCount()):
                    vals = []
                    for col in range(len(COLUMNS)):
                        item = self.table.item(row, col)
                        text = item.text().strip() if item else ""
                        vals.append(text if text else "无")
                    if all(v == "无" or v == "" for v in vals):
                        continue
                    f.write("/".join(vals) + "\n")
            self.status.setText(f"已保存: {path}")
        except Exception as e:
            self.status.setText(f"保存失败: {e}")

    def load_txt(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "加载任务文件", "", "Text Files (*.txt);;All Files (*)")
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                lines = [l.strip() for l in f if l.strip()]
            if not lines:
                self.status.setText("文件为空")
                return
            data_lines = lines[1:] if lines[0].startswith("序号") else lines
            self.table.setRowCount(0)
            for line in data_lines:
                parts = [p.strip() for p in line.split("/")]
                parts = (parts + ["无"] * len(COLUMNS))[:len(COLUMNS)]
                row = self.table.rowCount()
                self.table.insertRow(row)
                for col, val in enumerate(parts):
                    self.table.setItem(row, col, QtWidgets.QTableWidgetItem(val))
            self.status.setText(f"已加载 {self.table.rowCount()} 条任务: {path}")
        except Exception as e:
            self.status.setText(f"加载失败: {e}")


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = TaskEditor()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()