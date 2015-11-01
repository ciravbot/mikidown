import datetime
from enum import Enum
import shlex
import subprocess

from PyQt4.QtGui import QDialog, QListView, QGridLayout, QAbstractItemDelegate, \
                        QComboBox, QWidget, QStandardItem, QStandardItemModel, \
                        QDialogButtonBox, QLabel, QLineEdit
from PyQt4.QtCore import Qt

from .utils import NOTE_EXTS, doesFileExist

#BANNED_COMMANDS={'rm', 'cp', 'mv', 'unlink', 'mkdir', 'rmdir'}

# --- CORE FUNCTIONALITY
class TitleType(Enum):
    FSTRING  = 0
    DATETIME = 1
    #COMMAND  = 2

def makeDefaultBody(title, dt_in_body_txt):
    dtnow = datetime.datetime.now()
    filled_title = makeTemplateTitle(TitleType.FSTRING, "{}", dtnow=dtnow, userinput=title)
    return makeTemplateBody(dt_in_body_txt=dt_in_body_txt)

def makeTemplateTitle(title_type, title, dtnow=None, userinput=""):
    if dtnow is None:
        dtnow = datetime.datetime.now()

    if title_type == TitleType.FSTRING:
        filled_title = title.format(userinput)
    elif title_type == TitleType.DATETIME:
        filled_title = dtnow.strftime(title).format(userinput)
    #elif title_type == TitleType.COMMAND:
    #    args = shlex.split(title)
    #    if args[0] in BANNED_COMMANDS:
    #        raise ValueError("{} contains banned command {}".format(args[0]))
    #    filled_title = subprocess.check_output(args).decode('utf-8')
    else:
        return
    return filled_title

def makeTemplateBody(filled_title, dt_in_body=True, dtnow=None,
        dt_in_body_fmt="%Y-%m-%d", dt_in_body_txt="Created {}", 
        userinput="", body=""):
    if dtnow is None:
        dtnow = datetime.datetime.now()

    if filled_title is None:
        return

    if dt_in_body is True:
        formatted_dt = dt_in_body_txt.format(dtnow.strftime(dt_in_body_fmt))
        return "# {}\n{}\n\n{}".format(filled_title, formatted_dt, body)
    else:
        return "# {}\n{}".format(filled_title, body)

# --- WIDGETS
COL_DATA = Qt.UserRole
COL_EXTRA_DATA = COL_DATA + 1

class EditTitleTemplateDialog(QDialog):
    def __init__(self, pos, settings, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle(self.tr("Edit title template"))
        self.pos = pos
        self.titleFriendlyName = QLineEdit(self)
        self.titleTemplateContent = QLineEdit(self)
        self.titleTemplateContent.textChanged.connect(self.updateUi)
        self.usesDate = QCheckBox(self)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | 
                                          QDialogButtonBox.Cancel)
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self.settings = settings

        layout = QGridLayout(self)
        layout.addWidget(0, 0, QLabel(self.tr("Friendly name")))
        layout.addWidget(0, 1, self.titleFriendlyName)
        layout.addWidget(1, 0, QLabel(self.tr("Title template")))
        layout.addWidget(1, 1, self.titleTemplateContent)
        layout.addWidget(2, 0, QLabel(self.tr("Uses date?")))
        layout.addWidget(2, 1, self.usesDate)
        layout.addWidget(3, 1, 1, 2, self.buttonBox)

        if self.pos != -1:
            item = self.settings.titleTemplates.item(self.pos)
            self.titleFriendlyName.setText(item.text())
            self.titleTemplateContent.setText(item.data(COL_DATA))
            if item.data(COL_EXTRA_DATA) == TitleType.DATETIME:
                self.usesDate.setCheckState(Qt.Checked)
            else:
                self.usesDate.setCheckState(Qt.Unchecked)

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def updateUi(self, newstr):
        if newstr:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

    def accept(self):
        acceptable = False
        try:
            if self.usesDate.isChecked():
                makeTemplateTitle(TitleType.DATETIME, userinput="TestString")
            else:
                makeTemplateTitle(TitleType.FSTRING, userinput="TestString")
            acceptable = True
        except Exception as e:
            acceptable = False
            emessage = e.message

        if acceptable:
            if self.pos != -1:
                item = self.settings.titleTemplates.item(self.pos)
                item.setText(self.titleFriendlyName.text())
                item.setData(self.titleTemplateContent.text(), COL_DATA)
                if self.usesDate.isChecked():
                    item.setData(TitleType.DATETIME, COL_EXTRA_DATA)
                else:
                    item.setData(TitleType.FSTRING, COL_EXTRA_DATA)
            else:
                item = QStandardItem()
                item.setText(self.titleFriendlyName.text())
                item.setData(self.titleTemplateContent.text(), COL_DATA)
                if self.usesDate.isChecked():
                    item.setData(TitleType.DATETIME, COL_EXTRA_DATA)
                else:
                    item.setData(TitleType.FSTRING, COL_EXTRA_DATA)
                self.settings.titleTemplates.appendRow(item)
            QDialog.accept(self)
        else:
            QMessageBox.warning(self, self.tr("Error"),
            self.tr("Title format invalid: %s") % emessage)

