import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTabWidget, QTableWidget, QTableWidgetItem,
    QMessageBox, QGroupBox, QGridLayout, QHeaderView, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from desktop_app.api_client import APIClient

class LoginDialog(QWidget):
    def __init__(self, api_client, on_success):
        super().__init__()
        self.api_client = api_client
        self.on_success = on_success
        self.setWindowTitle("Login - Sistema Operativo Móviles Chiriquí")
        self.setFixedSize(380, 260)
        
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        title = QLabel("🚛 Control Operativo Chiriquí")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        sub = QLabel("Inicie sesión para acceder al panel de supervisión")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(sub)
        
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("Usuario (ej. admin)")
        self.txt_user.setText("admin")
        layout.addWidget(self.txt_user)
        
        self.txt_pass = QLineEdit()
        self.txt_pass.setPlaceholderText("Contraseña")
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setText("admin123")
        layout.addWidget(self.txt_pass)
        
        self.btn_login = QPushButton("🔑 Iniciar Sesión")
        self.btn_login.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 10px; border-radius: 6px;")
        self.btn_login.clicked.connect(self.handle_login)
        layout.addWidget(self.btn_login)
        
        self.setLayout(layout)
        
    def handle_login(self):
        user = self.txt_user.text().strip()
        pwd = self.txt_pass.text()
        
        ok, res = self.api_client.login(user, pwd)
        if ok:
            self.on_success()
            self.close()
        else:
            QMessageBox.critical(self, "Error de Autenticación", str(res))


