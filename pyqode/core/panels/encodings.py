"""
Contains a panel to manage unicode decoding/encoding errors.

"""
from pyqode.core.api.panel import Panel
from pyqode.core.api.decoration import TextDecoration
from pyqode.core.qt import QtCore, QtGui, QtWidgets
from pyqode.core.ui.pnl_encoding_ui import Ui_Form


class EncodingPanel(Panel):
    """
    This panel display a warning in case encoding/decoding error and
    give the user the possibility to try out another encoding, to edit any way
    or to close the editor.

    The panel is automatically shown by
    :class:`pyqode.core.managers.FileManager` in case of error so that you
    don't have to worry about encoding issues. The only think you might do
    is to provide to your user a way to specify the default encoding, i.e. the
    one that is tried before showing this panel.

    The panel is a simple widget with a label describing the error, an encoding
    menu and 3 buttons: ``Retry``, ``Edit`` anyway and ``Cancel``. It is
    strongly inspired by the GEdit encoding panel.

    You can change the background color and the label foreground color by
    setting up the ``color`` and ``foreground`` properties.

    It's up to the client code to handle cancel requests. To do that simply
    connect ``cancel_requested`` signal to remove the editor from your
    application.

    """
    #: Signal emitted when the user pressed on cancel. It is up to the client
    #: code to handle this event.
    cancel_requested = QtCore.Signal(object)

    _description = ('<html><head/><body><p><span style=" font-weight:600;">%s'
                    '</span></p><p><span style=" font-size:9pt;">'
                    'The file you opened has some invalid characters. '
                    'If you continue editing this file you could corrupt this '
                    'document. You can also choose another character encoding '
                    'and try again.</span></p></body></html>')

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self._color = value
        self._refresh_stylesheet()

    @property
    def foreground(self):
        return self._foreground

    @foreground.setter
    def foreground(self, value):
        self._foreground = value
        self._refresh_stylesheet()

    def _refresh_stylesheet(self):
        try:
            self._lbl_stylesheet = ('color: %s;background: %s' %
                                    (self._foreground.name(),
                                     self._color.name()))
            for lbl in self._labels:
                lbl.setStyleSheet(self._lbl_stylesheet)
        except AttributeError:
            pass

    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self._labels = [self.ui.label, self.ui.lblDescription]
        self._color = None
        self.color = QtGui.QColor('#8AADD4')
        self._foreground = None
        self.foreground = QtGui.QColor('#FFFFFF')
        self._deco = None
        self.ui.pushButtonRetry.clicked.connect(self._reload)
        self.ui.pushButtonEdit.clicked.connect(self._edit_anyway)
        self.ui.pushButtonCancel.clicked.connect(self._cancel)
        self.hide()

    def enable_caret_line(self, value=True):
        try:
            from pyqode.core.modes import CaretLineHighlighterMode

            mode = self.editor.modes.get(CaretLineHighlighterMode)
        except KeyError:
            pass
        else:
            mode.enabled = value

    def on_open_failed(self, path, encoding):
        self.enable_caret_line(False)
        self.ui.comboBoxEncodings.current_encoding = encoding
        self.ui.lblDescription.setText(
            self._description % ('There was a problem opening the file %r' %
                                 path))
        # load text as binary and mark it as red, user might make use the
        # binary to recognize the original encoding
        with open(path, 'rb') as file:
            content = str(file.read(16))
            print(content)
        # set plain text
        self.editor.setPlainText(
            content, self.editor.file.get_mimetype(path),
            self.editor.file.encoding)
        self.editor.setDocumentTitle(self.editor.file.name)
        self.editor.setWindowTitle(self.editor.file.name)

        # Delay because the editor might not have been shown yet
        QtCore.QTimer.singleShot(1, self.show)

    def show(self):
        super().show()
        self.editor.selectAll()
        self._deco = TextDecoration(self.editor.textCursor())
        self._deco.set_background(QtCore.Qt.red)
        self._deco.set_foreground(QtCore.Qt.black)
        self.editor.decorations.append(self._deco)
        cursor = self.editor.textCursor()
        cursor.clearSelection()
        cursor.setPosition(0)
        self.editor.setTextCursor(cursor)
        self.editor.setReadOnly(True)

    def paintEvent(self, event):
        """ Fills the panel background. """
        # pylint: disable=invalid-name
        super().paintEvent(event)
        if self.isVisible():
            # fill background
            painter = QtGui.QPainter(self)
            self._background_brush = QtGui.QBrush(self._color)
            painter.fillRect(event.rect(), self._background_brush)

    def _reload(self):
        self.hide()
        self.editor.decorations.remove(self._deco)
        self.editor.setReadOnly(False)
        self.enable_caret_line(True)
        self.editor.file.open(
            self.editor.file.path, self.ui.comboBoxEncodings.current_encoding)

    def _edit_anyway(self):
        self.hide()
        self.editor.decorations.remove(self._deco)
        self.editor.setReadOnly(False)
        self.enable_caret_line(True)

    def _cancel(self):
        self.hide()
        self.editor.decorations.remove(self._deco)
        self.enable_caret_line(True)
        self.cancel_requested.emit(self.editor)


if __name__ == '__main__':
    import locale
    import sys
    from pyqode.core.api import CodeEdit

    def simulate_open():
        pnl.on_open_failed(__file__, locale.getpreferredencoding())

    def simulate_save():
        pnl.on_save_failed(__file__, locale.getpreferredencoding())

    app = QtWidgets.QApplication(sys.argv)
    # app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    edit = CodeEdit()
    edit.setMinimumSize(800, 600)
    edit.file.open(__file__)
    pnl = EncodingPanel()
    edit.panels.append(pnl, pnl.Position.TOP)
    edit.show()
    simulate_open()
    QtCore.QTimer.singleShot(5000, simulate_save)
    app.exec_()