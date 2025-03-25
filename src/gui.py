import sys
import os
import threading
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QComboBox, QPushButton, QTextEdit, 
    QSpinBox, QDoubleSpinBox, QGroupBox, QProgressBar, QMessageBox,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QFileDialog, QListWidget, QAbstractItemView, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QColor
from dotenv import load_dotenv

# Import your existing logic
from src.logic import get_arbitrage_opportunities, get_sports

class WorkerSignals(QObject):
    """Defines the signals available from the worker thread."""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(list)
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    sports_loaded = pyqtSignal(list)

class ArbitrageWorker(threading.Thread):
    """Worker thread for running arbitrage calculations."""
    def __init__(self, key, region, cutoff, selected_sports=None):
        super().__init__()
        self.key = key
        self.region = region
        self.cutoff = cutoff
        self.selected_sports = selected_sports
        self.signals = WorkerSignals()
        self.daemon = True  # Make thread exit when main thread exits
        
    def run(self):
        try:
            self.signals.status.emit("Getting available sports...")
            opportunities = get_arbitrage_opportunities(
                key=self.key, 
                region=self.region, 
                cutoff=self.cutoff,
                selected_sports=self.selected_sports
            )
            self.signals.result.emit(opportunities)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()

class SportsLoaderWorker(threading.Thread):
    """Worker thread for loading available sports."""
    def __init__(self, key):
        super().__init__()
        self.key = key
        self.signals = WorkerSignals()
        self.daemon = True
        
    def run(self):
        try:
            self.signals.status.emit("Loading available sports...")
            sports = get_sports(self.key)
            self.signals.sports_loaded.emit(sports)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.status.emit("Sports loaded")
            self.signals.finished.emit()

class ArbitrageFinderGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Arbitrage Finder")
        self.setMinimumSize(1000, 700)
        
        # Load API key from environment if available
        load_dotenv()
        default_api_key = os.environ.get("API_KEY", "")
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Input section
        input_group = QGroupBox("Configuration")
        input_layout = QVBoxLayout()
        input_group.setLayout(input_layout)
        
        # API Key input
        api_key_layout = QHBoxLayout()
        api_key_label = QLabel("API Key:")
        self.api_key_input = QLineEdit(default_api_key)
        self.api_key_input.setPlaceholderText("Enter your API key from The Odds API")
        load_sports_button = QPushButton("Load Sports")
        load_sports_button.clicked.connect(self.load_available_sports)
        
        api_key_layout.addWidget(api_key_label)
        api_key_layout.addWidget(self.api_key_input, 1)
        api_key_layout.addWidget(load_sports_button)
        input_layout.addLayout(api_key_layout)
        
        # Sports filter and region selection section
        filter_region_layout = QHBoxLayout()
        
        # Sports filter section
        sports_group = QGroupBox("Sports Filter")
        sports_layout = QVBoxLayout()
        sports_group.setLayout(sports_layout)
        
        sports_header_layout = QHBoxLayout()
        sports_label = QLabel("Available Sports:")
        self.select_all_sports = QCheckBox("Select All")
        self.select_all_sports.setChecked(True)
        self.select_all_sports.stateChanged.connect(self.toggle_all_sports)
        
        sports_header_layout.addWidget(sports_label)
        sports_header_layout.addWidget(self.select_all_sports)
        sports_layout.addLayout(sports_header_layout)
        
        self.sports_list = QListWidget()
        self.sports_list.setSelectionMode(QAbstractItemView.MultiSelection)
        sports_layout.addWidget(self.sports_list)
        
        # Region and cutoff section
        region_group = QGroupBox("Region & Margin")
        region_layout = QVBoxLayout()
        region_group.setLayout(region_layout)
        
        region_label = QLabel("Region:")
        self.region_combo = QComboBox()
        self.region_combo.addItems(["eu", "us", "au", "uk"])
        self.region_combo.setCurrentText("us")
        
        cutoff_label = QLabel("Min. Profit Margin (%):")
        self.cutoff_spin = QDoubleSpinBox()
        self.cutoff_spin.setRange(0, 10)
        self.cutoff_spin.setSingleStep(0.1)
        self.cutoff_spin.setValue(0)
        
        region_layout.addWidget(region_label)
        region_layout.addWidget(self.region_combo)
        region_layout.addWidget(cutoff_label)
        region_layout.addWidget(self.cutoff_spin)
        
        # Add sports and region sections to layout
        filter_region_layout.addWidget(sports_group, 2)
        filter_region_layout.addWidget(region_group, 1)
        input_layout.addLayout(filter_region_layout)
        
        # Bankroll settings
        bankroll_layout = QHBoxLayout()
        bankroll_label = QLabel("Bankroll Amount:")
        self.bankroll_input = QDoubleSpinBox()
        self.bankroll_input.setRange(1, 1000000)
        self.bankroll_input.setValue(1000)
        self.bankroll_input.setPrefix("$")
        self.bankroll_input.setDecimals(2)
        
        self.show_bankroll_alloc = QCheckBox("Show Bankroll Allocation")
        self.show_bankroll_alloc.setChecked(True)
        
        bankroll_layout.addWidget(bankroll_label)
        bankroll_layout.addWidget(self.bankroll_input)
        bankroll_layout.addWidget(self.show_bankroll_alloc)
        
        input_layout.addLayout(bankroll_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.search_button = QPushButton("Find Opportunities")
        self.search_button.clicked.connect(self.find_opportunities)
        self.export_button = QPushButton("Export Results")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setEnabled(False)
        
        button_layout.addWidget(self.search_button)
        button_layout.addWidget(self.export_button)
        input_layout.addLayout(button_layout)
        
        main_layout.addWidget(input_group)
        
        # Status label and progress bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setVisible(False)
        
        status_layout.addWidget(self.status_label, 1)
        status_layout.addWidget(self.progress_bar, 3)
        main_layout.addLayout(status_layout)
        
        # Results display with tabs
        self.tabs = QTabWidget()
        
        # Text view tab
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.tabs.addTab(self.results_text, "Text View")
        
        # Table view tab
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)  # Initial columns, will be expanded with outcomes
        self.results_table.setHorizontalHeaderLabels(['Match', 'League', 'Hours to Start', 'Total Implied Odds', 'Profit %', 'Profit Amount'])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabs.addTab(self.results_table, "Table View")
        
        main_layout.addWidget(self.tabs)
        
        # Store opportunities for export
        self.opportunities = []
        
        # Initialize with empty sports list (will be populated on load)
        self.sports = []
        
        # Disable search button until sports are loaded
        self.search_button.setEnabled(False)
        
    def toggle_all_sports(self, state):
        """Select or deselect all sports in the list."""
        for i in range(self.sports_list.count()):
            item = self.sports_list.item(i)
            if state == Qt.Checked:
                item.setSelected(True)
            else:
                item.setSelected(False)
    
    def load_available_sports(self):
        """Load available sports using the API key."""
        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Missing API Key", "Please enter your API key from The Odds API.")
            return
        
        # Show progress and update status
        self.progress_bar.setVisible(True)
        self.status_label.setText("Loading available sports...")
        self.sports_list.clear()
        
        # Load sports in a background thread
        self.sports_loader = SportsLoaderWorker(api_key)
        self.sports_loader.signals.sports_loaded.connect(self.update_sports_list)
        self.sports_loader.signals.error.connect(self.handle_error)
        self.sports_loader.signals.finished.connect(lambda: self.progress_bar.setVisible(False))
        self.sports_loader.signals.status.connect(self.update_status)
        self.sports_loader.start()
    
    def update_sports_list(self, sports):
        """Update the sports list with available sports."""
        self.sports = sports
        self.sports_list.clear()
        
        for sport in sorted(sports):
            self.sports_list.addItem(sport)
        
        # Select all sports by default
        if self.select_all_sports.isChecked():
            for i in range(self.sports_list.count()):
                self.sports_list.item(i).setSelected(True)
        
        self.search_button.setEnabled(True)
        self.status_label.setText(f"Loaded {len(sports)} sports")
        
    def calculate_bankroll_allocation(self, odds_dict, total_implied_odds, bankroll):
        """
        Calculate the optimal bankroll allocation for each outcome to ensure equal profit.
        Returns a dictionary with outcome names as keys and allocation percentages as values.
        """
        allocations = {}
        total_percentage = 0
        
        for outcome, (bookmaker, odd) in odds_dict.items():
            # Calculate stake as percentage of bankroll
            stake_percentage = (1 / odd) / total_implied_odds
            allocations[outcome] = {
                'percentage': stake_percentage * 100,  # Convert to percentage
                'amount': bankroll * stake_percentage,
                'bookmaker': bookmaker,
                'odd': odd
            }
            total_percentage += stake_percentage * 100
            
        # Verify total percentage is approximately 100%
        if not (99.5 <= total_percentage <= 100.5):
            print(f"Warning: Total allocation percentage is {total_percentage:.2f}%, not 100%")
            
        return allocations
        
    def find_opportunities(self):
        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Missing API Key", "Please enter your API key from The Odds API.")
            return
        
        # Get selected sports
        selected_sports = [item.text() for item in self.sports_list.selectedItems()]
        if not selected_sports:
            QMessageBox.warning(self, "No Sports Selected", "Please select at least one sport.")
            return
            
        region = self.region_combo.currentText()
        cutoff = self.cutoff_spin.value() / 100
        
        # Disable search button and show progress
        self.search_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Searching for arbitrage opportunities...")
        
        self.results_text.clear()
        self.results_table.setRowCount(0)
        self.results_text.append(f"Searching for arbitrage opportunities in {len(selected_sports)} sports...\n")
        
        # Run the search in a background thread
        self.worker = ArbitrageWorker(api_key, region, cutoff, selected_sports)
        self.worker.signals.result.connect(self.display_results)
        self.worker.signals.error.connect(self.handle_error)
        self.worker.signals.finished.connect(self.search_completed)
        self.worker.signals.status.connect(self.update_status)
        self.worker.start()
    
    def update_status(self, message):
        self.status_label.setText(message)
    
    def display_results(self, opportunities):
        self.opportunities = opportunities
        self.results_text.clear()
        
        count = len(opportunities)
        self.results_text.append(f"{count} arbitrage opportunities found\n")
        
        # Get bankroll amount
        bankroll = self.bankroll_input.value()
        show_allocation = self.show_bankroll_alloc.isChecked()
        
        # Update text view
        for arb in opportunities:
            self.results_text.append(f"🏆 {arb['match_name']} in {arb['league']}")
            self.results_text.append(f"    Total implied odds: {arb['total_implied_odds']:.4f} with these odds:")
            
            # Calculate bankroll allocation if checkbox is checked
            if show_allocation:
                allocations = self.calculate_bankroll_allocation(
                    arb['best_outcome_odds'], 
                    arb['total_implied_odds'],
                    bankroll
                )
                
                # Store the allocations in the opportunity data for export
                arb['bankroll_allocations'] = allocations
                
                # Display odds with allocation information
                for outcome, allocation in allocations.items():
                    self.results_text.append(
                        f"    • {outcome} with {allocation['bookmaker']} for {allocation['odd']:.2f} odds - "
                        f"Bet: ${allocation['amount']:.2f} ({allocation['percentage']:.2f}% of bankroll)"
                    )
            else:
                # Display just the odds without allocation information
                for key, value in arb['best_outcome_odds'].items():
                    self.results_text.append(f"    • {key} with {value[0]} for {value[1]}")
            
            # Calculate and show potential profit
            profit_percentage = (1 - arb['total_implied_odds']) * 100
            self.results_text.append(f"    Potential profit: {profit_percentage:.2f}%\n")
            
            if show_allocation:
                # Calculate actual profit amount based on bankroll
                profit_amount = bankroll * (1 - arb['total_implied_odds'])
                self.results_text.append(f"    Profit amount: ${profit_amount:.2f} on ${bankroll:.2f} bankroll\n")
        
        # Update table view
        self.update_table_view(opportunities, bankroll, show_allocation)
    
    def update_table_view(self, opportunities, bankroll, show_allocation):
        if not opportunities:
            return
            
        # Get all unique outcome names across all opportunities
        all_outcomes = set()
        for arb in opportunities:
            for outcome in arb['best_outcome_odds'].keys():
                all_outcomes.add(outcome)
        
        # Set up the table columns
        base_columns = ['Match', 'League', 'Hours to Start', 'Total Implied Odds', 'Profit %', 'Profit Amount']
        outcome_columns = []
        
        if show_allocation:
            for outcome in sorted(all_outcomes):
                outcome_columns.extend([f"{outcome} Bookmaker", f"{outcome} Odds", f"{outcome} Stake"])
        
        all_columns = base_columns + outcome_columns
        self.results_table.setColumnCount(len(all_columns))
        self.results_table.setHorizontalHeaderLabels(all_columns)
        
        # Populate the table
        self.results_table.setRowCount(len(opportunities))
        
        for row_idx, arb in enumerate(opportunities):
            # Calculate profit percentage and amount
            profit_percentage = (1 - arb['total_implied_odds']) * 100
            profit_amount = bankroll * (1 - arb['total_implied_odds'])
            
            # Base columns
            self.results_table.setItem(row_idx, 0, QTableWidgetItem(arb['match_name']))
            self.results_table.setItem(row_idx, 1, QTableWidgetItem(arb['league']))
            self.results_table.setItem(row_idx, 2, QTableWidgetItem(f"{arb['hours_to_start']:.1f}"))
            self.results_table.setItem(row_idx, 3, QTableWidgetItem(f"{arb['total_implied_odds']:.4f}"))
            self.results_table.setItem(row_idx, 4, QTableWidgetItem(f"{profit_percentage:.2f}%"))
            self.results_table.setItem(row_idx, 5, QTableWidgetItem(f"${profit_amount:.2f}"))
            
            # Apply conditional formatting - higher profit = greener
            profit_item = self.results_table.item(row_idx, 4)
            intensity = min(int(profit_percentage * 25), 150)  # Scale green intensity
            profit_item.setBackground(QColor(255 - intensity, 255, 255 - intensity))
            
            # Outcome columns if showing allocation
            if show_allocation:
                allocations = self.calculate_bankroll_allocation(
                    arb['best_outcome_odds'],
                    arb['total_implied_odds'],
                    bankroll
                )
                
                col_offset = len(base_columns)
                for outcome_idx, outcome in enumerate(sorted(all_outcomes)):
                    if outcome in allocations:
                        alloc = allocations[outcome]
                        self.results_table.setItem(row_idx, col_offset + outcome_idx*3, 
                                                 QTableWidgetItem(alloc['bookmaker']))
                        self.results_table.setItem(row_idx, col_offset + outcome_idx*3 + 1, 
                                                 QTableWidgetItem(f"{alloc['odd']:.2f}"))
                        self.results_table.setItem(row_idx, col_offset + outcome_idx*3 + 2, 
                                                 QTableWidgetItem(f"${alloc['amount']:.2f}"))
                    else:
                        self.results_table.setItem(row_idx, col_offset + outcome_idx*3, QTableWidgetItem("N/A"))
                        self.results_table.setItem(row_idx, col_offset + outcome_idx*3 + 1, QTableWidgetItem("N/A"))
                        self.results_table.setItem(row_idx, col_offset + outcome_idx*3 + 2, QTableWidgetItem("N/A"))
        
        # Adjust column widths
        self.results_table.resizeColumnsToContents()
    
    def handle_error(self, error_msg):
        self.results_text.clear()
        self.results_text.append(f"Error: {error_msg}")
        self.status_label.setText(f"Error: {error_msg}")
        QMessageBox.critical(self, "Error", f"An error occurred: {error_msg}")
    
    def search_completed(self):
        self.search_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.export_button.setEnabled(len(self.opportunities) > 0)
        
        if self.opportunities:
            self.status_label.setText(f"Found {len(self.opportunities)} arbitrage opportunities.")
        else:
            self.status_label.setText("No arbitrage opportunities found.")
    
    def export_results(self):
        if not self.opportunities:
            return
            
        file_path, filter_used = QFileDialog.getSaveFileName(
            self, "Export Results", "", "JSON Files (*.json);;CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            show_allocation = self.show_bankroll_alloc.isChecked()
            bankroll = self.bankroll_input.value()
            
            # For export, ensure we calculate allocations if they don't exist yet
            if show_allocation:
                for arb in self.opportunities:
                    if 'bankroll_allocations' not in arb:
                        arb['bankroll_allocations'] = self.calculate_bankroll_allocation(
                            arb['best_outcome_odds'],
                            arb['total_implied_odds'],
                            bankroll
                        )
            
            # Add file extension if not present
            if "json" in filter_used and not file_path.lower().endswith('.json'):
                file_path += '.json'
            elif "csv" in filter_used and not file_path.lower().endswith('.csv'):
                file_path += '.csv'
            
            if file_path.endswith('.json'):
                with open(file_path, 'w') as f:
                    json.dump(self.opportunities, f, indent=2)
            elif file_path.endswith('.csv'):
                import csv
                with open(file_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    
                    # Write header
                    header = ['Match', 'League', 'Hours to Start', 'Total Implied Odds', 'Profit %']
                    
                    # Add allocation columns if showing allocations
                    if show_allocation:
                        # We need to get the outcome names from the first opportunity to create headers
                        if self.opportunities:
                            first_arb = self.opportunities[0]
                            for outcome in first_arb['best_outcome_odds'].keys():
                                header.extend([f"{outcome} Bookmaker", f"{outcome} Odds", f"{outcome} Stake %", f"{outcome} Stake $"])
                    
                    writer.writerow(header)
                    
                    # Write data
                    for arb in self.opportunities:
                        profit = (1 - arb['total_implied_odds']) * 100
                        row = [
                            arb['match_name'],
                            arb['league'],
                            f"{arb['hours_to_start']:.1f}",
                            f"{arb['total_implied_odds']:.4f}",
                            f"{profit:.2f}%"
                        ]
                        
                        # Add allocation data if showing allocations
                        if show_allocation and 'bankroll_allocations' in arb:
                            for outcome in arb['best_outcome_odds'].keys():
                                if outcome in arb['bankroll_allocations']:
                                    alloc = arb['bankroll_allocations'][outcome]
                                    row.extend([
                                        alloc['bookmaker'],
                                        f"{alloc['odd']:.2f}",
                                        f"{alloc['percentage']:.2f}%",
                                        f"${alloc['amount']:.2f}"
                                    ])
                                else:
                                    row.extend(["N/A", "N/A", "N/A", "N/A"])
                        
                        writer.writerow(row)
            else:
                # Default to JSON if no recognized extension
                with open(file_path, 'w') as f:
                    json.dump(self.opportunities, f, indent=2)
                    
            QMessageBox.information(self, "Export Successful", f"Results successfully exported to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export results: {str(e)}")