class MainWindow(QMainWindow):
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.setWindowTitle("Sistema de Control Operativo de Móviles – Chiriquí (Escritorio)")
        self.resize(1100, 720)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Header Bar
        header = QHBoxLayout()
        title_lbl = QLabel("🚛 Control Operativo de Móviles – Chiriquí")
        title_lbl.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header.addWidget(title_lbl)
        
        header.addStretch()
        
        btn_refresh = QPushButton("🔄 Actualizar Datos")
        btn_refresh.clicked.connect(self.refresh_all_tabs)
        header.addWidget(btn_refresh)
        
        main_layout.addLayout(header)
        
        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Initialize Tabs
        self.init_tab_dashboard()
        self.init_tab_orders()
        self.init_tab_inspections()
        self.init_tab_guarantees()
        self.init_tab_action_plans()
        self.init_tab_reports()
        
        self.refresh_all_tabs()
        
    def init_tab_dashboard(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # KPIs Grid
        kpi_group = QGroupBox("📊 Indicadores Generales (KPIs)")
        kpi_layout = QGridLayout(kpi_group)
        
        self.lbl_kpi_completed = QLabel("Órdenes: 0")
        self.lbl_kpi_completed.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        kpi_layout.addWidget(self.lbl_kpi_completed, 0, 0)
        
        self.lbl_kpi_inspections = QLabel("Inspecciones: 0")
        self.lbl_kpi_inspections.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        kpi_layout.addWidget(self.lbl_kpi_inspections, 0, 1)
        
        self.lbl_kpi_guarantees = QLabel("Garantías: 0.0% (Meta <= 5.0%)")
        self.lbl_kpi_guarantees.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        kpi_layout.addWidget(self.lbl_kpi_guarantees, 0, 2)
        
        self.lbl_kpi_avg_install = QLabel("Prom. Instalación: 0 min")
        self.lbl_kpi_avg_install.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        kpi_layout.addWidget(self.lbl_kpi_avg_install, 0, 3)
        
        layout.addWidget(kpi_group)
        
        # Semáforo de Móviles Table
        sem_group = QGroupBox("🚦 Semáforo y Estado Operativo por Móvil (M200 - M206)")
        sem_layout = QVBoxLayout(sem_group)
        
        self.table_sem = QTableWidget(0, 6)
        self.table_sem.setHorizontalHeaderLabels(["Móvil", "Técnicos Asignados", "Órdenes (Real/Tot)", "Garantías", "NC Abiertas", "Estado Semáforo"])
        self.table_sem.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        sem_layout.addWidget(self.table_sem)
        
        layout.addWidget(sem_group)
        self.tabs.addTab(tab, "🚦 Dashboard & Semáforos")
        
    def init_tab_orders(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.table_orders = QTableWidget(0, 7)
        self.table_orders.setHorizontalHeaderLabels(["Fecha", "Orden #", "Móvil", "Técnico", "Tipo Trabajo", "Duración (Min)", "Alerta 45 Min"])
        self.table_orders.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_orders)
        
        self.tabs.addTab(tab, "📋 Órdenes de Trabajo")
        
    def init_tab_inspections(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.table_insp = QTableWidget(0, 6)
        self.table_insp.setHorizontalHeaderLabels(["Fecha", "Código", "Móvil", "Técnico", "Orden #", "Resultado General"])
        self.table_insp.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_insp)
        
        self.tabs.addTab(tab, "🖼️ Inspecciones de Campo")
        
    def init_tab_guarantees(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.lbl_guarantee_header = QLabel("Índice Global de Garantías: 0.0% (Objetivo: <= 5.0%)")
        self.lbl_guarantee_header.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(self.lbl_guarantee_header)
        
        self.table_guar = QTableWidget(0, 5)
        self.table_guar.setHorizontalHeaderLabels(["Móvil", "Órdenes Completadas", "Garantías", "Índice %", "Cumple Meta (<=5%)"])
        self.table_guar.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_guar)
        
        self.tabs.addTab(tab, "🛡️ Control de Garantías")
        
    def init_tab_action_plans(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.table_plans = QTableWidget(0, 6)
        self.table_plans.setHorizontalHeaderLabels(["Móvil", "Problema Detectado", "Acción Correctiva", "Responsable", "Fecha Límite", "Estado"])
        self.table_plans.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_plans)
        
        self.tabs.addTab(tab, "📌 Plan de Acción")
        
    def init_tab_reports(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        grp = QGroupBox("📄 Exportación de Reportes Operativos")
        vbox = QVBoxLayout(grp)
        
        btn_excel = QPushButton("📊 Exportar Reporte de Órdenes en Excel (.xlsx)")
        btn_excel.setStyleSheet("padding: 12px; font-weight: bold; background-color: #10b981; color: white;")
        btn_excel.clicked.connect(lambda: self.download_report("excel"))
        vbox.addWidget(btn_excel)
        
        btn_pdf = QPushButton("📑 Exportar Reporte Operativo en PDF (.pdf)")
        btn_pdf.setStyleSheet("padding: 12px; font-weight: bold; background-color: #2563eb; color: white;")
        btn_pdf.clicked.connect(lambda: self.download_report("pdf"))
        vbox.addWidget(btn_pdf)
        
        layout.addWidget(grp)
        layout.addStretch()
        self.tabs.addTab(tab, "📄 Reportes y Exportación")
        
    def refresh_all_tabs(self):
        # 1. Summary
        sum_data = self.api_client.get_dashboard_summary()
        if sum_data:
            self.lbl_kpi_completed.setText(f"Órdenes Realizadas: {sum_data.get('completed_orders', 0)}")
            self.lbl_kpi_inspections.setText(f"Inspecciones: {sum_data.get('total_inspections', 0)}")
            self.lbl_kpi_guarantees.setText(f"Índice Garantías: {sum_data.get('guarantee_index_pct', 0.0)}% (Meta <= 5%)")
            self.lbl_kpi_avg_install.setText(f"Prom. Instalación: {sum_data.get('avg_installation_time_minutes', 0.0)} min")
            
        # 2. Semáforos
        sem_data = self.api_client.get_mobile_status()
        self.table_sem.setRowCount(len(sem_data))
        for i, m in enumerate(sem_data):
            self.table_sem.setItem(i, 0, QTableWidgetItem(m['mobile_code']))
            self.table_sem.setItem(i, 1, QTableWidgetItem(", ".join(m['assigned_technicians']) or "Sin asignar"))
            self.table_sem.setItem(i, 2, QTableWidgetItem(f"{m['completed_orders']}/{m['total_orders']} ({m['compliance_pct']}%)"))
            self.table_sem.setItem(i, 3, QTableWidgetItem(f"{m['guarantees_count']} ({m['guarantee_index_pct']}%)"))
            self.table_sem.setItem(i, 4, QTableWidgetItem(str(m['open_non_conformities'])))
            
            item_sem = QTableWidgetItem(m['status_text'])
            if m['semaphore_color'] == 'green':
                item_sem.setBackground(QColor("#d1fae5"))
            elif m['semaphore_color'] == 'yellow':
                item_sem.setBackground(QColor("#fef3c7"))
            else:
                item_sem.setBackground(QColor("#fee2e2"))
            self.table_sem.setItem(i, 5, item_sem)

        # 3. Órdenes
        orders = self.api_client.get_orders()
        self.table_orders.setRowCount(len(orders))
        for i, o in enumerate(orders):
            self.table_orders.setItem(i, 0, QTableWidgetItem(o['order_date']))
            self.table_orders.setItem(i, 1, QTableWidgetItem(o['order_number']))
            self.table_orders.setItem(i, 2, QTableWidgetItem(o['mobile_code'] or ''))
            self.table_orders.setItem(i, 3, QTableWidgetItem(o['primary_technician_name'] or ''))
            self.table_orders.setItem(i, 4, QTableWidgetItem(o['order_type']))
            self.table_orders.setItem(i, 5, QTableWidgetItem(str(o['duration_minutes'])))
            
            item_alert = QTableWidgetItem("SÍ - SUPERÓ 45 MIN" if o['exceeds_target_time'] else "OK")
            if o['exceeds_target_time']:
                item_alert.setBackground(QColor("#fee2e2"))
            self.table_orders.setItem(i, 6, item_alert)

        # 4. Inspecciones
        insps = self.api_client.get_inspections()
        self.table_insp.setRowCount(len(insps))
        for i, insp in enumerate(insps):
            self.table_insp.setItem(i, 0, QTableWidgetItem(insp['inspection_date']))
            self.table_insp.setItem(i, 1, QTableWidgetItem(insp['inspection_code']))
            self.table_insp.setItem(i, 2, QTableWidgetItem(insp['mobile_code'] or ''))
            self.table_insp.setItem(i, 3, QTableWidgetItem(insp['technician_name'] or ''))
            self.table_insp.setItem(i, 4, QTableWidgetItem(insp['order_number']))
            self.table_insp.setItem(i, 5, QTableWidgetItem(insp['general_result']))

        # 5. Garantías
        guar_summary = self.api_client.get_guarantees()
        if guar_summary:
            overall = guar_summary.get('overall_guarantee_index_pct', 0.0)
            self.lbl_guarantee_header.setText(f"Índice Global de Garantías: {overall}% (Objetivo: <= 5.0%)")
            
            mob_guar = guar_summary.get('summary_by_mobile', [])
            self.table_guar.setRowCount(len(mob_guar))
            for i, mg in enumerate(mob_guar):
                self.table_guar.setItem(i, 0, QTableWidgetItem(mg['mobile_code']))
                self.table_guar.setItem(i, 1, QTableWidgetItem(str(mg['completed_orders'])))
                self.table_guar.setItem(i, 2, QTableWidgetItem(str(mg['guarantees_count'])))
                self.table_guar.setItem(i, 3, QTableWidgetItem(f"{mg['guarantee_index_pct']}%"))
                
                item_meta = QTableWidgetItem("SÍ (<= 5%)" if not mg['exceeds_target'] else "NO (EXCEDE 5%)")
                if mg['exceeds_target']:
                    item_meta.setBackground(QColor("#fee2e2"))
                else:
                    item_meta.setBackground(QColor("#d1fae5"))
                self.table_guar.setItem(i, 4, item_meta)

        # 6. Plan de Acción
        plans = self.api_client.get_action_plans()
        self.table_plans.setRowCount(len(plans))
        for i, p in enumerate(plans):
            self.table_plans.setItem(i, 0, QTableWidgetItem(p['mobile_code'] or ''))
            self.table_plans.setItem(i, 1, QTableWidgetItem(p['detected_problem']))
            self.table_plans.setItem(i, 2, QTableWidgetItem(p['corrective_action']))
            self.table_plans.setItem(i, 3, QTableWidgetItem(p['responsible_person']))
            self.table_plans.setItem(i, 4, QTableWidgetItem(p['due_date']))
            self.table_plans.setItem(i, 5, QTableWidgetItem(p['status']))

    def download_report(self, fmt):
        if fmt == "excel":
            content = self.api_client.export_excel("orders")
            ext = ".xlsx"
            filter_str = "Excel Files (*.xlsx)"
        else:
            content = self.api_client.export_pdf()
            ext = ".pdf"
            filter_str = "PDF Files (*.pdf)"

        if not content:
            QMessageBox.warning(self, "Error", "No se pudo generar el reporte")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Guardar Reporte", f"reporte_operativo{ext}", filter_str)
        if path:
            with open(path, "wb") as f:
                f.write(content)
            QMessageBox.information(self, "Éxito", f"Reporte guardado exitosamente en:\n{path}")


def main():
    app = QApplication(sys.argv)
    api_client = APIClient()
    
    main_win = None
    
    def on_login_success():
        nonlocal main_win
        main_win = MainWindow(api_client)
        main_win.show()

    login = LoginDialog(api_client, on_login_success)
    login.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
