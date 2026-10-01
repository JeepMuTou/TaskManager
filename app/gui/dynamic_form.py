from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QHBoxLayout,
                               QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox, QLabel,
                               QPushButton, QListWidget, QListWidgetItem, QAbstractItemView, QScrollArea,
                               QFileDialog, QTextEdit)
from PySide6.QtCore import Qt

class DynamicForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.form_container = QWidget()
        self.form_layout = QFormLayout(self.form_container)
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        self.layout.addWidget(self.form_container)
        self.layout.addStretch()
        
        self.inputs = {}
        
    def build_form(self, schema_parameters: list, saved_params: dict, task_id: str = None, task_manager = None):
        """根据 schema 动态生成表单"""
        self.clear_form()
        self.inputs.clear()
        
        for param in schema_parameters:
            name = param.get("name")
            p_type = param.get("type")
            label = param.get("label", name)
            default = param.get("default")
            
            # 使用保存的值，如果没有则使用默认值
            current_value = saved_params.get(name, default)
            
            widget = None
            if p_type == "string":
                widget = QLineEdit()
                if current_value is not None:
                    widget.setText(str(current_value))
            elif p_type == "password":
                widget = QLineEdit()
                widget.setEchoMode(QLineEdit.Password)
                if current_value is not None:
                    widget.setText(str(current_value))
            elif p_type == "text_area":
                widget = QTextEdit()
                widget.setMaximumHeight(100)
                if current_value is not None:
                    widget.setPlainText(str(current_value))
            elif p_type == "int":
                widget = QSpinBox()
                widget.setRange(0, 999999)
                if current_value is not None:
                    widget.setValue(int(current_value))
            elif p_type == "float":
                widget = QDoubleSpinBox()
                widget.setRange(0.0, 999999.0)
                widget.setDecimals(4)
                if current_value is not None:
                    widget.setValue(float(current_value))
            elif p_type in ["file", "directory"]:
                widget = QWidget()
                h_layout = QHBoxLayout(widget)
                h_layout.setContentsMargins(0, 0, 0, 0)
                txt_path = QLineEdit()
                if current_value is not None:
                    txt_path.setText(str(current_value))
                btn_browse = QPushButton("浏览...")
                h_layout.addWidget(txt_path, stretch=1)
                h_layout.addWidget(btn_browse)
                
                def make_browse_handler(txt_widget, is_dir):
                    def handler():
                        if is_dir:
                            path = QFileDialog.getExistingDirectory(widget, "选择文件夹", txt_widget.text())
                            if path: txt_widget.setText(path)
                        else:
                            path, _ = QFileDialog.getOpenFileName(widget, "选择文件", txt_widget.text())
                            if path: txt_widget.setText(path)
                    return handler
                    
                btn_browse.clicked.connect(make_browse_handler(txt_path, p_type == "directory"))
                self.inputs[name] = {"widget": widget, "txt_path": txt_path, "type": p_type}
                lbl = QLabel(label)
                lbl.setContentsMargins(0, 5, 0, 0)
                self.form_layout.addRow(lbl, widget)
                continue
            elif p_type == "bool":
                widget = QCheckBox()
                if current_value is not None:
                    widget.setChecked(bool(current_value))
            elif p_type == "choice":
                widget = QComboBox()
                options = param.get("options", [])
                widget.addItems(options)
                if current_value in options:
                    widget.setCurrentText(str(current_value))
            elif p_type == "dynamic_choice":
                widget = QWidget()
                h_layout = QHBoxLayout(widget)
                h_layout.setContentsMargins(0, 0, 0, 0)
                
                combo = QComboBox()
                if current_value is not None:
                    combo.addItem(str(current_value))
                    combo.setCurrentText(str(current_value))
                
                btn_fetch = QPushButton("刷新选项")
                h_layout.addWidget(combo, stretch=1)
                h_layout.addWidget(btn_fetch)
                
                if task_manager and task_id:
                    def make_dchoice_handler(t_id, p_name, cb, saved_val):
                        def handler():
                            opts = task_manager.get_dynamic_options(t_id, p_name)
                            cb.clear()
                            for opt in opts:
                                cb.addItem(str(opt))
                            if saved_val and str(saved_val) in [str(o) for o in opts]:
                                cb.setCurrentText(str(saved_val))
                        return handler
                    btn_fetch.clicked.connect(make_dchoice_handler(task_id, name, combo, current_value))
                
                self.inputs[name] = {"widget": widget, "combo": combo, "type": p_type}
                lbl = QLabel(label)
                lbl.setContentsMargins(0, 5, 0, 0)
                self.form_layout.addRow(lbl, widget)
                continue
            elif p_type == "dynamic_multichoice":
                # 使用原生 QCheckBox，避免 QListWidget 的 QSS 样式冲突导致打钩图标消失
                widget = QWidget()
                vbox = QVBoxLayout(widget)
                vbox.setContentsMargins(0, 0, 0, 0)
                
                btn_fetch = QPushButton("获取选项")
                
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setMaximumHeight(150)
                scroll.setStyleSheet("QScrollArea { border: 1px solid #dcdde1; border-radius: 4px; background: white; }")
                
                container = QWidget()
                container.setObjectName("ContainerWidget")
                container.setStyleSheet("QWidget#ContainerWidget { background: transparent; }")
                container_layout = QVBoxLayout(container)
                container_layout.setContentsMargins(5, 5, 5, 5)
                container_layout.setSpacing(2)
                container_layout.setAlignment(Qt.AlignTop)
                scroll.setWidget(container)
                
                h_btn_layout = QHBoxLayout()
                h_btn_layout.setContentsMargins(0, 0, 0, 0)
                h_btn_layout.addWidget(btn_fetch, alignment=Qt.AlignTop)
                h_btn_layout.addStretch()
                
                vbox.addLayout(h_btn_layout)
                vbox.addWidget(scroll, stretch=1)
                
                # 存放真正的 QCheckBox
                checkboxes = []
                
                # 恢复之前保存的选项 (current_value 应该是一个 list)
                saved_list = current_value if isinstance(current_value, list) else []
                for val in saved_list:
                    chk = QCheckBox(str(val))
                    chk.setChecked(True)
                    container_layout.addWidget(chk)
                    checkboxes.append(chk)
                
                # 绑定按钮点击事件
                if task_manager and task_id:
                    def make_fetch_handler(t_id, p_name, layout, cbs, saved_opts):
                        def handler():
                            opts = task_manager.get_dynamic_options(t_id, p_name)
                            # 清理旧的 CheckBox
                            for i in reversed(range(layout.count())):
                                w = layout.itemAt(i).widget()
                                if w:
                                    w.setParent(None)
                                    w.deleteLater()
                            cbs.clear()
                            
                            for opt in opts:
                                chk = QCheckBox(str(opt))
                                if str(opt) in saved_opts:
                                    chk.setChecked(True)
                                layout.addWidget(chk)
                                cbs.append(chk)
                        return handler
                    btn_fetch.clicked.connect(make_fetch_handler(task_id, name, container_layout, checkboxes, saved_list))
                
                # 记录 widget 和 checkboxes
                self.inputs[name] = {"widget": widget, "checkboxes": checkboxes, "type": p_type}
                lbl = QLabel(label)
                lbl.setContentsMargins(0, 5, 0, 0)
                self.form_layout.addRow(lbl, widget)
                continue
            elif p_type == "dynamic_editable_list":
                widget = QWidget()
                vbox = QVBoxLayout(widget)
                vbox.setContentsMargins(0, 0, 0, 0)
                
                h_input_layout = QHBoxLayout()
                h_input_layout.setContentsMargins(0, 0, 0, 0)
                txt_input = QLineEdit()
                btn_add = QPushButton("录入")
                h_input_layout.addWidget(txt_input)
                h_input_layout.addWidget(btn_add)
                
                vbox.addLayout(h_input_layout)
                
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setStyleSheet("QScrollArea { border: 1px solid #dcdde1; border-radius: 4px; background: white; }")
                
                container = QWidget()
                # 移除了透明背景样式，防止破坏 QCheckBox 原生渲染
                container_layout = QVBoxLayout(container)
                container_layout.setContentsMargins(5, 5, 5, 5)
                container_layout.setSpacing(2)
                container_layout.setAlignment(Qt.AlignTop)
                scroll.setWidget(container)
                
                vbox.addWidget(scroll, stretch=1)
                
                list_items = []
                
                def create_add_item(l_items, t_input, c_layout):
                    def add_item(val=None, text_override=None):
                        text = text_override if text_override is not None else t_input.text().strip()
                        if not text:
                            return
                        for item in l_items:
                            if item["value"] == text:
                                t_input.clear()
                                return
                                
                        row_widget = QWidget()
                        row_layout = QHBoxLayout(row_widget)
                        row_layout.setContentsMargins(0, 0, 0, 0)
                        
                        chk = QCheckBox(text)
                        chk.setChecked(True)
                        
                        btn_del = QPushButton("x")
                        btn_del.setFixedWidth(24)
                        btn_del.setStyleSheet("QPushButton { border: none; color: red; font-weight: bold; } QPushButton:hover { background: #fee; }")
                        
                        row_layout.addWidget(chk)
                        row_layout.addStretch()
                        row_layout.addWidget(btn_del)
                        
                        c_layout.addWidget(row_widget)
                        
                        item_data = {"checkbox": chk, "widget": row_widget, "value": text}
                        l_items.append(item_data)
                        
                        def delete_item(checked=False, i_data=item_data):
                            if i_data in l_items:
                                l_items.remove(i_data)
                            i_data["widget"].deleteLater()
                            
                        btn_del.clicked.connect(delete_item)
                        if text_override is None:
                            t_input.clear()
                    return add_item
                
                add_item = create_add_item(list_items, txt_input, container_layout)

                        
                btn_add.clicked.connect(add_item)
                txt_input.returnPressed.connect(add_item)
                
                saved_list = current_value if isinstance(current_value, list) else []
                if isinstance(saved_list, str):
                    if saved_list:
                        saved_list = [saved_list]
                    else:
                        saved_list = []
                for val in saved_list:
                    add_item(text_override=str(val))
                    
                self.inputs[name] = {"widget": widget, "list_items": list_items, "type": p_type}
                lbl = QLabel(label)
                lbl.setContentsMargins(0, 5, 0, 0)
                self.form_layout.addRow(lbl, widget)
                continue
            elif p_type == "dynamic_info":
                # 添加纯展示用的动态文本控件
                widget = QWidget()
                h_layout = QHBoxLayout(widget)
                h_layout.setContentsMargins(0, 0, 0, 0)
                
                lbl_info = QLabel("尚未获取...")
                lbl_info.setStyleSheet("color: #2f3640; padding: 4px; border: 1px solid #dcdde1; border-radius: 4px; background: #f5f6fa;")
                
                btn_refresh = QPushButton("刷新")
                btn_refresh.setCursor(Qt.PointingHandCursor)
                
                h_layout.addWidget(lbl_info, stretch=1)
                h_layout.addWidget(btn_refresh)
                
                if task_manager and task_id:
                    def make_info_handler(t_id, p_name, lbl):
                        def handler():
                            opts = task_manager.get_dynamic_options(t_id, p_name)
                            if opts and len(opts) > 0:
                                lbl.setText(str(opts[0]))
                            else:
                                lbl.setText("获取失败或无数据")
                        return handler
                    btn_refresh.clicked.connect(make_info_handler(task_id, name, lbl_info))
                
                self.inputs[name] = {"widget": widget, "type": p_type}
                lbl = QLabel(label)
                lbl.setContentsMargins(0, 5, 0, 0)
                self.form_layout.addRow(lbl, widget)
                continue
            
            if widget:
                lbl = QLabel(label)
                lbl.setContentsMargins(0, 5, 0, 0)
                self.form_layout.addRow(lbl, widget)
                self.inputs[name] = {"widget": widget, "type": p_type}
                
    def get_values(self) -> dict:
        """获取当前表单的所有值"""
        values = {}
        for name, data in self.inputs.items():
            widget = data.get("widget")
            p_type = data.get("type")
            
            if not widget:
                continue
                
            if p_type in ["string", "password"]:
                values[name] = widget.text()
            elif p_type == "text_area":
                values[name] = widget.toPlainText()
            elif p_type in ["int", "float"]:
                values[name] = widget.value()
            elif p_type == "bool":
                values[name] = widget.isChecked()
            elif p_type == "choice":
                values[name] = widget.currentText()
            elif p_type in ["file", "directory"]:
                values[name] = data["txt_path"].text()
            elif p_type == "dynamic_choice":
                values[name] = data["combo"].currentText()
            elif p_type == "dynamic_multichoice":
                # 获取所有勾选的项
                selected = []
                for chk in data["checkboxes"]:
                    if chk.isChecked():
                        selected.append(chk.text())
                values[name] = selected
            elif p_type == "dynamic_editable_list":
                selected = []
                for item in data["list_items"]:
                    if item["checkbox"].isChecked():
                        selected.append(item["value"])
                values[name] = selected
            elif p_type == "dynamic_info":
                # 只读展示，不需要把值保存进配置
                pass
                
        return values
        
    def clear_form(self):
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
