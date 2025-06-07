from .gui import PhotoPickerApp
from PyQt5 import QtWidgets
import sys

def main():
    app = QtWidgets.QApplication(sys.argv)
    win = PhotoPickerApp()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()