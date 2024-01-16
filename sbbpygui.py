# PySide modules
from PySide6.QtWidgets import QApplication, QComboBox, QCheckBox, QListView, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QListWidget, QAbstractItemView, QLineEdit, QFileDialog, QProgressDialog
from PySide6.QtGui import QPainter, QStandardItemModel, QStandardItem
from PySide6 import QtCharts
from PySide6.QtCore import QTimer, Qt, QThread, QObject, Signal, Slot

# SBB modules
import serial.tools.list_ports
import sbbtarget

# Other modules
import json, utils
from scipy.io import savemat

class SBBPyGui(QMainWindow):

    def __init__(self):
        super().__init__()

        self.signal_series_dict = {}  # Dictionary to store signal series
        self.signal_names = []  # List to store signal names
        self.comm_status_str = "" # Status of the communication
        self.target = sbbtarget.SBBTarget()
        self.isrunning = False
        self.loggeddata = {}

        self.settings = {}

        self.load_settings()

        self.init_ui()

        self.update_signal_list()

    def load_settings(self):
        # Load settings from JSON file
        with open("settings.json", "r") as file:
            self.settings = json.load(file)

    def init_ui(self):
        self.setWindowTitle("SLRT-Host")
        self.setGeometry(self.settings["gui"]["win_defsize"][0], self.settings["gui"]["win_defsize"][1], self.settings["gui"]["win_defsize"][2], self.settings["gui"]["win_defsize"][3])

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Communication widgets
        self.port_label = QLabel("COM port:")
        self.port_input = QComboBox()
        self.port_input.setMaximumWidth(self.settings["gui"]["port_maxwidth"])
        self.port_input.setMinimumWidth(self.settings["gui"]["port_minwidth"])
        self.port_input.addItem("Refresh", -1)
        self.update_port_list(None)
        self.port_input.view().pressed.connect(self.update_port_list)

        self.baud_label = QLabel("Baudrate:")
        self.baud_input = QLineEdit(str(int(self.settings["comm"]["baud_def"])))
        self.baud_input.setMaximumWidth(self.settings["gui"]["baud_maxwidth"])
        self.baud_input.setMinimumWidth(self.settings["gui"]["baud_minwidth"])
        self.baud_input.textEdited.connect(self.validate_baud)

        self.timeout_label = QLabel("Timeout:")
        self.timeout_input = QLineEdit(str(int(self.settings["comm"]["timeout_def"])))
        self.timeout_input.setMaximumWidth(self.settings["gui"]["timeout_maxwidth"])
        self.timeout_input.setMinimumWidth(self.settings["gui"]["timeout_minwidth"])
        self.timeout_input.textEdited.connect(self.validate_timeout)
        
        # Communication widgets
        self.communication_button = QPushButton("Open Communication")
        self.communication_button.clicked.connect(self.toggle_communication)
        self.communication_status_label = QLabel("Communication Status: Closed")
        self.comm_status_str = self.communication_status_label.text()
        
        # Execution widgets
        self.execution_button = QPushButton("Start Execution")
        self.execution_button.setDisabled(True) # Initially disabled
        self.execution_button.clicked.connect(self.toggle_execution)
        self.execution_time_display = QLabel("Execution Time: 0.00")
        self.update_timer = QTimer()
        self.update_timer.setInterval(self.settings["gui"]["update_time"])

        # Logdata widgets
        self.enable_log_checkbox = QCheckBox("Log data")
        self.save_log_button = QPushButton("Save log")
        self.save_log_button.clicked.connect(self.save_log)

        # Signal widgets
        self.signal_label = QLabel("Select Signal(s):")
        self.signal_list = QListView()
        self.signal_list.setMaximumWidth(self.settings["gui"]["sgnlist_maxwidth"])
        self.signal_list.setMinimumWidth(self.settings["gui"]["sgnlist_minwidth"])
        self.signal_list.setSelectionMode(QListView.ExtendedSelection)
        self.signal_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.signal_list_model = QStandardItemModel()
        self.signal_list.setModel(self.signal_list_model)
        self.signal_list.pressed.connect(self.update_series_visibility)

        # Create the chart and set its properties
        self.chart = QtCharts.QChart()
        self.chart.setBackgroundRoundness(0)

        # Create the X and Y axes for the chart
        self.x_axis = QtCharts.QValueAxis()
        self.y_axis = QtCharts.QValueAxis()
        self.x_axis.setTitleText("Sample")
        self.y_axis.setTitleText("Signal value(s)")

        # Set the ranges for the X and Y axes
        self.update_axis_range(0)

        # Add the axes to the chart
        self.chart.addAxis(self.x_axis, Qt.AlignBottom)
        self.chart.addAxis(self.y_axis, Qt.AlignLeft)

        # Create the chart view
        self.chart_view = QtCharts.QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setRubberBand(QtCharts.QChartView.RectangleRubberBand)
        self.chart_view.setDragMode(QtCharts.QChartView.ScrollHandDrag)

        # Communication and Execution layouts
        comm_exec_layout = QHBoxLayout()
        comm_exec_layout.addWidget(self.port_label)
        comm_exec_layout.addWidget(self.port_input)
        comm_exec_layout.addWidget(self.baud_label)
        comm_exec_layout.addWidget(self.baud_input)
        comm_exec_layout.addWidget(self.timeout_label)
        comm_exec_layout.addWidget(self.timeout_input)
        comm_exec_layout.addWidget(self.communication_button)

        comm_exec_layout.addStretch(1)  # Add stretchable space to separate the sections
        comm_exec_layout.addWidget(self.execution_button)

        # Log data layout
        logdata_layout = QHBoxLayout()
        logdata_layout.addWidget(self.enable_log_checkbox)
        logdata_layout.addWidget(self.save_log_button)
        logdata_layout.addStretch(1)

        # Signal and Chart layouts
        signal_chart_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.signal_label)
        left_layout.addWidget(self.signal_list)

        chart_layout = QVBoxLayout()
        chart_layout.addWidget(self.chart_view)
        signal_chart_layout.addLayout(left_layout)
        signal_chart_layout.addLayout(chart_layout)

        # Bottom layout for Communication and Execution status labels
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.communication_status_label)
        bottom_layout.addStretch(1)  # Add stretchable space to separate the labels
        bottom_layout.addWidget(self.execution_time_display)

        # Main layout combining all the layouts
        main_layout = QVBoxLayout()
        main_layout.addLayout(comm_exec_layout)
        main_layout.addLayout(logdata_layout)
        main_layout.addLayout(signal_chart_layout)
        main_layout.addLayout(bottom_layout)

        self.central_widget.setLayout(main_layout)
        
        # Set a specific style for the application (e.g., "Fusion", "Windows", "Macintosh")
        self.setStyle("Fusion")  # Replace "Fusion" with the desired style name

    def setStyle(self, style):
        # Set a specific style for the application
        app = QApplication.instance()
        app.setStyle(style)

    def save_log(self):
        if len(self.loggeddata) < 1:
            self.execution_time_display.setText("Error: No Logged Data Found")
            return
        
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(self, "Save MATLAB file", "", "MAT file (*.mat)", options=options)
        if filename:
            savemat(filename, {key.replace(' ', '_'): value for key, value in self.loggeddata.items()}, appendmat=True, oned_as='column', long_field_names=True)
            
    def validate_baud(self, baudstr):
        if utils.valid_baud(baudstr):
            self.baud_input.setStyleSheet("")  # Reset to pre-defined
            self.communication_status_label.setText(self.comm_status_str)
        else:
            self.baud_input.setStyleSheet(
                "border: 1px solid red;"
                "border-radius: 3px;"
                "padding: 2px 0px 2px 0px;"
                "background-color: rgba(255, 0, 0, 30);"
            )
            self.communication_status_label.setText("Invalid baudrate")

    def validate_timeout(self, timeoutstr):
        if utils.valid_timeout(timeoutstr):
            self.timeout_input.setStyleSheet("")  # Reset to pre-defined
            self.communication_status_label.setText(self.comm_status_str)
        else:
            self.timeout_input.setStyleSheet(
                "border: 1px solid red;"
                "border-radius: 3px;"
                "padding: 2px 0px 2px 0px;"
                "background-color: rgba(255, 0, 0, 30);"
            )
            self.communication_status_label.setText("Invalid timeout")

    def update_port_list(self, index):
        idx = -1
        if not(index is None):
            idx = self.port_input.itemData(index.row())
        if idx == -1:
            self.port_input.clear()
            ports = serial.tools.list_ports.comports()
            for port in ports:
                self.port_input.addItem(port.device, 0)
            self.port_input.addItem("Refresh", -1)   
            self.port_input.setCurrentIndex(0)     
        
    def set_editable(self, flag: bool):
        self.port_input.setDisabled(not flag)
        self.baud_input.setDisabled(not flag)
        self.timeout_input.setDisabled(not flag)

    def toggle_communication(self):
        if not self.target.isOpen():

            baudstr = self.baud_input.text()
            timeoutstr = self.timeout_input.text()
            
            if not utils.valid_baud(baudstr):
                return
            if not utils.valid_timeout(timeoutstr):
                return
                
            port = self.port_input.currentText()
            baud = int(baudstr)
            timeout = int(timeoutstr)

            self.setDisabled(True)
            self.communication_status_label.setText("Opening Communication... Please wait.")
            
            # Start a new thread to execute target.begin
            self.thread = QThread()
            self.worker = Worker(self.target, port, baud, timeout)
            self.worker.moveToThread(self.thread)
            self.worker.finished.connect(self.on_open_communication_finished)
            self.thread.started.connect(self.worker.open_communication)
            self.thread.start()
        else:
            self.setDisabled(True)
            self.communication_status_label.setText("Closing Communication... Please wait.")

            # Start a new thread to execute target.close
            if self.isrunning:
                self.worker.stoptimer()
                self.thread.quit()
                self.thread.wait()
            
            self.thread = QThread()
            self.worker = Worker(self.target)
            self.worker.moveToThread(self.thread)
            self.worker.finished.connect(self.on_close_communication_finished)
            self.thread.started.connect(self.worker.close_communication)
            self.thread.start()
            
    def toggle_execution(self):
        if not self.isrunning:
            self.thread = QThread(parent=self)
            chart_update_factor = self.settings["gui"]["update_chart_factor"]
            max_fails = self.settings["comm"]["max_fails"]
            enable_log = self.enable_log_checkbox.isChecked()
            self.worker = Executer(self.target, self.update_timer,self.signal_names, self.signal_list, chart_update_factor, max_fails, enable_log)
            self.worker.moveToThread(self.thread)
            self.worker.chart_updater.connect(self.update_signal_chart)
            self.worker.exectime_updater.connect(self.update_execution_time)
            self.worker.error_comm.connect(self.trow_error_comm)
            self.isrunning = True
            for signal_name, series in self.signal_series_dict.items():
                series.clear()
            self.execution_button.setText("Stop Execution")
            self.enable_log_checkbox.setDisabled(True)
            self.worker.starttimer()
            self.thread.start()
        else:
            self.worker.stoptimer()
            if self.enable_log_checkbox.isChecked(): # Get logged data
                self.loggeddata = self.worker.log_vals
            else:
                self.loggeddata = {}
            self.thread.quit()
            self.thread.wait()
            self.execution_button.setText("Start Execution")
            self.enable_log_checkbox.setDisabled(False)
            self.isrunning = False

    def on_close_communication_finished(self):
        self.thread.quit()  # Stop the thread
        self.setDisabled(False)
        self.communication_button.setText("Open Communication")
        self.execution_button.setText("Start Execution") # Just to be sure
        self.execution_time_display.setText("Execution Time: 0.00")
        self.communication_status_label.setText("Communication Status: Closed")
        self.comm_status_str = self.communication_status_label.text()
        self.set_editable(True)
        self.enable_log_checkbox.setDisabled(False)
        self.execution_button.setDisabled(True)
        self.clear_signal_list()

    def on_open_communication_finished(self):
        self.thread.quit()  # Stop the thread
        self.setDisabled(False)
        if self.target.isOpen():
            self.communication_button.setText("Close Communication")
            self.communication_status_label.setText("Communication Status: Open")
            self.update_signal_list()
            self.set_editable(False)
            self.execution_button.setDisabled(False)
        else:
            self.communication_status_label.setText("Communication Status: Failed to Connect")
        
        self.comm_status_str = self.communication_status_label.text()

    def trow_error_comm(self):
        self.worker.stoptimer()
        self.thread.quit()
        self.thread.wait()
        self.execution_time_display.setText("Execution Status: Error")
        self.execution_button.setText("Start Execution")
        self.enable_log_checkbox.setDisabled(False)
        self.isrunning = False

    @Slot(float)
    def update_execution_time(self, exectime):
        self.execution_time_display.setText(f"Execution Time: {exectime:.2f} s")

    def clear_signal_list(self):
        # Clear the list view and signal ID dictionary
        self.signal_list_model.clear()
        self.signal_names = []

    def update_signal_list(self):
        # Get the signal names from the target
        self.signal_names = self.target.get_signames()
        #self.signal_names = self.settings["signames"]

        # Clear the list view and signal ID dictionary
        self.signal_list_model.clear()

        # Populate the list view with signal names and IDs
        for signal_name in self.signal_names:
            item = QStandardItem(signal_name)
            self.signal_list_model.appendRow(item)

        # Update the signal series in the chart
        self.create_signal_series()

    def create_signal_series(self):
        # Remove all existing series from the chart
        self.chart.removeAllSeries()

        # Create a QLineSeries for each signal and add them to the chart
        for signal_name in self.signal_names:
            series = QtCharts.QLineSeries()
            series.setName(signal_name)
            series.setVisible(False)
            self.chart.addSeries(series)
            self.signal_series_dict[signal_name] = series

        # Attach the X and Y axes to the series
        for series in self.signal_series_dict.values():
            series.attachAxis(self.x_axis)
            series.attachAxis(self.y_axis)

    def update_series_visibility(self):
        # Get the selected signal IDs from the list view
        selected_indexes = self.signal_list.selectedIndexes()
        # selected_signal_ids = [index.row() for index in selected_indexes]
        selected_signal_names = [index.data() for index in selected_indexes]
        
        # Show the selected series and hide the others
        for signal_name, series in self.signal_series_dict.items():
            series.setVisible(signal_name in selected_signal_names) 

    @Slot(float, list, dict)
    def update_signal_chart(self, chart_count, chart_count_vals, signal_vals_dict):

        # Set chart data
        for signal_name, series in self.signal_series_dict.items():
            for x, y in zip(chart_count_vals, signal_vals_dict[signal_name]):
                series.append(x, y)
            while series.count() > self.settings["gui"]["chart_window"]:
                series.removePoints(0, 1)

        # Set X Axis
        self.update_axis_range(chart_count)

    def update_axis_range(self, count):  
        xrange_init = (count // self.settings["gui"]["chart_window"])*self.settings["gui"]["chart_window"]
        self.x_axis.setRange(xrange_init, xrange_init + self.settings["gui"]["chart_window"])

        # Inizializza i valori minimi e massimi con il primo valore della serie
        min_value = float('inf')
        max_value = float('-inf')

        # Trova i valori minimi e massimi nella serie
        for series in self.signal_series_dict.values():
            if series.isVisible():
                for point in series.pointsVector():
                    y_value = point.y()
                    min_value = min(min_value, y_value)
                    max_value = max(max_value, y_value)

        # Imposta il range dell'asse Y in base ai valori minimi e massimi
        y_range = max_value - min_value
        if y_range == 0:
            min_value = min_value-1
            max_value = max_value+1
        else:
            min_value = min_value - y_range*0.02
            max_value = max_value + y_range*0.02
        self.y_axis.setRange(min_value, max_value)

    def closeEvent(self, event):
        # Personalized close function, perform any closing tasks here
        if self.target.isOpen(): # Load only if comm open
            self.target.close()  # Close the communication with the target

        # Call the parent class closeEvent to ensure proper closing of the application
        super().closeEvent(event)

class Executer(QObject):
    chart_updater = Signal(float, list, dict)
    exectime_updater = Signal(float)
    error_comm = Signal()
    chart_count = 0 # Counter for the chart
    chart_update_factor = 1
    chart_count_vals = [] # List to store the counter values
    signal_names = [] # Names of the signals
    signal_vals_dict = {} # Dictionary to store the values of the signals
    log_vals = {} #Dictionary to store the values logged
    fails = 0
    max_fails = 10
    signal_length = 1
    enable_log = False

    def __init__(self, target, timer, signal_names, signal_list, chart_update_factor, max_fails, enable_log):
        super().__init__()
        self.target = target
        self.timer = timer
        self.timer.timeout.connect(self.update)
        self.chart_count = 0
        self.fails = 0
        self.enable_log = enable_log
        self.chart_update_factor = chart_update_factor
        self.signal_names = signal_names
        self.signal_length = len(signal_names)
        self.signal_list = signal_list
        self.max_fails = max_fails
        self.reset_signal_vals_dict()
        self.reset_log_vals()

    def starttimer(self):
        self.timer.start()
        
    def stoptimer(self):
        self.timer.stop()

    def update(self):
        # Read data and append to dictionary
        data, _ = self.target.get_signals(self.signal_length)
        if data is None: # No read
            self.fails = self.fails + 1
            if self.fails > self.max_fails:
                self.error_comm.emit()
                return
            return
        self.fails = 0 #Reset

        # Get exec time
        exectime = self.target.get_exectime()
        
        # Log data
        if self.enable_log:
            self.log_vals["sample"].append(self.chart_count)
            self.log_vals["time"].append(exectime)
            
        # Add counter to the count list
        self.chart_count_vals.append(self.chart_count)

        for signal_id, signal_name in enumerate(self.signal_names):
            self.signal_vals_dict[signal_name].append(data[signal_id])
            if self.enable_log:
                self.log_vals[signal_name].append(data[signal_id])


        # Update chart
        if self.chart_count % self.chart_update_factor == 0:
            self.chart_updater.emit(self.chart_count, self.chart_count_vals, self.signal_vals_dict)
            self.reset_signal_vals_dict()
            if not(exectime is None):
                self.exectime_updater.emit(exectime)
            
        # Increment the chart count
        self.chart_count = self.chart_count + 1

    def reset_signal_vals_dict(self):
        self.chart_count_vals = []
        for signal_name in self.signal_names:
            self.signal_vals_dict[signal_name] = []

    def reset_log_vals(self):
        self.log_vals = {}
        for signal_name in self.signal_names:
            self.log_vals[signal_name] = []
        self.log_vals["sample"] = []
        self.log_vals["time"] = []


class Worker(QObject):
    finished = Signal()
 
    def __init__(self, target, port = None, baud = None, timeout = None):
        super().__init__()
        self.target = target
        if not(port is None):
            self.target.port = port
        if not(baud is None):
            self.target.baud = baud
        if not(timeout is None):
            self.target.timeout = float(timeout)/1000.0
            

    def open_communication(self):
        # Open the communication
        try:
            self.target.open()
        except serial.SerialException as e:
            pass
        self.finished.emit()

    def close_communication(self):
        # Close the communication
        self.target.close()
        self.finished.emit()
