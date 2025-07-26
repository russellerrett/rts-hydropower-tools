from	java.awt			import	Frame, EventQueue, Font
from	java.awt.event		import	ActionListener
from	java.lang			import	Runnable
from	javax.swing			import	JDialog, JFrame, JPanel, JLabel, JScrollPane, JTable, JButton, JOptionPane, SpringLayout, ScrollPaneConstants, ListSelectionModel
from	javax.swing.border	import	EmptyBorder
from	javax.swing.table	import	DefaultTableModel
from	hec.dssgui			import	ListSelection
from	hec.script			import	MessageBox, Plot
from	hec.heclib.dss		import	HecDss
from	hec.heclib.util		import	HecTime
from	hec.io				import	TimeSeriesContainer
from	com.rma.client		import	Browser
from	hec2.rts.script		import	RTS
from	datetime			import	date, timedelta
from	array				import	array

def output(msg="") :
	'''
	Output to console log
	'''
	print ("%s : %s" % (progname, msg))
def error(msg) :
	'''
	Outputs an error message and rasies an exception
	'''
	output(msg)
	raise Exception(msg)
	
def chktab(tab) :
	'''
	Checks that the "Modeling" tab is selected
	'''
	if tab.getTabTitle() != "Modeling" : 
		msg = "The Modeling tab must be selected"
		output("ERROR : %s" % msg)
		raise Exception(msg)
	 
def chkfcst(fcst) :
	'''
	Checks that a forecast is open
	'''
	if fcst is None : 
		msg = "A forecast must be open"
		output("ERROR : %s" % msg)
		raise Exception(msg)

####################################################
####			Project Metadata Setup			####
####################################################
ReservoirProject = "Mark Twain Lake"
ProjectName = "Mark_Twain_Lake"		##### Name of Reservoir in ResSim
PowerName = "Turbines"		##### Name of Power Plant in ResSim
NumberUnits = 2
MW_UH = 30				##### MW per Unit Hour (UH)
Turbine_EF = 0		##### DSF per Unit Hour (UH) | Set to 0 to have it computed from ResSim Turbine Rating
OutletNames = ["Tainter Gates"]		##### Name of other outlets in ResSim (i.e. ["Spill", "Sluice", "Orifice"])
NoOutlets = len(OutletNames)
ResSimNetwork = "Salt_River_Hydropower"		#### Name of ResSim Reservoir Network
####################################################
####################################################
####################################################

## Get the current forecast ##
frame = Browser.getBrowser().getBrowserFrame()
proj = frame.getCurrentProject()
pane = frame.getTabbedPane()
tab = pane.getSelectedComponent()
chktab(tab)
fcst = tab.getForecast()
chkfcst(fcst)
dssfile = fcst.getOutDssPath()
fcstTimeWindowString = str(fcst.getRunTimeWindow())
cwmsFile = HecDss.open(dssfile)

dssFileName = fcst.getForecastDSSFilename()
forecastDirectory = str(os.path.dirname(dssFileName))
HOTDSSDirectory = os.path.join(forecastDirectory,'rss',"HOT")
HOT_DSS = HOTDSSDirectory.replace("\\", "/")
HOTFile = HecDss.open(HOT_DSS)

RSSNetworkDirectory = os.path.join(forecastDirectory,'rss', "_"+ResSimNetwork)
RSSNetwork_DSS = RSSNetworkDirectory.replace("\\", "/")
RSSNetworkFile = HecDss.open(RSSNetwork_DSS)

## Find ResSim in selected forecast run alternative
ActiveFcst = tab.getActiveForecastRun()
ActiveAlts = ActiveFcst.getModelAlternatives("ResSim")
print ActiveAlts
No_ActiveRSSAlts = len(ActiveAlts)
if No_ActiveRSSAlts > 1:
	SelectedRSSAlt = JOptionPane.showInputDialog(None,"Select ResSim Alternative","ResSim Alternative",JOptionPane.PLAIN_MESSAGE,None,ActiveAlts,ActiveAlts[0])
	ActiveRSSAlt = SelectedRSSAlt
	ActiveRSSAlt_Fpart = ActiveRSSAlt.getFpart()
else:
	ActiveRSSAlt = ActiveAlts.get(0)
	ActiveRSSAlt_Fpart = ActiveRSSAlt.getFpart()
print("ResSim F-part: "+ActiveRSSAlt_Fpart)

##	Open ResSim override dss file for selected forecast run alternative
OverrideFile_osDir = os.path.join(forecastDirectory,'rss', ActiveRSSAlt_Fpart)
OverrideFile_Dir = OverrideFile_osDir.replace("\\", "/")
OverrideFile = HecDss.open(OverrideFile_Dir)

## SWPA Power Demand TS
PowerDemandDSSFile_osDir = os.path.join(forecastDirectory,'..\\..\\..\\database\\SWPA_Power_Demand')
PowerDemandDSSFile_Dir = PowerDemandDSSFile_osDir.replace("\\", "/")
	
## print 'fcstTimeWindowString : %s' %(fcstTimeWindowString)
important_times = [ i.strip(' ') for i in fcstTimeWindowString.split(';') ]
start_time, forecast_time, end_time = important_times[0], important_times[1], important_times[2]

HOT_start = HecTime()
HOT_start.set(forecast_time)
HOT_start.addDays(-1)
HOT_start_string = str(HOT_start)

HOTFile.setTimeWindow(HOT_start_string, end_time)

fcstStart_time = HecTime()
fcstStart_time.set(forecast_time)

fcstEnd_time = HecTime()
fcstEnd_time.set(end_time)

fcst_window = fcstEnd_time.julian() - fcstStart_time.julian() + 1

fcstStart_time.dateAndTime(17)

# A small helper to create a table model with custom editability
class MyTableModel(DefaultTableModel):
	def __init__(self, data, columnNames, editableCols):
		DefaultTableModel.__init__(self, data, columnNames)
		self.editable = editableCols
	
	def isCellEditable(self, row, col):
		return self.editable[col]
	
	