class PickTemplateDialog(QDialog):
    def __init__(self, path, settings, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle(self.tr("Create note from template"))
        self.path = path

        self.titleTemplates = QComboBox(self)
        self.bodyTemplates  = QComboBox(self)
        self.bodyTitlePairs = QComboBox(self)
        self.titleTemplateParameter = QLineEdit(self)
        self.bodyTitlePairs.currentIndexChanged.connect(self.updateTitleBody)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok |
                                          QDialogButtonBox.Cancel)
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self.settings = settings

        self.titleTemplates.setModel(self.settings.titleTemplates)
        self.bodyTemplates.setModel(self.settings.bodyTemplates)
        pathToIdx = self.settings.bodyTemplates.index(self.settings.templatesPath)
        self.bodyTemplates.setRootModelIndex(pathToIdx)
        self.bodyTemplates.model().directoryLoaded.connect(self.updateUi)
        self.bodyTitlePairs.setModel(self.settings.bodyTitlePairs)

        layout = QGridLayout(self)
        layout.addWidget(QLabel(self.tr("Title template:")), 0, 0)
        layout.addWidget(self.titleTemplates, 0, 1)
        layout.addWidget(QLabel(self.tr("Title parameter:")), 1, 0)
        layout.addWidget(self.titleTemplateParameter, 1, 1)
        layout.addWidget(QLabel(self.tr("Body template:")), 2, 0)
        layout.addWidget(self.bodyTemplates, 2, 1)
        tmpLabel = QLabel(self.tr("--- OR ---"))
        tmpLabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(tmpLabel, 3, 0, 1, 2)
        layout.addWidget(QLabel(self.tr("Quick pick pair...")), 4, 0)
        layout.addWidget(self.bodyTitlePairs, 4, 1)
        layout.addWidget(self.buttonBox, 5, 0, 1, 2)

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.updateUi()

    def accept(self):
        dtnow = datetime.datetime.now()
        titleItem = self.titleTemplates.model().item(curTitleIdx)
        titleItemContent = titleItem.data(COL_DATA)
        titleItemType = titleItem.data(COL_EXTRA_DATA)
        titleParameter = self.titleTemplateParameter.text()
        newPageName = mikitemplate.makeTemplateTitle(titleItemType, 
            titleItemContent, dtnow=dtnow, userinput=titleParameter)
        notePath = os.path.join(self.path, newPageName)
        acceptable, existPath = doesFileExist(notePath, NOTE_EXTS)
        if acceptable:
            QDialog.accept(self)
        else:
            QMessageBox.warning(self, self.tr("Error"),
            self.tr("File already exists: %s") % existPath)

    def updateUi(self):
        comboModel = self.bodyTemplates.model()
        rowCount = comboModel.rowCount()
        itemIdx = comboModel.index(0, 0, parent=self.bodyTemplates.rootModelIndex())
        singleNotRoot = itemIdx.isValid()
        shouldEnable = rowCount > 1 or singleNotRoot
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(shouldEnable)
        self.bodyTemplates.setEnabled(shouldEnable)

    def updateTitleBody(self, idx):
        modelItem = self.bodyTitlePairs.model().item(idx)
        if modelItem is not None:
            self.titleTemplates.setCurrentIndex(modelItem.data(COL_DATA))
            self.bodyTemplates.setCurrentIndex(self.bodyTemplates.findText(modelItem.data(COL_EXTRA_DATA)))