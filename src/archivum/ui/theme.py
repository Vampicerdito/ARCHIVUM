APP_STYLE = """
QWidget {
    background-color: #171719;
    color: #e9e7e5;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QMainWindow { background-color: #171719; }
QFrame#Sidebar { background-color: #111113; border-right: 1px solid #303034; }
QLabel#Brand { color: #f0eeee; font-size: 19pt; font-weight: 800; letter-spacing: 2px; }
QLabel#Muted { color: #969398; }
QPushButton {
    background-color: #252528; border: 1px solid #39393e; border-radius: 7px;
    padding: 9px 13px; text-align: left;
}
QPushButton:hover { background-color: #333338; border-color: #68636a; }
QPushButton:checked { background-color: #48232b; border-color: #8c3949; color: #ffffff; }
QPushButton#Primary {
    background-color: #873747; border: 1px solid #a34b5c;
    color: white; font-weight: 600;
}
QPushButton#Primary:hover { background-color: #9a4052; }
QFrame#Panel { background-color: #202023; border: 1px solid #343438; border-radius: 10px; }
QLabel#Metric { font-size: 25pt; font-weight: 700; color: #ffffff; }
QLineEdit {
    background-color: #202023; border: 1px solid #3b3b40;
    border-radius: 6px; padding: 8px;
}
QTableWidget {
    background-color: #202023; alternate-background-color: #252529;
    gridline-color: #35353a; border: 1px solid #35353a;
}
QHeaderView::section {
    background-color: #29292d; color: #c8c5c8; padding: 8px;
    border: none; border-bottom: 1px solid #414147;
}
QStatusBar { background-color: #111113; color: #a8a5a8; }
QScrollArea { border: none; }
"""