class HOT(JDialog, ActionListener):
	def __init__(self, owner=None, title="", modal=False, modalityType=None, gc=None):
		global theDialog, dailyTable
		
		# Call the superclass constructor with different arguments based on provided values
		if isinstance(owner, Frame):
			super(HOT, self).__init__(owner, title, modal, gc)
		elif isinstance(owner, Dialog):
			super(HOT, self).__init__(owner, title, modal, gc)
		elif isinstance(owner, Window):
			super(HOT, self).__init__(owner, title, modalityType, gc)
		else:
			super(HOT, self).__init__()
		
		theDialog = self
		
		# content pane
		content = JPanel()
		content.setBorder(EmptyBorder(5,5,5,5))
		self.setContentPane(content)
		sl = SpringLayout()
		content.setLayout(sl)
		
		# window settings
		self.setDefaultCloseOperation(JDialog.DISPOSE_ON_CLOSE)
		self.setBounds(100, 100, 1000, 930)
		
		# Title
		lblRes = JLabel(ReservoirProject)
		lblRes.setFont(Font("Tahoma", Font.BOLD, 16))
		sl.putConstraint(SpringLayout.NORTH, lblRes, 10, SpringLayout.NORTH, content)
		sl.putConstraint(SpringLayout.WEST,  lblRes, 10, SpringLayout.WEST,  content)
		content.add(lblRes)
		
		# Daily Section Label
		lblDaily = JLabel("Daily Hydropower Overrides")
		lblDaily.setFont(Font("Tahoma", Font.BOLD, 14))
		sl.putConstraint(SpringLayout.NORTH, lblDaily, 10, SpringLayout.SOUTH, lblRes)
		sl.putConstraint(SpringLayout.WEST,  lblDaily, 10, SpringLayout.WEST,  lblRes)
		content.add(lblDaily)
		
		self.btnImportPhysical = JButton("Import Physical Data")
		self.btnImportPhysical.addActionListener(self)
		sl.putConstraint(SpringLayout.NORTH, self.btnImportPhysical, 0, SpringLayout.NORTH, lblRes)
		sl.putConstraint(SpringLayout.EAST,  self.btnImportPhysical, -20, SpringLayout.EAST, content)
		content.add(self.btnImportPhysical)
		
		self.btnImportForecast = JButton("Import from forecast.dss")
		self.btnImportForecast.addActionListener(self)
		sl.putConstraint(SpringLayout.NORTH, self.btnImportForecast, 0, SpringLayout.NORTH, lblRes)
		sl.putConstraint(SpringLayout.EAST,  self.btnImportForecast, -6, SpringLayout.WEST, self.btnImportPhysical)
		content.add(self.btnImportForecast)
		
		self.btnLoadDaily = JButton("Load Daily Data")
		self.btnLoadDaily.addActionListener(self)
		sl.putConstraint(SpringLayout.NORTH, self.btnLoadDaily, 0, SpringLayout.NORTH, lblDaily)
		sl.putConstraint(SpringLayout.EAST,  self.btnLoadDaily, -20, SpringLayout.EAST, content)
		content.add(self.btnLoadDaily)
		
		# Daily Table inside scroll pane
		baseDailyCols = ["Day","Date","Pool Elev","Inflow (dsf)","Power (MW)",
						"EF (dsf/UH)","No Units","Turbine (dsf)"]
		outletDailyCols = ["%s (dsf)" % o for o in OutletNames]
		
		dailyCols = baseDailyCols + outletDailyCols + ["Total (dsf)"]
		
		dailyData = []
		dailyEditable = [False,False,False,False,True,True,True,True] + [True]*NoOutlets + [False]
		self.dailyCols = dailyCols
		self.dailyEditableCols = dailyEditable
		self.dailyModel = MyTableModel(dailyData, dailyCols, dailyEditable)
		
		self.dailyTable = JTable(self.dailyModel)
		self.dailyTable.setSelectionMode(ListSelectionModel.SINGLE_INTERVAL_SELECTION)
		# set col widths
		for i in range(len(dailyCols)):
		    col = self.dailyTable.getColumnModel().getColumn(i)
		    col.setMinWidth(75)
		    col.setMaxWidth(150)
		
		dailySP = JScrollPane(self.dailyTable)
		dailySP.setVerticalScrollBarPolicy(ScrollPaneConstants.VERTICAL_SCROLLBAR_ALWAYS)
		sl.putConstraint(SpringLayout.NORTH, dailySP, 20, SpringLayout.SOUTH, lblDaily)
		sl.putConstraint(SpringLayout.WEST,  dailySP,  0, SpringLayout.WEST,  lblDaily)
		sl.putConstraint(SpringLayout.EAST,  dailySP, -20, SpringLayout.EAST, content)
		sl.putConstraint(SpringLayout.SOUTH, dailySP, -590, SpringLayout.SOUTH, content)
		content.add(dailySP)
		
		# Edit Hourly Data Button
		self.btnCompHrPeak = JButton("Compute Hourly with Peaking")
		self.btnCompHrPeak.addActionListener(self)
		sl.putConstraint(SpringLayout.NORTH, self.btnCompHrPeak, 6, SpringLayout.SOUTH, dailySP)
		#sl.putConstraint(SpringLayout.EAST,  self.btnCompHrStep, -6, SpringLayout.WEST, self.btnCompHrPeak)
		content.add(self.btnCompHrPeak)
		
		self.btnEditHourly = JButton("Edit Hourly for Selected Day")
		self.btnEditHourly.addActionListener(self)
		sl.putConstraint(SpringLayout.NORTH, self.btnEditHourly, 6, SpringLayout.SOUTH, dailySP)
		sl.putConstraint(SpringLayout.EAST,  self.btnCompHrPeak, -6, SpringLayout.WEST, self.btnEditHourly)
		content.add(self.btnEditHourly)
		
		self.btnComp_P2Q = JButton("Power to Flow")
		self.btnComp_P2Q.addActionListener(self)
		sl.putConstraint(SpringLayout.NORTH, self.btnComp_P2Q, 6, SpringLayout.SOUTH, dailySP)
		sl.putConstraint(SpringLayout.EAST,  self.btnEditHourly, -6, SpringLayout.WEST, self.btnComp_P2Q)
		content.add(self.btnComp_P2Q)
		
		self.btnComp_Q2P = JButton("Flow to Power")
		self.btnComp_Q2P.addActionListener(self)
		sl.putConstraint(SpringLayout.NORTH, self.btnComp_Q2P, 6, SpringLayout.SOUTH, dailySP)
		sl.putConstraint(SpringLayout.EAST,  self.btnComp_Q2P, 0, SpringLayout.EAST, dailySP)
		sl.putConstraint(SpringLayout.EAST,  self.btnComp_P2Q, -6, SpringLayout.WEST, self.btnComp_Q2P)
		content.add(self.btnComp_Q2P)
		
		
		# Hourly Section Label
		self.lblHourly = JLabel("Hourly Hydropower Overrides")
		self.lblHourly.setFont(Font("Tahoma", Font.BOLD, 14))
		sl.putConstraint(SpringLayout.SOUTH, self.lblHourly, -525, SpringLayout.SOUTH, content)
		sl.putConstraint(SpringLayout.WEST,  self.lblHourly, 0, SpringLayout.WEST, lblDaily)
		content.add(self.lblHourly)
		
		# Hourly Table
		baseHourCols = ["Ending Hour","Pool Elev","Inflow (cfs)","Power (MW)",
						"EF (dsf/UH)","No Units","Turbine (cfs)"]
		outletHourCols = ["%s (cfs)" % o for o in OutletNames]
		hourCols = baseHourCols + outletHourCols + ["Total (cfs"]
		
		hourlyData = []
		hourlyEditable = [False,False,False,True,True,True,True] + [True]*NoOutlets + [False]
		self.hourCols = hourCols
		self.hourlyEditableCols = hourlyEditable
		self.hourlyModel = MyTableModel(hourlyData, hourCols, hourlyEditable)
		
		self.hourlyTable = JTable(self.hourlyModel)
		for i in range(len(hourCols)):
		    c = self.hourlyTable.getColumnModel().getColumn(i)
		    c.setMinWidth(75)
		    c.setMaxWidth(150)
		
		hourlySP = JScrollPane(self.hourlyTable)
		hourlySP.setHorizontalScrollBarPolicy(ScrollPaneConstants.HORIZONTAL_SCROLLBAR_ALWAYS)
		sl.putConstraint(SpringLayout.NORTH, hourlySP, 20, SpringLayout.SOUTH, self.lblHourly)
		sl.putConstraint(SpringLayout.WEST,  hourlySP, 0,  SpringLayout.WEST, self.lblHourly)
		sl.putConstraint(SpringLayout.EAST,  hourlySP,-20, SpringLayout.EAST, content)
		sl.putConstraint(SpringLayout.SOUTH, hourlySP, 450, SpringLayout.SOUTH, self.lblHourly)
		content.add(hourlySP)
		
		# Buttons
		self.btnHourly_P2Q = JButton("Power to Flow")
		self.btnHourly_P2Q.addActionListener(self)
		sl.putConstraint(SpringLayout.NORTH, self.btnHourly_P2Q, 6, SpringLayout.SOUTH, hourlySP)
		content.add(self.btnHourly_P2Q)
		
		self.btnHourly_Q2P = JButton("Flow to Power")
		self.btnHourly_Q2P.addActionListener(self)
		sl.putConstraint(SpringLayout.NORTH, self.btnHourly_Q2P, 6, SpringLayout.SOUTH, hourlySP)
		sl.putConstraint(SpringLayout.EAST,  self.btnHourly_Q2P, 0, SpringLayout.EAST, hourlySP)
		sl.putConstraint(SpringLayout.EAST,  self.btnHourly_P2Q, -6, SpringLayout.WEST, self.btnHourly_Q2P)
		content.add(self.btnHourly_Q2P)
		
		##	Result plot buttons
		self.btnPlotHOT = JButton("Plot HOT Edits")
		self.btnPlotHOT.addActionListener(self)
		sl.putConstraint(SpringLayout.SOUTH, self.btnPlotHOT, -10, SpringLayout.SOUTH, content)
		sl.putConstraint(SpringLayout.WEST,  self.btnPlotHOT,  0, SpringLayout.WEST, dailySP)
		content.add(self.btnPlotHOT)
		
		self.btnCompPlot = JButton("Plot HOT vs Forecast")
		self.btnCompPlot.addActionListener(self)
		sl.putConstraint(SpringLayout.SOUTH, self.btnCompPlot, -10, SpringLayout.SOUTH, content)
		sl.putConstraint(SpringLayout.WEST,  self.btnCompPlot,  10, SpringLayout.EAST, self.btnPlotHOT)
		content.add(self.btnCompPlot)
		
		self.btnPlotDayVsHour = JButton("Plot Daily vs Hourly")
		self.btnPlotDayVsHour.addActionListener(self)
		sl.putConstraint(SpringLayout.SOUTH, self.btnPlotDayVsHour, -10, SpringLayout.SOUTH, content)
		sl.putConstraint(SpringLayout.WEST,  self.btnPlotDayVsHour,  10, SpringLayout.EAST, self.btnCompPlot)
		content.add(self.btnPlotDayVsHour)
		
		##	Save Overrides
		self.btnSave = JButton("Save Overrides to ResSim")
		self.btnSave.addActionListener(self)
		sl.putConstraint(SpringLayout.SOUTH, self.btnSave, -10, SpringLayout.SOUTH, content)
		sl.putConstraint(SpringLayout.EAST,  self.btnSave,  0, SpringLayout.EAST, dailySP)
		content.add(self.btnSave)
		
	
	def actionPerformed(self, event):
		src = event.getSource()
		if src is self.btnImportForecast:
			self.import_Forecast_Data()
		if src is self.btnImportPhysical:
			self.import_Physical_Data()
		elif src is self.btnLoadDaily:
			self.load_Daily()
		elif src is self.btnCompHrPeak:
			self.compute_Hourly_Peaking()
		elif src is self.btnEditHourly:
			self.edit_Hourly()
		elif src is self.btnComp_P2Q:
			self.compute_P2Q()
		elif src is self.btnComp_Q2P:
			self.compute_Q2P()
		elif src is self.btnHourly_P2Q:
			self.compute_Hourly_P2Q()
		elif src is self.btnHourly_Q2P:
			self.compute_Hourly_Q2P()
		elif src is self.btnPlotHOT:
			self.plot_HOT_Edits()
		elif src is self.btnCompPlot:
			self.plot_HOT_Forecast()
		elif src is self.btnPlotDayVsHour:
			self.plot_Daily_Hourly()
		elif src is self.btnSave:
			self.save_Overrides()
		
