import os
import time

from PyQt5.QtWidgets import (QApplication, QMainWindow, QAction, QFileSystemModel,
                             QTreeView, QSplitter, QTextEdit, QWidget, QVBoxLayout,
                             QHBoxLayout, QPlainTextEdit, QFileDialog)
from PyQt5.QtCore import Qt, QDir, QRect, QSize
from PyQt5.QtGui import QTextCursor, QPainter, QTextBlock, QColor
import sys
# from auto_lexical_analyzer import Lexer  # 导入词法分析模块 -- 自动


from non_auto_lexical_analyzer import Lexer  # 导入词法分析模块 -- 手动
from practice.tokenType import TokenCategory


# LineNumberArea 类用于显示代码编辑器中的行号区域
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)  # 初始化 QWidget，父类是 editor
        self.editor = editor  # 保存编辑器对象

    def sizeHint(self):
        # 返回行号区域的大小提示，宽度是行号区域的宽度，高度为 0（高度由编辑器的内容决定）
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        # 画出行号区域，调用编辑器的绘制方法
        self.editor.line_number_area_paint_event(event)


# CodeEditor 类是自定义的代码编辑器，继承自 QPlainTextEdit
class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()  # 初始化父类 QPlainTextEdit
        self.line_number_area = LineNumberArea(self)  # 创建一个行号区域
        self.blockCountChanged.connect(self.update_line_number_area_width)  # 行数改变时更新行号区域宽度
        self.updateRequest.connect(self.update_line_number_area)  # 内容更新时更新行号区域
        self.update_line_number_area_width()  # 初始化行号区域宽度

        # 设置更大的字体
        font = self.font()  # 获取当前字体
        font.setPointSize(12)  # 设置字体大小为 12
        self.setFont(font)  # 应用新字体

    def line_number_area_width(self):
        # 计算行号区域的宽度，基于当前行数来动态决定
        digits = 1  # 默认最小宽度，1 位数字
        max_lines = max(1, self.blockCount())  # 获取当前行数，最少为 1
        while max_lines >= 10:  # 每增加一位数字，宽度就增加
            max_lines //= 10
            digits += 1
        # 增加基础宽度并添加间距（20 为基本宽度，后面部分是基于字体的宽度计算）
        space = 20 + self.fontMetrics().horizontalAdvance('9') * (digits + 1)
        return space

    def update_line_number_area_width(self):
        # 更新视口的边距，确保行号区域有足够的空间
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        # 更新行号区域，处理滚动或内容更新
        if dy:
            self.line_number_area.scroll(0, dy)  # 如果是垂直滚动，移动行号区域
        else:
            # 更新可见区域的行号区域
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        # 如果视口区域发生变化，更新行号区域宽度
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event):
        # 重写窗口大小改变事件，调整行号区域大小
        super().resizeEvent(event)
        cr = self.contentsRect()  # 获取内容区域的矩形
        # 设置行号区域的大小和位置
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(),
                  self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        # 绘制行号区域
        painter = QPainter(self.line_number_area)  # 创建绘图工具
        # 使用更明显的背景色
        painter.fillRect(event.rect(), QColor("#d0d0d0"))

        # 设置行号字体样式
        painter.setFont(self.font())
        painter.setPen(QColor("#404040"))  # 设置字体颜色

        block = self.firstVisibleBlock()  # 获取第一个可见的块（文本行）
        block_number = block.blockNumber()  # 获取该块的行号
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()  # 获取该行的顶部位置
        bottom = top + self.blockBoundingRect(block).height()  # 获取该行的底部位置

        # 遍历所有可见的文本块，绘制行号
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)  # 获取当前行的行号
                # 在行号区域绘制行号，添加阴影效果
                painter.drawText(5, int(top),
                                 self.line_number_area.width() - 10,
                                 self.fontMetrics().height(),
                                 Qt.AlignRight | Qt.AlignVCenter,
                                 number)

            block = block.next()  # 获取下一个文本块
            top = bottom  # 更新当前行的位置
            bottom = top + self.blockBoundingRect(block).height()  # 更新当前行底部位置
            block_number += 1  # 行号加 1


# 保存结果到指定目录
def save_analysis_results(tokens, errors):
    # 确保目录存在
    os.makedirs("./token", exist_ok=True)
    os.makedirs("./error", exist_ok=True)

    # 保存Token
    with open(f"./token/tokens.txt", "w") as f:
        for token in tokens:
            f.write(f"{token.line}:{token.column}\t{token.token_type.category.value}\t{token.lexeme}\n")

    # 保存错误
    with open(f"./error/errors.txt", "w") as f:
        for error in errors:
            f.write(f"[Line {error.line}:{error.column}] 无效Token: {error.lexeme}\n")


class CompilerIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("C语言编译器")
        self.setup_ui()
        self.connect_actions()

    # 初始化ui界面
    def setup_ui(self):
        # 创建菜单栏
        menu_bar = self.menuBar()
        self.setup_menu()  # 设置自定义的菜单选项
        menu_bar.addMenu("语法分析")  # 添加“语法分析”菜单
        edit_menu = menu_bar.addMenu("编辑")  # 添加“编辑”菜单
        view_menu = menu_bar.addMenu("视图")  # 添加“视图”菜单
        menu_bar.addMenu("中间代码")  # 添加“中间代码”菜单
        menu_bar.addMenu("目标代码")  # 添加“目标代码”菜单
        menu_bar.addMenu("相关算法")  # 添加“相关算法”菜单
        menu_bar.addMenu("关于")  # 添加“关于”菜单

        # 创建“编辑”菜单项
        copy_action = QAction("复制", self)  # 创建复制动作
        paste_action = QAction("粘贴", self)  # 创建粘贴动作
        cut_action = QAction("剪切", self)  # 创建剪切动作
        undo_action = QAction("撤销", self)  # 创建撤销动作
        redo_action = QAction("重做", self)  # 创建重做动作
        delete_action = QAction("删除", self)  # 创建删除动作
        select_all_action = QAction("全选", self)  # 创建全选动作

        # 将这些动作添加到“编辑”菜单
        edit_menu.addAction(copy_action)
        edit_menu.addAction(paste_action)
        edit_menu.addAction(cut_action)
        edit_menu.addSeparator()  # 添加分隔符
        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)
        edit_menu.addSeparator()  # 添加分隔符
        edit_menu.addAction(delete_action)
        edit_menu.addAction(select_all_action)

        # 创建“视图”菜单项（可以选择显示哪些视图）
        self.show_source_action = QAction("源代码编辑区", self, checkable=True, checked=True)  # 是否显示源代码编辑区
        self.show_analysis_action = QAction("分析结果区", self, checkable=True, checked=True)  # 是否显示分析结果区
        self.show_console_action = QAction("控制台输出区", self, checkable=True, checked=True)  # 是否显示控制台输出区

        # 将这些视图操作添加到“视图”菜单
        view_menu.addAction(self.show_source_action)
        view_menu.addAction(self.show_analysis_action)
        view_menu.addAction(self.show_console_action)

        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)  # 设置中央部件
        layout = QVBoxLayout(central_widget)  # 垂直布局

        # 左侧区域（包含文件树，分为上下两部分）
        left_splitter = QSplitter(Qt.Vertical)

        # 当前目录文件树
        self.file_model1 = QFileSystemModel()
        root_path = QDir.currentPath()  # 获取当前目录路径
        self.file_model1.setRootPath(root_path)

        self.tree1 = QTreeView()  # 创建文件树视图
        self.tree1.setModel(self.file_model1)  # 设置模型
        self.tree1.setRootIndex(self.file_model1.index(root_path))  # 设置根目录
        self.tree1.setSortingEnabled(True)  # 启用排序
        left_splitter.addWidget(self.tree1)  # 添加文件树到左侧区域

        # 磁盘文件树
        self.file_model2 = QFileSystemModel()
        self.file_model2.setRootPath("")  # 设置磁盘文件树的根路径为空

        self.tree2 = QTreeView()  # 创建第二个文件树视图
        self.tree2.setModel(self.file_model2)  # 设置模型
        self.tree2.setRootIndex(self.file_model2.index(""))  # 设置根目录为空
        left_splitter.addWidget(self.tree2)  # 添加文件树到左侧区域

        # 右侧区域（包含代码编辑区和控制台）
        self.right_splitter = QSplitter(Qt.Vertical)
        self.sub_splitter = QSplitter(Qt.Horizontal)

        # 自定义的代码编辑器（用于源代码编辑）
        self.text_edit_top = CodeEditor()
        self.text_edit_top.setPlaceholderText("源代码编辑区")  # 设置占位符文本
        self.text_edit_top.setStyleSheet("""  # 设置代码编辑器的样式
                    background-color: #f7f7f7;
                    QScrollBar:vertical {
                        border: none;
                        background: #f0f0f0;
                        width: 10px;
                        margin: 0px 0px 0px 0px;
                    }
                    QScrollBar::handle:vertical {
                        background: #888;
                        min-height: 20px;
                        border-radius: 5px;
                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        background: none;
                        border: none;
                    }
                    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                        background: none;
                    }
                """)

        # 创建分析结果区（只读文本编辑器）
        self.text_edit_right = QTextEdit()
        self.text_edit_right.setPlaceholderText("分析结果区")  # 设置占位符文本
        self.text_edit_right.setStyleSheet("background-color: #e8ffe8;")  # 设置背景色
        self.text_edit_right.setReadOnly(True)  # 设置只读

        # 创建控制台输出区（只读文本编辑器）
        self.text_edit_bottom = QTextEdit()
        self.text_edit_bottom.setPlaceholderText("控制台输出区")  # 设置占位符文本
        self.text_edit_bottom.setStyleSheet("background-color: #eef5ff;")  # 设置背景色
        self.text_edit_bottom.setReadOnly(True)  # 设置只读

        # 将编辑器和结果区、控制台区放入分割器
        self.sub_splitter.addWidget(self.text_edit_top)  # 添加源代码编辑器
        self.sub_splitter.addWidget(self.text_edit_right)  # 添加分析结果区
        self.right_splitter.addWidget(self.sub_splitter)
        self.right_splitter.addWidget(self.text_edit_bottom)  # 添加控制台输出区

        # 设置初始分割比例
        self.sub_splitter.setSizes([1, 1])  # 设置左右分割器比例
        self.right_splitter.setSizes([2, 1])  # 设置上下分割器比例

        # 总分割器（左右布局）
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(left_splitter)  # 添加左侧区域
        main_splitter.addWidget(self.right_splitter)  # 添加右侧区域

        layout.addWidget(main_splitter)  # 将主分割器添加到布局中

        # 设置可伸缩比例
        left_splitter.setStretchFactor(0, 2)  # 设置左侧分割器的伸缩比例
        left_splitter.setStretchFactor(1, 1)  # 设置左侧第二个分割器的伸缩比例
        main_splitter.setStretchFactor(0, 1)  # 设置主分割器的伸缩比例
        main_splitter.setStretchFactor(1, 2)  # 设置主分割器的伸缩比例
        self.right_splitter.setStretchFactor(0, 2)  # 设置右侧分割器的伸缩比例
        self.right_splitter.setStretchFactor(1, 1)  # 设置右侧第二个分割器的伸缩比例

        # 绑定菜单动作到相应的方法
        copy_action.triggered.connect(self.text_edit_top.copy)  # 复制操作
        paste_action.triggered.connect(self.text_edit_top.paste)  # 粘贴操作
        cut_action.triggered.connect(self.text_edit_top.cut)  # 剪切操作
        undo_action.triggered.connect(self.text_edit_top.undo)  # 撤销操作
        redo_action.triggered.connect(self.text_edit_top.redo)  # 重做操作
        delete_action.triggered.connect(self.text_edit_top.clear)  # 删除操作
        select_all_action.triggered.connect(self.text_edit_top.selectAll)  # 全选操作

        # 视图菜单绑定
        self.show_source_action.triggered.connect(self.toggle_source_editor)  # 显示/隐藏源代码编辑区
        self.show_analysis_action.triggered.connect(self.toggle_analysis_area)  # 显示/隐藏分析结果区
        self.show_console_action.triggered.connect(self.toggle_console)  # 显示/隐藏控制台输出区

    """控制各个区域的可见性"""

    def toggle_source_editor(self, checked):
        """切换源代码编辑区的可见性"""
        self.text_edit_top.setVisible(checked)  # 设置源代码编辑区的可见性
        if checked and self.text_edit_right.isVisible():  # 如果显示源代码编辑区且分析区可见
            self.sub_splitter.setSizes([1, 1])  # 设置分割器比例
        elif checked:
            self.sub_splitter.setSizes([1, 0])  # 如果只显示源代码编辑区
        else:
            if self.text_edit_right.isVisible():  # 如果分析区可见
                self.sub_splitter.setSizes([0, 1])  # 只显示分析区

    def toggle_analysis_area(self, checked):
        """切换分析结果区的可见性"""
        self.text_edit_right.setVisible(checked)  # 设置分析结果区的可见性
        if checked and self.text_edit_top.isVisible():  # 如果显示分析结果区且源代码编辑区可见
            self.sub_splitter.setSizes([1, 1])  # 设置分割器比例
        elif checked:
            self.sub_splitter.setSizes([0, 1])  # 如果只显示分析结果区
        else:
            if self.text_edit_top.isVisible():  # 如果源代码编辑区可见
                self.sub_splitter.setSizes([1, 0])  # 只显示源代码编辑区

    def toggle_console(self, checked):
        """切换控制台输出区的可见性"""
        self.text_edit_bottom.setVisible(checked)  # 设置控制台输出区的可见性
        if checked:
            self.right_splitter.setSizes([2, 1])  # 设置右侧分割器的比例
        else:
            self.right_splitter.setSizes([1, 0])  # 如果不显示控制台输出区

    # 导航栏
    def setup_menu(self):
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")
        self.open_action = QAction("打开", self)  # 保存为实例变量
        self.save_action = QAction("保存", self)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)

        # 词法分析菜单
        analysis_menu = menubar.addMenu("词法分析")
        self.lex_action = QAction("执行分析", self)
        analysis_menu.addAction(self.lex_action)

    # 文件操作
    def connect_actions(self):
        # 直接使用保存的动作实例
        self.open_action.triggered.connect(self.open_file)
        self.save_action.triggered.connect(self.save_file)
        self.lex_action.triggered.connect(self.run_lexical_analysis)

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "打开源代码文件", "",
            "C Files (*.c *.h);;Text Files (*.txt);;All Files (*)"
        )
        if filename:
            with open(filename, 'r', encoding='utf-8-sig') as f:
                self.text_edit_top.setPlainText(f.read())

    def save_file(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存文件", "",
            "C Files (*.c *.h);;Text Files (*.txt);;All Files (*)"
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.text_edit_top.toPlainText())

    # 执行词法分析
    def run_lexical_analysis(self):
        try:
            # 获取源代码
            code = self.text_edit_top.toPlainText()

            # 执行词法分析
            lexer = Lexer()
            tokens, errors = lexer.tokenize(code)
            print(errors)
            # 保存结果到文件
            save_analysis_results(tokens, errors)

            # 显示结果
            self.display_tokens(tokens)
            self.display_errors(errors)

            # 控制台输出
            self.text_edit_bottom.append(f"分析完成！发现{len(errors)}个错误")
        except Exception as e:
            self.text_edit_bottom.setTextColor(QColor("#D8000C"))
            self.text_edit_bottom.append(f"分析错误：{str(e)}")
            # 记录错误日志
            error_msg = f"[{time.ctime()}] Lexer Error: {str(e)}\n"
            with open("error_log.txt", "a") as f:
                f.write(error_msg)

    # 执行语法分析
    def run_syntax_analysis(self):
        pass

    # 展示分析结果 -- token表
    def display_tokens(self, tokens):
        self.text_edit_right.clear()

        # 设置表格样式
        self.text_edit_right.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #D3D3D3;
                padding: 5px;
            }
        """)

        # 表头格式
        header = (
            f"<table style='width:100%; border-collapse: collapse;'>"
            f"<tr style='background-color: #F5F5F5; border-bottom: 2px solid #D3D3D3;'>"
            f"<th style='padding: 6px; text-align: left; width: 60px;'>row</th>"
            f"<th style='padding: 6px; text-align: left; width: 60px;'>col</th>"
            f"<th style='padding: 6px; text-align: left; width: 120px;'>type</th>"
            f"<th style='padding: 6px; text-align: left; width: 60px;'>code</th>"
            f"<th style='padding: 6px; text-align: left;'>word</th>"
            f"</tr>"
        )

        # 数据行
        rows = []
        for token in tokens:
            print(token)
            color = "#333333"
            if token.token_type.category == TokenCategory.KEYWORD:
                color = "#007ACC"  # 蓝色
            elif token.token_type.category == TokenCategory.OPERATOR:
                color = "#AF00DB"  # 紫色
            elif token.token_type.category == TokenCategory.DELIMITER:
                color = "#AF00DB"  # 绿色

            formatted_type = f"{token.token_type.category.value}"

            print(token.lexeme)

            row = (
                f"<tr style='border-bottom: 1px solid #EEEEEE;'>"
                f"<td style='padding: 6px; color: {color};'>{token.line}</td>"
                f"<td style='padding: 6px; color: {color};'>{token.column}</td>"
                f"<td style='padding: 6px; color: {color};'>{formatted_type}</td>"
                f"<td style='padding: 6px; color: {color};'>{token.token_type.code}</td>"
                f"<td style='padding: 6px; color: {color};'><code>{token.lexeme}</code></td>"
                f"</tr>"
            )
            rows.append(row)

        # 组合HTML
        html = f"""
            {header}
            {"".join(rows)}
            </table>
        """

        self.text_edit_right.setHtml(html)

    # 展示错误信息
    def display_errors(self, errors):
        self.text_edit_bottom.clear()
        for error in errors:
            self.text_edit_bottom.setTextColor(QColor("red"))
            # 如果 error.error_msg 存在，则显示详细错误信息，否则显示无效词素
            err_info = error.error_msg if error.error_msg else "无效词素"
            self.text_edit_bottom.append(
                f"错误：行 {error.line} 列 {error.column} - {err_info} [词素: {error.lexeme}]"
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ide = CompilerIDE()
    ide.show()
    sys.exit(app.exec_())