################################################################################
####	Data processing, compute, and other dialog functions defined below	####
################################################################################
	
####	Copy data from forecast.dss to HOT.dss
	def import_Forecast_Data(self):
		cwmsFile.setTimeWindow(start_time, end_time)
		
		CWMS_PoolElev_1H = cwmsFile.read("//"+ProjectName+"-Pool/Elev//1Hour/"+ActiveRSSAlt_Fpart+"/")
		CWMS_PoolStor_1H = cwmsFile.read("//"+ProjectName+"-Pool/Stor//1Hour/"+ActiveRSSAlt_Fpart+"/")
		CWMS_Inflow_1H = cwmsFile.read("//"+ProjectName+"-Pool/Flow-IN//1Hour/"+ActiveRSSAlt_Fpart+"/")
		CWMS_NetInflow_1H = cwmsFile.read("//"+ProjectName+"-Pool/Flow-IN NET//1Hour/"+ActiveRSSAlt_Fpart+"/")
		CWMS_Outflow_1H = cwmsFile.read("//"+ProjectName+"-Pool/Flow-OUT//1Hour/"+ActiveRSSAlt_Fpart+"/")
		CWMS_Power_1H = cwmsFile.read("//"+ProjectName+"-"+PowerName+"/Power//1Hour/"+ActiveRSSAlt_Fpart+"/")
		CWMS_Turbine_1H = cwmsFile.read("//"+ProjectName+"-"+PowerName+"/Flow//1Hour/"+ActiveRSSAlt_Fpart+"/")
		
		CWMS_PoolElev_1D = CWMS_PoolElev_1H.transformTimeSeries("1Day", "0M", "INT")
		CWMS_PoolStor_1D = CWMS_PoolStor_1H.transformTimeSeries("1Day", "0M", "INT")
		CWMS_Inflow_1D = CWMS_Inflow_1H.transformTimeSeries("1Day", "0M", "AVE")
		CWMS_NetInflow_1D = CWMS_NetInflow_1H.transformTimeSeries("1Day", "0M", "AVE")
		CWMS_Outflow_1D = CWMS_Outflow_1H.transformTimeSeries("1Day", "0M", "AVE")
		CWMS_Power_Acc = CWMS_Power_1H.accumulation()
		CWMS_Power_Acc_1D = CWMS_Power_Acc.transformTimeSeries("1Day", "0M", "INT")
		CWMS_Power_1D = CWMS_Power_Acc_1D.successiveDifferences()
		CWMS_Turbine_1D = CWMS_Turbine_1H.transformTimeSeries("1Day", "0M", "AVE")
		
		CWMS_Outlets_1H = []
		CWMS_Outlets_1D = []
		for o in OutletNames:
			path = "//%s-%s/Flow//1Hour/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart)
			ts_hr = cwmsFile.read(path)
			ts_d = ts_hr.transformTimeSeries("1Day", "0M", "AVE")
			CWMS_Outlets_1H.append(ts_hr)
			CWMS_Outlets_1D.append(ts_d)
		
		HOTFile.write(CWMS_PoolElev_1H)
		HOTFile.write(CWMS_PoolStor_1H)
		HOTFile.write(CWMS_Inflow_1H)
		HOTFile.write(CWMS_NetInflow_1H)
		HOTFile.write(CWMS_Outflow_1H)
		HOTFile.write(CWMS_Power_1H)
		HOTFile.write(CWMS_Turbine_1H)
		for ts in CWMS_Outlets_1H:
			HOTFile.write(ts)
		
		HOTFile.write(CWMS_PoolElev_1D)
		HOTFile.write(CWMS_PoolStor_1D)
		HOTFile.write(CWMS_Inflow_1D)
		HOTFile.write(CWMS_NetInflow_1D)
		HOTFile.write(CWMS_Outflow_1D)
		HOTFile.write(CWMS_Power_1D)
		HOTFile.write(CWMS_Turbine_1D)
		for ts in CWMS_Outlets_1D:
			HOTFile.write(ts)
		
		MessageBox.showInformation("ResSim data extracted.", "Data Extract Complete")
		
	
####	Copy physical data to HOT.dss
	def import_Physical_Data(self):
		cwmsFile.setTimeWindow(start_time, end_time)
		
		CWMS_Power_1H = cwmsFile.read("//"+ProjectName+"-"+PowerName+"/Power//1Hour/"+ActiveRSSAlt_Fpart+"/")
		PoolElev_1D = HOTFile.read("//"+ProjectName+"-Pool/Elev//1Day/"+ActiveRSSAlt_Fpart+"/")
		ResSim_TurbineRating = RSSNetworkFile.read("/"+ProjectName+"/"+PowerName+"-Rating/Elev-Flow////")
		ResSim_PoolStorRating = RSSNetworkFile.get("/"+ProjectName+"/Pool-Area Capacity/Elev-Stor-Area////")
		
		PowerDemandDSSFile = HecDss.open(PowerDemandDSSFile_Dir)
		PowerDemandDSSFile.setTimeWindow(start_time, end_time)
		PowerDemandCurve = PowerDemandDSSFile.read("//SWPA/Demand//1Hour/Seasonal_Varying/")
		
		SetNoUnits_0 = CWMS_Power_1H.multiply(0)
		SetNoUnits_1H = SetNoUnits_0.add(NumberUnits)
		SetNoUnits_1H.setParameterPart("Units")
		SetNoUnits_1H.setUnits("Quantity")
		SetNoUnits_1D = SetNoUnits_1H.transformTimeSeries("1Day", "0M", "AVE")
		
		if Turbine_EF > 0:
			SetTurbineEF_0 = CWMS_Power_1H.multiply(0)
			SetTurbineEF_1H = SetTurbineEF_0.add(Turbine_EF)
			SetTurbineEF_1H.setParameterPart("EF")
			SetTurbineEF_1H.setUnits("CFS")
			SetTurbineEF_1H.setType("PER-AVER")
			SetTurbineEF_1D = SetTurbineEF_1H.transformTimeSeries("1Day", "0M", "AVE")
		else:
			SetTurbineEF_1D = ResSim_TurbineRating.ratingTableInterpolation(PoolElev_1D).divide(24)
			SetTurbineEF_1D.setLocation(""+ProjectName+"-"+PowerName+"")
			SetTurbineEF_1D.setParameterPart("EF")
			SetTurbineEF_1D.setUnits("CFS")
			SetTurbineEF_1D.setType("PER-AVER")
			SetTurbineEF_1H = SetTurbineEF_1D.transformTimeSeries("1Hour", "0M", "AVE")
		
		HOTFile.write(SetNoUnits_1H)
		HOTFile.write(SetNoUnits_1D)
		HOTFile.write(SetTurbineEF_1H)
		HOTFile.write(SetTurbineEF_1D)
		HOTFile.write(ResSim_TurbineRating)
		HOTFile.put(ResSim_PoolStorRating)
		HOTFile.write(PowerDemandCurve)
		
		MessageBox.showInformation("Physical Data Extracted.", "Data Extract Complete")
		
		
####	Load daily data from HOT.dss to daily table
	def load_Daily(self):
		HOTFile.setTimeWindow(HOT_start_string, end_time)
		
		PoolElev_1D = HOTFile.get("//"+ProjectName+"-Pool/Elev//1Day/"+ActiveRSSAlt_Fpart+"/")
		Inflow_1D = HOTFile.get("//"+ProjectName+"-Pool/Flow-IN//1Day/"+ActiveRSSAlt_Fpart+"/")
		Outflow_1D = HOTFile.get("//"+ProjectName+"-Pool/Flow-OUT//1Day/"+ActiveRSSAlt_Fpart+"/")
		Power_1D = HOTFile.get("//"+ProjectName+"-"+PowerName+"/Power//1Day/"+ActiveRSSAlt_Fpart+"/")
		EF_1D = HOTFile.get("//"+ProjectName+"-"+PowerName+"/EF//1Day/"+ActiveRSSAlt_Fpart+"/")
		NoUnits_1D = HOTFile.get("//"+ProjectName+"-"+PowerName+"/Units//1Day/"+ActiveRSSAlt_Fpart+"/")
		Turbine_1D = HOTFile.get("//"+ProjectName+"-"+PowerName+"/Flow//1Day/"+ActiveRSSAlt_Fpart+"/")
		outletTS_1D = []
		for o in OutletNames:
			path = "//%s-%s/Flow//1Day/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart)
			tsc = HOTFile.get(path)
			outletTS_1D.append(tsc)
		
		start = date(fcstStart_time.year(), fcstStart_time.month(), fcstStart_time.day())
		
		dailyData = []
		for dayIndex in range(fcst_window):
			# base row
			row = [
				"Day %d" % (dayIndex+1),
				(start + timedelta(days=dayIndex)).strftime("%d-%b, %a"),
				round(PoolElev_1D.values[dayIndex+1],2),
				round(Inflow_1D.values[dayIndex+1],0),
				round(Power_1D.values[dayIndex+1],0),
				round(EF_1D.values[dayIndex+1],0),
				round(NoUnits_1D.values[dayIndex+1],0),
				round(Turbine_1D.values[dayIndex+1],-1),
			]
			flows = [round(ts.values[dayIndex+1],-1) for ts in outletTS_1D]
			row.extend(flows)
			row.append(round(Outflow_1D.values[dayIndex+1],-1))
			dailyData.append(row)
			
		self.dailyModel = MyTableModel(dailyData, self.dailyCols, self.dailyEditableCols)
		self.dailyTable.setModel(self.dailyModel)
		
	
####	Dissaggrgate daily data into hourly by using peaking pattern
	def compute_Hourly_Peaking(self):
		model = self.dailyTable.getModel()
		n = model.getRowCount()
		
		if n == 0:
			JOptionPane.showMessageDialog(
				self,
				"No daily data loaded",
				"Error",
				JOptionPane.ERROR_MESSAGE
			)
			return
		
		dailyVals = []
		firstOutletCol = 8
		for i in range(n):
			vals = {
				'UH':		float(model.getValueAt(i, 4)/MW_UH),	# hours
				'ef':		float(model.getValueAt(i, 5)),			# dsf/UH
				'units':	float(model.getValueAt(i, 6)),			# Quantity
			}
			for j, outlet in enumerate(OutletNames):
				vals[outlet] = float(model.getValueAt(i, firstOutletCol + j))
			dailyVals.append(vals)
		
		specs = [
			('UH',		"//"+ProjectName+"-Unit Hours/Value//1Day/"+ActiveRSSAlt_Fpart+"/",		'CFS',		'INST-VAL'),
			('ef',		"//"+ProjectName+"-"+PowerName+"/EF//1Day/"+ActiveRSSAlt_Fpart+"/",		'CFS',		'PER-AVER'),
			('units',	"//"+ProjectName+"-"+PowerName+"/Units//1Day/"+ActiveRSSAlt_Fpart+"/",	'Quantity',	'PER-AVER'),
		]
		for o in OutletNames:
			specs.append((o, "//%s-%s/Flow//1Day/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart),	'CFS',		'PER-AVER'))
		
		self._create_Daily_TS(forecast_time, dailyVals, specs)
		
		pathnames = [
			"//"+ProjectName+"-Unit Hours/Value//1Day/"+ActiveRSSAlt_Fpart+"/",
			"//"+ProjectName+"-"+PowerName+"/EF//1Day/"+ActiveRSSAlt_Fpart+"/",
			"//"+ProjectName+"-"+PowerName+"/Units//1Day/"+ActiveRSSAlt_Fpart+"/",
		]
		pathnames += ["//%s-%s/Flow//1Day/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart) for o in OutletNames]
		
		self._Daily_to_Hourly(pathnames)
		
		HOTFile.setTimeWindow(forecast_time, end_time)
		unitHoursTS_Hr = HOTFile.read("//"+ProjectName+"-Unit Hours/Value//1Hour/"+ActiveRSSAlt_Fpart+"/")
		efTS_Hr = HOTFile.read("//"+ProjectName+"-"+PowerName+"/EF//1Hour/"+ActiveRSSAlt_Fpart+"/")
		noUnitsTS_Hr = HOTFile.read("//"+ProjectName+"-"+PowerName+"/Units//1Hour/"+ActiveRSSAlt_Fpart+"/")
		outletTS_Hr = [HOTFile.read("//%s-%s/Flow//1Hour/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart)) for o in OutletNames]
		
		PowerDemand = HOTFile.read("//SWPA/Demand//1Hour/Seasonal_Varying/")
		UH_Avaiable = PowerDemand.multiply(noUnitsTS_Hr)
		PowerGenHrs = UH_Avaiable.add(unitHoursTS_Hr)
		PowerGenHrs_Min = PowerGenHrs.screenWithMaxMin(0.0, 1000000.0, 1000000.0, 1, 0.0, "")
		PowerGenHrs_Cap = PowerGenHrs_Min.subtract(noUnitsTS_Hr)
		PowerGenHrs_Max = PowerGenHrs_Cap.screenWithMaxMin(-1000000.0, 0.0, 1000000.0, 1, 0.0, "")
		PowerGen_UH = PowerGenHrs_Max.add(noUnitsTS_Hr)
		
		Turbine_Capacity = efTS_Hr.multiply(24)
		Turbine_Release = Turbine_Capacity.multiply(PowerGen_UH)
		Turbine_Release.setPathname("//"+ProjectName+"-"+PowerName+"/Flow//1Hour/"+ActiveRSSAlt_Fpart+"/")
		Turbine_Release.setUnits("CFS")
		Turbine_Release.setType("PER-AVER")
		HOTFile.write(Turbine_Release)
		
		Total_Release = Turbine_Release
		for o in outletTS_Hr:
			Total_Release = Total_Release.add(o)
		Total_Release.setPathname("//"+ProjectName+"-Pool/Flow-OUT//1Hour/"+ActiveRSSAlt_Fpart+"/")
		HOTFile.write(Total_Release)
		
		Power = PowerGen_UH.multiply(MW_UH)
		Power.setPathname("//"+ProjectName+"-"+PowerName+"/Power//1Hour/"+ActiveRSSAlt_Fpart+"/")
		Power.setType("PER-AVER")
		HOTFile.write(Power)
		
		self._recompute_Pool_Elev()
		self.load_Daily()
		
		MessageBox.showInformation("Daily edits translated to hourly using peaking pattern.", "Daily to Hourly")
		
		
####	Populate hourly table with selected day from daily table
	def edit_Hourly(self):
		selectedDay = self.dailyTable.getSelectedRow()
		if selectedDay < 0:
			JOptionPane.showMessageDialog(
				self,
				"Please select a day first",
				"No Day Selected",
				JOptionPane.WARNING_MESSAGE
			)
			return
		
		dayStart = HecTime(); dayStart.set(forecast_time); dayStart.setTime("01:00")
		dayStart.addDays(selectedDay)
		dayEnd = HecTime(); dayEnd.set(forecast_time); dayEnd.setTime("24:00")
		dayEnd.addDays(selectedDay)
		
		HOTFile.setTimeWindow(str(dayStart), str(dayEnd))
		
		daySel = HecTime(); daySel.set(forecast_time); daySel.setTime("12:00")
		daySel.addDays(selectedDay)
		dateSel = date(daySel.year(), daySel.month(), daySel.day())
		datestr = dateSel.strftime("%d-%b, %a")
		self.lblHourly.setText("Hourly Hydropower Overrides for " + datestr)
		
		PoolElev_Hr = HOTFile.get("//"+ProjectName+"-Pool/Elev//1Hour/"+ActiveRSSAlt_Fpart+"/")
		Inflow_Hr = HOTFile.get("//"+ProjectName+"-Pool/Flow-IN//1Hour/"+ActiveRSSAlt_Fpart+"/")
		Outflow_Hr = HOTFile.get("//"+ProjectName+"-Pool/Flow-OUT//1Hour/"+ActiveRSSAlt_Fpart+"/")
		Power_Hr = HOTFile.get("//"+ProjectName+"-"+PowerName+"/Power//1Hour/"+ActiveRSSAlt_Fpart+"/")
		EF_Hr = HOTFile.get("//"+ProjectName+"-"+PowerName+"/EF//1Hour/"+ActiveRSSAlt_Fpart+"/")
		NoUnits_Hr = HOTFile.get("//"+ProjectName+"-"+PowerName+"/Units//1Hour/"+ActiveRSSAlt_Fpart+"/")
		Turbine_Hr = HOTFile.get("//"+ProjectName+"-"+PowerName+"/Flow//1Hour/"+ActiveRSSAlt_Fpart+"/")
		outletTS_Hr = []
		for o in OutletNames:
			path = "//%s-%s/Flow//1Hour/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart)
			tsc = HOTFile.get(path)
			outletTS_Hr.append(tsc)
		
		hourlyData = []
		for i in range(24):
			label_H = "%02d:00" % (i+1)
			row = [
				label_H,
				round(PoolElev_Hr.values[i],2),
				round(Inflow_Hr.values[i],0),
				round(Power_Hr.values[i],0), #MW_UH, #round(Power_Hr.values[i+1],0),
				round(EF_Hr.values[i],0),
				round(NoUnits_Hr.values[i],0),
				round(Turbine_Hr.values[i],-1),
			]
			flows = [round(ts.values[i],-1) for ts in outletTS_Hr]
			row.extend(flows)
			row.append(round(Outflow_Hr.values[i],-1))
			hourlyData.append(row)
		
		self.dayStart_str = str(dayStart)
		self.dayEnd_str = str(dayEnd)
		
		self.hourlyModel = MyTableModel(hourlyData, self.hourCols, self.hourlyEditableCols)
		self.hourlyTable.setModel(self.hourlyModel)
		
	
####	Compute daily flows from power information and recompute pool elev
	def compute_P2Q(self):
		model = self.dailyTable.getModel() 
		n = model.getRowCount()
		
		if n == 0:
			JOptionPane.showMessageDialog(
				self,
				"No daily data loaded",
				"Error",
				JOptionPane.ERROR_MESSAGE
			)
			return
		
		dailyVals = []
		firstOutletCol = 8
		for i in range(n):
			vals = {
				'power':	float(model.getValueAt(i, 4)),	# MW
				'ef':		float(model.getValueAt(i, 5)),	# dsf/UH
				'units':	float(model.getValueAt(i, 6)),	# Quantity
			}
			for j, outlet in enumerate(OutletNames):
				vals[outlet] = float(model.getValueAt(i, firstOutletCol + j))
			dailyVals.append(vals)
		
		specs = [
			('power',	"//"+ProjectName+"-"+PowerName+"/Power-Demand//1Day/"+ActiveRSSAlt_Fpart+"/",	'MW',		'PER-AVER'),
			('ef',		"//"+ProjectName+"-"+PowerName+"/EF//1Day/"+ActiveRSSAlt_Fpart+"/",				'CFS',		'PER-AVER'),
			('units',	"//"+ProjectName+"-"+PowerName+"/Units//1Day/"+ActiveRSSAlt_Fpart+"/",			'Quantity',	'PER-AVER'),
		]
		for o in OutletNames:
			specs.append((o, "//%s-%s/Flow//1Day/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart),			'CFS',	'PER-AVER'))
		
		self._create_Daily_TS(forecast_time, dailyVals, specs)
		
		##	Controlling Power
		HOTFile.setTimeWindow(forecast_time, end_time)
		PowerDemand	= HOTFile.read("//"+ProjectName+"-"+PowerName+"/Power-Demand//1Day/"+ActiveRSSAlt_Fpart+"/")
		EF			= HOTFile.read("//"+ProjectName+"-"+PowerName+"/EF//1Day/"+ActiveRSSAlt_Fpart+"/")
		NoUnits		= HOTFile.read("//"+ProjectName+"-"+PowerName+"/Units//1Day/"+ActiveRSSAlt_Fpart+"/")
		OutletTS	= [HOTFile.read("//%s-%s/Flow//1Day/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart)) for o in OutletNames]
		
		MaxPowerUH	= NoUnits.multiply(24)
		PowerCap	= MaxPowerUH.multiply(MW_UH)
		PowerCap.setUnits("MW")
		PowerCap.setParameterPart("Power-Capacity")
		PowerCap.setType("PER-AVER")
		HOTFile.write(PowerCap)
		
		Power1	= PowerDemand.subtract(PowerCap)
		Power2	= Power1.screenWithMaxMin(0.0, 1000000.0, 1000000.0, 1, 0.0, "")
		Power	= PowerDemand.subtract(Power2)
		Power.setParameterPart("Power")
		HOTFile.write(Power)
		
		Power.setType("INST-VAL")
		Power_2 = Power.shiftInTime("-23H")
		Power_3 = Power_2.mergeTimeSeries(Power)
		Power_4 = Power_3.transformTimeSeries("1Hour", "0M", "INT")
		Power_Hr = Power_4.divide(24)
		Power_Hr.setVersion(ActiveRSSAlt_Fpart)
		HOTFile.write(Power_Hr)
		
		Flow2Power = EF.divide(MW_UH)
		Turbine = Power.multiply(Flow2Power)
		Turbine.setUnits("CFS")
		Turbine.setParameterPart("Flow")
		Turbine.setType("PER-AVER")
		HOTFile.write(Turbine)
		
		Outflow = Turbine
		for ts in OutletTS:
			Outflow = Outflow.add(ts)
		Outflow.setPathname("//%s-Pool/Flow-OUT//1Day/%s/" % (ProjectName, ActiveRSSAlt_Fpart))
		Outflow.setType("PER-AVER")
		HOTFile.write(Outflow)
		
		pathnames = [
			"//"+ProjectName+"-"+PowerName+"/EF//1Day/"+ActiveRSSAlt_Fpart+"/",
			"//"+ProjectName+"-"+PowerName+"/Units//1Day/"+ActiveRSSAlt_Fpart+"/",
			"//"+ProjectName+"-"+PowerName+"/Flow//1Day/"+ActiveRSSAlt_Fpart+"/",
		] + [
			"//%s-%s/Flow//1Day/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart) for o in OutletNames
		] + [
			"//"+ProjectName+"-Pool/Flow-OUT//1Day/"+ActiveRSSAlt_Fpart+"/"
		]
		
		self._Daily_to_Hourly(pathnames)
		self._recompute_Pool_Elev()
		self.load_Daily()
		
	
####	Compute daily power from flow information and recompute pool elev
	def compute_Q2P(self):
		model = self.dailyTable.getModel() 
		n = model.getRowCount()
		
		if n == 0:
			JOptionPane.showMessageDialog(
				self,
				"No daily data loaded",
				"Error",
				JOptionPane.ERROR_MESSAGE
			)
			return
		
		dailyVals = []
		firstOutletCol = 8
		for i in range(n):
			vals = {
				'ef':		float(model.getValueAt(i, 5)),	# dsf/UH
				'units':	float(model.getValueAt(i, 6)),	# Quantity
				'turbine':	float(model.getValueAt(i, 7)),	# cfs
			}
			for j, outlet in enumerate(OutletNames):
				vals[outlet] = float(model.getValueAt(i, firstOutletCol + j))
			vals['outflow'] = float(model.getValueAt(i, firstOutletCol + NoOutlets))
			dailyVals.append(vals)
		
		specs = [
			('ef',		"//"+ProjectName+"-"+PowerName+"/EF//1Day/"+ActiveRSSAlt_Fpart+"/",			'CFS',		'PER-AVER'),
			('units',	"//"+ProjectName+"-"+PowerName+"/Units//1Day/"+ActiveRSSAlt_Fpart+"/",		'Quantity',	'PER-AVER'),
			('turbine',	"//"+ProjectName+"-"+PowerName+"/Flow-Demand//1Day/"+ActiveRSSAlt_Fpart+"/",'CFS',		'PER-AVER'),
		]
		for o in OutletNames:
			specs.append((o, "//%s-%s/Flow//1Day/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart),		'CFS',		'PER-AVER'))
		specs.append(('outflow', "//"+ProjectName+"-Pool/Flow-OUT//1Day/"+ActiveRSSAlt_Fpart+"/",	'CFS',		'PER-AVER'))
		
		self._create_Daily_TS(forecast_time, dailyVals, specs)
		
		##	Compute controlling outflow
		HOTFile.setTimeWindow(forecast_time, end_time)
		EF				= HOTFile.read("//"+ProjectName+"-"+PowerName+"/EF//1Day/"+ActiveRSSAlt_Fpart+"/")
		NoUnits			= HOTFile.read("//"+ProjectName+"-"+PowerName+"/Units//1Day/"+ActiveRSSAlt_Fpart+"/")
		TurbineDemand	= HOTFile.read("//"+ProjectName+"-"+PowerName+"/Flow-Demand//1Day/"+ActiveRSSAlt_Fpart+"/")
		OutletTS		= [HOTFile.read("//%s-%s/Flow//1Day/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart)) for o in OutletNames]
		
		##	Controlling Flow
		MaxPowerUH = NoUnits.multiply(24)
		TurbineCap = MaxPowerUH.multiply(EF)
		TurbineCap.setUnits("CFS")
		TurbineCap.setParameterPart("Flow-Capacity")
		HOTFile.write(TurbineCap)
		
		Turbine1 = TurbineDemand.subtract(TurbineCap)
		Turbine2 = Turbine1.screenWithMaxMin(0.0, 1000000.0, 1000000.0, 1, 0.0, "")
		Turbine = TurbineDemand.subtract(Turbine2)
		Turbine.setParameterPart("Flow")
		Turbine.setType("PER-AVER")
		HOTFile.write(Turbine)
		
		Flow2Power = EF.divide(MW_UH)
		Power = Turbine.divide(Flow2Power)
		Power.setUnits("MW")
		Power.setParameterPart("Power")
		Power.setType("PER-AVER")
		HOTFile.write(Power)
		
		Power.setType("INST-VAL")
		Power_2 = Power.shiftInTime("-23H")
		Power_3 = Power_2.mergeTimeSeries(Power)
		Power_4 = Power_3.transformTimeSeries("1Hour", "0M", "INT")
		Power_Hr = Power_4.divide(24)
		Power_Hr.setVersion(ActiveRSSAlt_Fpart)
		Power_Hr.setType("PER-AVER")
		HOTFile.write(Power_Hr)
		
		Outflow = Turbine
		for ts in OutletTS:
			Outflow = Outflow.add(ts)
		Outflow.setPathname("//%s-Pool/Flow-OUT//1Day/%s/" % (ProjectName, ActiveRSSAlt_Fpart))
		Outflow.setType("PER-AVER")
		HOTFile.write(Outflow)
		
		pathnames = [
			"//"+ProjectName+"-"+PowerName+"/EF//1Day/"+ActiveRSSAlt_Fpart+"/",
			"//"+ProjectName+"-"+PowerName+"/Units//1Day/"+ActiveRSSAlt_Fpart+"/",
			"//"+ProjectName+"-"+PowerName+"/Flow//1Day/"+ActiveRSSAlt_Fpart+"/",
		] + [
			"//%s-%s/Flow//1Day/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart) for o in OutletNames
		] + [
			"//"+ProjectName+"-Pool/Flow-OUT//1Day/"+ActiveRSSAlt_Fpart+"/"
		]

		self._Daily_to_Hourly(pathnames)
		self._recompute_Pool_Elev()
		self.load_Daily()
		
	
####	Create TS for select values from the daily table
	def _create_Daily_TS(self, start_time_str, dailyVals, specs):
		ht = HecTime()
		ht.set(start_time_str)
		ht.setTime("2400")
		times = []
		for i in range(len(dailyVals)):
			times.append(ht.value())
			ht.add(1440)
		
		for key, pathName, units, val_type in specs:
			c = TimeSeriesContainer()
			c.fullName		= pathName
			c.times			= times
			c.values		= [ day[key] for day in dailyVals ]
			c.numberValues	= len(c.values)
			c.interval		= 1440
			c.units			= units
			c.type			= val_type
			HOTFile.put(c)
		
		
####	Translate daily TS to hourly by uniform dissagragtion 
	def _Daily_to_Hourly(self, pathnames):
		
		HOTFile.setTimeWindow(forecast_time, end_time)
		for path in pathnames:
			ts			= HOTFile.read(path)
			ts.setType("INST-VAL")
			ts_shift	= ts.shiftInTime("-23H")
			ts_24hr		= ts_shift.mergeTimeSeries(ts)
			ts_hr		= ts_24hr.transformTimeSeries("1Hour", "0M", "INT")
			ts_hr.setVersion(ActiveRSSAlt_Fpart)
			ts_hr.setType("PER-AVER")
			HOTFile.write(ts_hr)
		
		
####	Compute hourly flows from power information and recompute pool elev
	def compute_Hourly_P2Q(self):
		
		model = self.hourlyTable.getModel() 
		n = model.getRowCount()
		
		if n == 0:
			JOptionPane.showMessageDialog(
				self,
				"No daily data loaded",
				"Error",
				JOptionPane.ERROR_MESSAGE
			)
			return
		
		hourlyVals = []
		firstOutletCol = 7
		for i in range(n):
			vals = {
				'power':	float(model.getValueAt(i, 3)),	# MW
				'ef':		float(model.getValueAt(i, 4)),	# dsf/UH
				'units':	float(model.getValueAt(i, 5)),	# Quantity
			}
			for j, outlet in enumerate(OutletNames):
				vals[outlet] = float(model.getValueAt(i, firstOutletCol + j))
			hourlyVals.append(vals)
		
		specs = [
			('power',	"//"+ProjectName+"-"+PowerName+"/Power-Demand//1Hour/"+ActiveRSSAlt_Fpart+"/",	'MW',		'PER-AVER'),
			('ef',		"//"+ProjectName+"-"+PowerName+"/EF//1Hour/"+ActiveRSSAlt_Fpart+"/",			'CFS',		'PER-AVER'),
			('units',	"//"+ProjectName+"-"+PowerName+"/Units//1Hour/"+ActiveRSSAlt_Fpart+"/",			'Quantity',	'PER-AVER'),
		]
		for o in OutletNames:
			specs.append((o, "//%s-%s/Flow//1Hour/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart),			'CFS',		'PER-AVER'))
		
		self._create_Hourly_TS(self.dayStart_str, hourlyVals, specs)
		
		##	Controlling Power
		HOTFile.setTimeWindow(self.dayStart_str, self.dayEnd_str)
		PowerDemand	= HOTFile.read("//"+ProjectName+"-"+PowerName+"/Power-Demand//1Hour/"+ActiveRSSAlt_Fpart+"/")
		EF			= HOTFile.read("//"+ProjectName+"-"+PowerName+"/EF//1Hour/"+ActiveRSSAlt_Fpart+"/")
		NoUnits		= HOTFile.read("//"+ProjectName+"-"+PowerName+"/Units//1Hour/"+ActiveRSSAlt_Fpart+"/")
		OutletTS	= [HOTFile.read("//%s-%s/Flow//1Hour/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart)) for o in OutletNames]
		
		PowerCap	= NoUnits.multiply(MW_UH)
		PowerCap.setUnits("MW")
		PowerCap.setParameterPart("Power-Capacity")
		HOTFile.write(PowerCap)
		
		Power1	= PowerDemand.subtract(PowerCap)
		Power2	= Power1.screenWithMaxMin(0.0, 1000000.0, 1000000.0, 1, 0.0, "")
		Power	= PowerDemand.subtract(Power2)
		Power.setParameterPart("Power")
		HOTFile.write(Power)
		
		Flow2Power = EF.divide(MW_UH).multiply(24)
		Turbine = Power.multiply(Flow2Power)
		Turbine.setUnits("CFS")
		Turbine.setParameterPart("Flow")
		Turbine.setType("PER-AVER")
		HOTFile.write(Turbine)
		
		Power_1 = Power.accumulation()
		#Power_1 = Power.shiftInTime("0H")
		Power_D = Power_1.transformTimeSeries("1Day", "0M", "INT")
		Power_D.setVersion(ActiveRSSAlt_Fpart)
		Power_D.setType("PER-AVER")
		HOTFile.write(Power_D)
		
		Outflow = Turbine
		for ts in OutletTS:
			Outflow = Outflow.add(ts)
		Outflow.setPathname("//%s-Pool/Flow-OUT//1Hour/%s/" % (ProjectName, ActiveRSSAlt_Fpart))
		Outflow.setType("PER-AVER")
		HOTFile.write(Outflow)
		
		pathnames = [
			"//"+ProjectName+"-"+PowerName+"/EF//1Hour/"+ActiveRSSAlt_Fpart+"/",
			"//"+ProjectName+"-"+PowerName+"/Units//1Hour/"+ActiveRSSAlt_Fpart+"/",
			"//"+ProjectName+"-"+PowerName+"/Flow//1Hour/"+ActiveRSSAlt_Fpart+"/",
		] + [
			"//%s-%s/Flow//1Hour/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart) for o in OutletNames
		] + [
			"//"+ProjectName+"-Pool/Flow-OUT//1Hour/"+ActiveRSSAlt_Fpart+"/"
		]
		
		self._Hourly_to_Daily(pathnames)
		self._recompute_Pool_Elev()
		self.load_Daily()
		self.load_Hourly()
		
		
####	Compute hourly power from flow information and recompute pool elev
	def compute_Hourly_Q2P(self):
		
		model = self.hourlyTable.getModel() 
		n = model.getRowCount()
		
		if n == 0:
			JOptionPane.showMessageDialog(
				self,
				"No daily data loaded",
				"Error",
				JOptionPane.ERROR_MESSAGE
			)
			return
		
		hourlyVals = []
		firstOutletCol = 7
		for i in range(n):
			vals = {
				'ef':		float(model.getValueAt(i, 4)),	# dsf/UH
				'units':	float(model.getValueAt(i, 5)),	# Quantity
				'turbine':	float(model.getValueAt(i, 6)),	# cfs
			}
			for j, outlet in enumerate(OutletNames):
				vals[outlet] = float(model.getValueAt(i, firstOutletCol + j))
			vals['outflow'] = float(model.getValueAt(i, firstOutletCol + NoOutlets))
			hourlyVals.append(vals)
		
		specs = [
			('ef',		"//"+ProjectName+"-"+PowerName+"/EF//1Hour/"+ActiveRSSAlt_Fpart+"/",			'CFS',		'PER-AVER'),
			('units',	"//"+ProjectName+"-"+PowerName+"/Units//1Hour/"+ActiveRSSAlt_Fpart+"/",			'Quantity',	'PER-AVER'),
			('turbine',	"//"+ProjectName+"-"+PowerName+"/Flow-Demand//1Hour/"+ActiveRSSAlt_Fpart+"/",	'CFS',		'PER-AVER'),
		]
		for o in OutletNames:
			specs.append((o, "//%s-%s/Flow//1Hour/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart),			'CFS',		'PER-AVER'))
		specs.append(('outflow', "//"+ProjectName+"-Pool/Flow-OUT//1Hour/"+ActiveRSSAlt_Fpart+"/",		'CFS',		'PER-AVER'))
		
		self._create_Hourly_TS(self.dayStart_str, hourlyVals, specs)
		
		##	Controlling Power
		HOTFile.setTimeWindow(self.dayStart_str, self.dayEnd_str)
		EF				= HOTFile.read("//"+ProjectName+"-"+PowerName+"/EF//1Hour/"+ActiveRSSAlt_Fpart+"/")
		NoUnits			= HOTFile.read("//"+ProjectName+"-"+PowerName+"/Units//1Hour/"+ActiveRSSAlt_Fpart+"/")
		TurbineDemand	= HOTFile.read("//"+ProjectName+"-"+PowerName+"/Flow-Demand//1Hour/"+ActiveRSSAlt_Fpart+"/")
		OutletTS		= [HOTFile.read("//%s-%s/Flow//1Hour/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart)) for o in OutletNames]
		
		TurbineCap = EF.multiply(NoUnits).multiply(24)
		TurbineCap.setUnits("CFS")
		TurbineCap.setParameterPart("Flow-Capacity")
		HOTFile.write(TurbineCap)
		
		Turbine1 = TurbineDemand.subtract(TurbineCap)
		Turbine2 = Turbine1.screenWithMaxMin(0.0, 1000000.0, 1000000.0, 1, 0.0, "")
		Turbine	= TurbineDemand.subtract(Turbine2)
		Turbine.setParameterPart("Flow")
		Turbine.setType("PER-AVER")
		HOTFile.write(Turbine)
		
		Flow2Power = EF.divide(MW_UH).multiply(24)
		Power = Turbine.divide(Flow2Power)
		Power.setUnits("CFS")
		Power.setParameterPart("Power")
		Power.setType("PER-AVER")
		HOTFile.write(Power)
		
		Power_1 = Power.accumulation()
		Power_D = Power_1.transformTimeSeries("1Day", "0M", "INT")
		Power_D.setVersion(ActiveRSSAlt_Fpart)
		Power_D.setType("PER-AVER")
		HOTFile.write(Power_D)
		
		Outflow = Turbine
		for ts in OutletTS:
			Outflow = Outflow.add(ts)
		Outflow.setPathname("//%s-Pool/Flow-OUT//1Hour/%s/" % (ProjectName, ActiveRSSAlt_Fpart))
		Outflow.setType("PER-AVER")
		HOTFile.write(Outflow)
		
		pathnames = [
			"//"+ProjectName+"-"+PowerName+"/EF//1Hour/"+ActiveRSSAlt_Fpart+"/",
			"//"+ProjectName+"-"+PowerName+"/Units//1Hour/"+ActiveRSSAlt_Fpart+"/",
			"//"+ProjectName+"-"+PowerName+"/Flow//1Hour/"+ActiveRSSAlt_Fpart+"/",
		] + [
			"//%s-%s/Flow//1Hour/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart) for o in OutletNames
		] + [
			"//"+ProjectName+"-Pool/Flow-OUT//1Hour/"+ActiveRSSAlt_Fpart+"/"
		]
		
		self._Hourly_to_Daily(pathnames)
		self._recompute_Pool_Elev()
		self.load_Daily()
		self.load_Hourly()
		
	
####	Create TS for select values from the hourly table
	def _create_Hourly_TS(self, start_time_str, hourlyVals, specs):
		ht = HecTime()
		ht.set(start_time_str)
		times = []
		for i in range(24):
			times.append(ht.value())
			ht.add(60)
		
		for key, pathName, units, val_type in specs:
			c = TimeSeriesContainer()
			c.fullName		= pathName
			c.times			= times
			c.values		= [ hour[key] for hour in hourlyVals ]
			c.numberValues	= len(c.values)
			c.interval		= 60
			c.units			= units
			c.type			= val_type
			HOTFile.put(c)
		
		
####	Translate daily TS to hourly by uniform dissagragtion 
	def _Hourly_to_Daily(self, pathnames):
		
		HOTFile.setTimeWindow(self.dayStart_str, self.dayEnd_str)
		for path in pathnames:
			ts			= HOTFile.read(path)
			#ts_shift	= ts.shiftInTime("1H")
			ts_day		= ts.transformTimeSeries("1Day", "0M", "AVE")
			ts_day.setVersion(ActiveRSSAlt_Fpart)
			ts_day.setType("PER-AVER")
			HOTFile.write(ts_day)
		
		
####	Load daily data from HOT.dss to daily table
	def load_Hourly(self):
		HOTFile.setTimeWindow(self.dayStart_str, self.dayEnd_str)
		
		PoolElev_Hr = HOTFile.get("//"+ProjectName+"-Pool/Elev//1Hour/"+ActiveRSSAlt_Fpart+"/")
		Inflow_Hr = HOTFile.get("//"+ProjectName+"-Pool/Flow-IN//1Hour/"+ActiveRSSAlt_Fpart+"/")
		Outflow_Hr = HOTFile.get("//"+ProjectName+"-Pool/Flow-OUT//1Hour/"+ActiveRSSAlt_Fpart+"/")
		Power_Hr = HOTFile.get("//"+ProjectName+"-"+PowerName+"/Power//1Hour/"+ActiveRSSAlt_Fpart+"/")
		EF_Hr = HOTFile.get("//"+ProjectName+"-"+PowerName+"/EF//1Hour/"+ActiveRSSAlt_Fpart+"/")
		NoUnits_Hr = HOTFile.get("//"+ProjectName+"-"+PowerName+"/Units//1Hour/"+ActiveRSSAlt_Fpart+"/")
		Turbine_Hr = HOTFile.get("//"+ProjectName+"-"+PowerName+"/Flow//1Hour/"+ActiveRSSAlt_Fpart+"/")
		outletTS_Hr = []
		for o in OutletNames:
			path = "//%s-%s/Flow//1Hour/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart)
			tsc = HOTFile.get(path)
			outletTS_Hr.append(tsc)
		
		hourlyData = []
		for i in range(24):
			label_H = "%02d:00" % (i+1)
			row = [
				label_H,
				round(PoolElev_Hr.values[i],2),
				round(Inflow_Hr.values[i],0),
				round(Power_Hr.values[i],0), #MW_UH, #round(Power_Hr.values[i+1],0),
				round(EF_Hr.values[i],0),
				round(NoUnits_Hr.values[i],0),
				round(Turbine_Hr.values[i],-1),
			]
			flows = [round(ts.values[i],-1) for ts in outletTS_Hr]
			row.extend(flows)
			row.append(round(Outflow_Hr.values[i],-1))
			hourlyData.append(row)
		
		self.hourlyModel = MyTableModel(hourlyData, self.hourCols, self.hourlyEditableCols)
		self.hourlyTable.setModel(self.hourlyModel)
		
		
####	Recompute pool elev
	def _recompute_Pool_Elev(self):
		HOTFile.setTimeWindow(forecast_time, end_time)
		PoolStor_1Hr	= HOTFile.read("//"+ProjectName+"-Pool/Stor//1Hour/"+ActiveRSSAlt_Fpart+"/")
		NetInflow_1Hr	= HOTFile.read("//"+ProjectName+"-Pool/Flow-IN NET//1Hour/"+ActiveRSSAlt_Fpart+"/")
		Outflow_1Hr		= HOTFile.read("//"+ProjectName+"-Pool/Flow-OUT//1Hour/"+ActiveRSSAlt_Fpart+"/")
		ElevStor		= HOTFile.read("/"+ProjectName+"/Pool-Area Capacity/Elev-Stor-Area////")
		
		InitialStor = PoolStor_1Hr.firstValidValue()
		NetHoldout_1Hr = NetInflow_1Hr.subtract(Outflow_1Hr)
		NetHoldout_1Hr.setType("INST-CUM")
		CumulativeHoldout_1Hr = NetHoldout_1Hr.accumulation()
		##(convert cfs-days to ac-ft (1.983744 ac-ft/cfs-day) & incremental time step (24 hrs/day) ~ 24 hrs/day / 1.983744 ac-ft/cfs-days ~ 12.09835)
		CumulativeHoldoutStor_1Hr = CumulativeHoldout_1Hr.divide(12.09835)
		UpdatedPoolStor_1Hr = CumulativeHoldoutStor_1Hr.add(InitialStor)
		UpdatedPoolStor_1Hr.setParameterPart("Stor")
		UpdatedPoolElev_1Hr = ElevStor.reverseRatingTableInterpolation(UpdatedPoolStor_1Hr)
		
		UpdatedPoolElev_1D = UpdatedPoolElev_1Hr.transformTimeSeries("1Day", "0M", "INT")
		HOTFile.write(UpdatedPoolElev_1Hr)
		HOTFile.write(UpdatedPoolElev_1D)
		
		
################################
####	HOT PLot Section	####
################################
	def plot_HOT_Edits(self):
		##	Get data
		HOTFile.setTimeWindow(forecast_time, end_time)
		PoolElev	= HOTFile.get("//"+ProjectName+"-Pool/Elev//1Hour/"+ActiveRSSAlt_Fpart+"/")
		Inflow		= HOTFile.get("//"+ProjectName+"-Pool/Flow-IN//1Hour/"+ActiveRSSAlt_Fpart+"/")
		Turbine_Q	= HOTFile.get("//"+ProjectName+"-"+PowerName+"/Flow//1Hour/"+ActiveRSSAlt_Fpart+"/")
		Outlets_Q	= [HOTFile.get("//%s-%s/Flow//1Hour/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart)) for o in OutletNames]
		Total_Q		= HOTFile.get("//"+ProjectName+"-Pool/Flow-OUT//1Hour/"+ActiveRSSAlt_Fpart+"/")
		
		##	Create Plot for HOT edited data
		HOT_Plot = Plot.newPlot("Hydropower Override Tool")
		HOT_Plot.addData(PoolElev)
		HOT_Plot.addData(Inflow)
		HOT_Plot.addData(Total_Q)
		for ts in Outlets_Q:
			HOT_Plot.addData(ts)
		HOT_Plot.addData(Turbine_Q)
		HOT_Plot.showPlot()
		
		##	Plot Line Styles
		InflowCurve = HOT_Plot.getCurve(Inflow)
		InflowCurve.setLineColor("darkgray")
		InflowCurve.setLineStyle("dash dot")
		TurbineCurve = HOT_Plot.getCurve(Turbine_Q)
		TurbineCurve.setLineColor("darkred")
		TotalCurve = HOT_Plot.getCurve(Total_Q)
		TotalCurve.setLineColor("darkgreen")
		TotalCurve.setLineWidth(4)
		
			
	def plot_HOT_Forecast(self):
		##	Get data from HOT.dss
		HOTFile.setTimeWindow(forecast_time, end_time)
		HOT_PoolElev = HOTFile.read("//"+ProjectName+"-Pool/Elev//1Hour/"+ActiveRSSAlt_Fpart+"/")
		HOT_Inflow = HOTFile.read("//"+ProjectName+"-Pool/Flow-IN//1Hour/"+ActiveRSSAlt_Fpart+"/")
		HOT_Total_Q = HOTFile.read("//"+ProjectName+"-Pool/Flow-OUT//1Hour/"+ActiveRSSAlt_Fpart+"/")
		HOT_PoolElev.setVersion("HOT")
		HOT_Total_Q.setVersion("HOT")
		
		##	Get data from forecast.dss
		cwmsFile.setTimeWindow(forecast_time, end_time)
		CWMS_PoolElev = cwmsFile.read("//"+ProjectName+"-Pool/Elev//1Hour/"+ActiveRSSAlt_Fpart+"/")
		CWMS_Total_Q = cwmsFile.read("//"+ProjectName+"-Pool/Flow-OUT//1Hour/"+ActiveRSSAlt_Fpart+"/")
		CWMS_PoolElev.setVersion("ResSim")
		CWMS_Total_Q.setVersion("ResSim")
		
		
		##	Create Plot for HOT edited data
		Comp_Plot = Plot.newPlot("Hydropower Override Tool vs ResSim Simulation")
		Comp_Plot.addData(HOT_PoolElev.getData())
		Comp_Plot.addData(CWMS_PoolElev.getData())
		Comp_Plot.addData(HOT_Inflow.getData())
		Comp_Plot.addData(HOT_Total_Q.getData())
		Comp_Plot.addData(CWMS_Total_Q.getData())
		Comp_Plot.showPlot()
		
		##	Plot Line Styles
		HOT_PoolElevCurve = Comp_Plot.getCurve(HOT_PoolElev)
		HOT_PoolElevCurve.setLineColor("darkgreen")
		HOT_PoolElevCurve.setLineWidth(4)
		CWMS_PoolElevCurve = Comp_Plot.getCurve(CWMS_PoolElev)
		CWMS_PoolElevCurve.setLineColor("lightgreen")
		CWMS_PoolElevCurve.setLineStyle("dash")
		HOT_InflowCurve = Comp_Plot.getCurve(HOT_Inflow)
		HOT_InflowCurve.setLineColor("darkgray")
		HOT_InflowCurve.setLineStyle("dash dot")
		
		HOT_TotalCurve = Comp_Plot.getCurve(HOT_Total_Q)
		HOT_TotalCurve.setLineColor("darkgreen")
		HOT_TotalCurve.setLineWidth(4)
		CWMS_TotalCurve = Comp_Plot.getCurve(CWMS_Total_Q)
		CWMS_TotalCurve.setLineColor("lightgreen")
		CWMS_TotalCurve.setLineStyle("dash")
		
		
	def plot_Daily_Hourly(self):
		##	Get data
		HOTFile.setTimeWindow(forecast_time, end_time)
		PoolElev_H = HOTFile.get("//"+ProjectName+"-Pool/Elev//1Hour/"+ActiveRSSAlt_Fpart+"/")
		Inflow_H = HOTFile.get("//"+ProjectName+"-Pool/Flow-IN//1Hour/"+ActiveRSSAlt_Fpart+"/")
		Turbine_Q_H = HOTFile.get("//"+ProjectName+"-"+PowerName+"/Flow//1Hour/"+ActiveRSSAlt_Fpart+"/")
		Outlets_Q_H	= [HOTFile.get("//%s-%s/Flow//1Hour/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart)) for o in OutletNames]
		Total_Q_H = HOTFile.get("//"+ProjectName+"-Pool/Flow-OUT//1Hour/"+ActiveRSSAlt_Fpart+"/")
		PoolElev_D = HOTFile.get("//"+ProjectName+"-Pool/Elev//1Day/"+ActiveRSSAlt_Fpart+"/")
		Inflow_D = HOTFile.get("//"+ProjectName+"-Pool/Flow-IN//1Day/"+ActiveRSSAlt_Fpart+"/")
		Turbine_Q_D = HOTFile.get("//"+ProjectName+"-"+PowerName+"/Flow//1Day/"+ActiveRSSAlt_Fpart+"/")
		Outlets_Q_D	= [HOTFile.get("//%s-%s/Flow//1Day/%s/" % (ProjectName, o, ActiveRSSAlt_Fpart)) for o in OutletNames]
		Total_Q_D = HOTFile.get("//"+ProjectName+"-Pool/Flow-OUT//1Day/"+ActiveRSSAlt_Fpart+"/")
		
		##	Create Plot for HOT edited data
		HOT_Plot = Plot.newPlot("Hydropower Override Tool")
		HOT_Plot.addData(PoolElev_D)
		HOT_Plot.addData(PoolElev_H)
		HOT_Plot.addData(Inflow_D)
		HOT_Plot.addData(Inflow_H)
		HOT_Plot.addData(Total_Q_D)
		HOT_Plot.addData(Total_Q_H)
		for ts in Outlets_Q_D:
			HOT_Plot.addData(ts)
		for ts in Outlets_Q_H:
			HOT_Plot.addData(ts)
		HOT_Plot.addData(Turbine_Q_D)
		HOT_Plot.addData(Turbine_Q_H)
		HOT_Plot.showPlot()
		
		##	Plot Line Styles
		H_InflowCurve = HOT_Plot.getCurve(Inflow_H)
		H_InflowCurve.setLineColor("darkgray")
		H_InflowCurve.setLineStyle("dash dot")
		D_InflowCurve = HOT_Plot.getCurve(Inflow_D)
		D_InflowCurve.setLineColor("gray")
		D_InflowCurve.setLineWidth(4)
		H_TurbineCurve = HOT_Plot.getCurve(Turbine_Q_H)
		H_TurbineCurve.setLineColor("lightred")
		D_TurbineCurve = HOT_Plot.getCurve(Turbine_Q_D)
		D_TurbineCurve.setLineColor("darkred")
		D_TurbineCurve.setLineWidth(4)
		H_TotalCurve = HOT_Plot.getCurve(Total_Q_H)
		H_TotalCurve.setLineColor("lightgreen")
		D_TotalCurve = HOT_Plot.getCurve(Total_Q_D)
		D_TotalCurve.setLineColor("darkgreen")
		D_TotalCurve.setLineWidth(4)
		
		colors_H = ["lightblue","lightpurple","lightcyan","lightyellow"]
		for i, ts in enumerate(Outlets_Q_H):
			curve = HOT_Plot.getCurve(ts)
			curve.setLineColor(colors_H[i % len(colors_H)])
		colors_D = ["darkblue","darkpurple","darkcyan","darkyellow"]
		for i, ts in enumerate(Outlets_Q_D):
			curve = HOT_Plot.getCurve(ts)
			curve.setLineColor(colors_D[i % len(colors_D)])
			curve.setLineWidth(4)
		
		
########################################################
####	Save hourly flows to ResSim overrides file	####
########################################################
	def save_Overrides(self):
		HOTFile.setTimeWindow(forecast_time, end_time)
		OverrideFile.setTimeWindow(forecast_time, end_time)
		turbine_Overrides = HOTFile.read("//%s-%s/Flow//1Hour/%s/" % (ProjectName,PowerName,ActiveRSSAlt_Fpart))
		turbine_Overrides.setPathname("//%s-%s/Flow-RELEASE OVERRIDE//IR-Month//"%(ProjectName,PowerName))
		OverrideFile.write(turbine_Overrides)
		
		for o in OutletNames:
			o_ts = HOTFile.read("//%s-%s/Flow//1Hour/%s/" % (ProjectName,o,ActiveRSSAlt_Fpart))
			o_ts.setPathname("//%s-%s/Flow-RELEASE OVERRIDE//IR-Month//" % (ProjectName,o))
			OverrideFile.write(o_ts)
		
		JOptionPane.showMessageDialog(self,
				"Release overrides have been saved to ResSim",
				"Overrides Saved",
				JOptionPane.INFORMATION_MESSAGE)
		
		
def main():
	dialog = HOT(owner=ListSelection.getMainWindow(), title="Hydropower Override Tool")
	dialog.setVisible(True)

if __name__ == "__main__":
	main()
	
cwmsFile.done()
HOTFile.done()
OverrideFile.done()
RSSNetworkFile.done()