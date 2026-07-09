"""
 Version 1.1

 Author: Manju Sudhakar (manjus [at] ursc.gov.in)
 Date: December 23rd, 2024

 Description: Interactive display of HEL1OS light curve data
 (1) Prompts the user to select the file via a dilaog box. Each file corresponds to the time profile measured by either CdTe1, CdTe2, CZT1, CZT2
 (2) Plots the light curve in the entire energy range.
 (3) Prompts the user to zoom-in and select start-time (left mouse click) and end-time (right mouse click).
 (4) Prompts user if they are satisfied with the selected time range. If not user is allowed to re-select the time range until they are satisfied.
 (5) start and end times are stored.
 (6) User is prompted to select the energy range of interest, by selecting a number (e.g. "1" corresponds to the first energy range, "2" the second energy range, and so on). The user can select more than one energy range, and may indicate that they have completed the selection by typing "done".
 (7) User will be prompted if they are interested to view the selected energies plotted within the selected time interval. 
 (8) The selected energies, within the time-range of interest will be stored as global dataframes, which are available for further analysis by the user. 
 (9) An example is the "rebin_dataframe" function, which operates after the final selection of time range of interest and energies. 
    Usage: newdataframe = rebin_dataframe('dataframe',binsize)
    Here, 
    (a) <dataframe> refers to any one of the dataframes saved/stored after running the main workflow section,
    (b) binsize (in seconds) is an integer number which is a user-defined binsize for rebin: we have tested for 11, 15, 60,
    (c) <newdataframe> is the return value which will be renamed appropriately and returned to the user for further analysis.
    <dataframe> has three columns: TIME, COUNT_RATE, STAT_ERR
    <newdataframe> has two columns: COUNT_RATE, STAT_ERR. The 'TIME' column is now the index. 

 """
#===== Function Block Starts Here =======================================================================
# Copy paste the entire block up to "End of Function Block" into your python command line and run. This is where most of the work happens.
import os
import numpy as np
import pandas as pd
from astropy.io import fits
from astropy.time import Time
import matplotlib.pyplot as plt
from matplotlib.dates import num2date
from tkinter import Tk, filedialog

# Dictionary to store selected times
selected_times = {"start_time": None, "end_time": None}
click_count = {"left": 0}

plot_window = None
selected_dataframes = []

def on_click(event):
    """Handle mouse clicks for selecting time ranges."""
    if event.inaxes:  # Ensure the click is within a subplot
        x_data = event.xdata

        if event.button == 1:  # Left click
            click_count["left"] += 1

            # Ignore the first left click for zooming
            if click_count["left"] == 1:
                print("First left click detected, ignored (used for zooming).")
                return

            selected_times["start_time"] = num2date(x_data).strftime("%Y-%m-%d %H:%M:%S.%f")
            print(f"Start time selected: {selected_times['start_time']}")

        elif event.button == 3:  # Right click
            selected_times["end_time"] = num2date(x_data).strftime("%Y-%m-%d %H:%M:%S.%f")
            print(f"End time selected: {selected_times['end_time']}")

        # Check if both times are selected
        if selected_times["start_time"] and selected_times["end_time"]:
            prompt_user_for_confirmation()

def prompt_user_for_confirmation():
    """Prompt the user to confirm their selection."""
    print("Are you satisfied with the selection [yes/no]?")
    response = input().strip().lower()

    if response == "yes":
        global plot_window
        if plot_window:
            plt.close(plot_window)
        print(f"Final selected times:\nStart Time: {selected_times['start_time']}\nEnd Time: {selected_times['end_time']}")
        prompt_energy_range_selection()
    elif response == "no":
        print("Please zoom in and re-select the times.")
        reset_selection_and_plot()
    else:
        print("Invalid response. Please type 'yes' or 'no'.")
        prompt_user_for_confirmation()

def reset_selection_and_plot():
    """Reset the selection and re-enable zoom for the plot."""
    global binding_id, plot_window
    selected_times["start_time"] = None
    selected_times["end_time"] = None
    click_count["left"] = 0

    if plot_window:
        plt.close(plot_window)

    plot_window = plt.figure()
    plt.plot(time_utc, counts, label=energy_range)
    plt.xlabel("Time (UTC)")
    plt.ylabel("Count Rate")
    plt.title("Light Curve: Please reselect the Time Range of Interest")
    plt.legend()
    plt.grid()
    binding_id = plot_window.canvas.mpl_connect('button_press_event', on_click)
    plt.show()

def plot_selected_range():
    """Plot the final selected range."""
    start = pd.Timestamp(selected_times["start_time"])
    end = pd.Timestamp(selected_times["end_time"])
    mask = (time_utc >= start) & (time_utc <= end)

    plt.figure()
    stat_err = np.sqrt(counts[mask])  # Statistical errors
    plt.errorbar(time_utc[mask], counts[mask], yerr=stat_err, fmt='o', label=f"Selected Range: {energy_range}")
    plt.xlabel("Time (UTC)")
    plt.ylabel("Count Rate")
    plt.title("Selected Light Curve Range")
    plt.legend()
    plt.grid()
    plt.show()

def prompt_energy_range_selection():
    """Prompt the user to select energy ranges."""
    global selected_dataframes
    with fits.open(file_path) as hdul:
        energy_options = []
        for i, hdu in enumerate(hdul):
            if i == 0 or i == len(hdul) - 1:
                continue
            ext_name = hdu.header.get("EXTNAME", "")
            if "BAND_" in ext_name:
                energy_options.append((i, ext_name.split("BAND_")[-1]))

        if not energy_options:
            print("No energy ranges found in the FITS file.")
            return

        print("Which energy range would you like to plot?")
        for idx, (ext_idx, energy_range) in enumerate(energy_options):
            print(f"{idx + 1}. {energy_range}")

        while True:
            choice = input("Select an energy range by typing the corresponding number (or type 'done' to finish): ").strip().lower()
            if choice == "done":
                break

            try:
                choice_idx = int(choice) - 1
                if choice_idx < 0 or choice_idx >= len(energy_options):
                    raise ValueError
                ext_idx, selected_energy_range = energy_options[choice_idx]
                hdu = hdul[ext_idx]
                energy_data = pd.DataFrame({
                    "TIME": Time(hdu.data["MJD"], format="mjd").to_datetime(),
                    "COUNT_RATE": hdu.data["CTR"],
                    "STAT_ERR": np.sqrt(hdu.data["CTR"])  # Statistical errors
                })
                var_name = f"df{selected_energy_range.split('.')[0]}keVto{selected_energy_range.split('_TO_')[1].split('.')[0]}keV"
                globals()[var_name] = energy_data
                selected_dataframes.append((selected_energy_range, energy_data))
                print(f"Data for {selected_energy_range} stored in a dataframe named '{var_name}'.")
            except ValueError:
                print("Invalid choice. Please select a valid number.")

        if selected_dataframes:
            print("Would you like to see plots of the selected energy ranges? [yes/no]")
            response = input().strip().lower()
            if response == "yes":
                plot_energy_ranges()

def plot_energy_ranges():
    """Plot all selected energy ranges within the selected time range."""
    start = pd.Timestamp(selected_times["start_time"])
    end = pd.Timestamp(selected_times["end_time"])

    plt.figure()
    for energy_range, df in selected_dataframes:
        mask = (df["TIME"] >= start) & (df["TIME"] <= end)
        plt.errorbar(df["TIME"][mask], df["COUNT_RATE"][mask], yerr=df["STAT_ERR"][mask], label=f"Energy Range: {energy_range}")

    plt.yscale("log")
    plt.xlabel("Time (UTC)")
    plt.ylabel("Count Rate")
    plt.title("Light Curves for Selected Energy Ranges")
    plt.legend()
    plt.grid()
    plt.show()

    print("Dataframes for all selected energy ranges are available as global variables for further analysis.")
    for energy_range, _ in selected_dataframes:
        var_name = f"df{energy_range.split('.')[0]}keVto{energy_range.split('_TO_')[1].split('.')[0]}keV"
        print(f"- {var_name}")

def rebin_dataframe(df_name, bin_size):
    """Rebin a dataframe by the specified bin size in seconds."""
    try:
        df = globals()[df_name]
        df = df.set_index("TIME")
        df.index = pd.to_datetime(df.index)

        # Ensure data is in native byte order
        df["COUNT_RATE"] = df["COUNT_RATE"].values.astype(np.float64)
        rebinned_df = df.resample(f"{bin_size}S").sum()

        # Recompute statistical error after rebinning
        rebinned_df["STAT_ERR"] = np.sqrt(rebinned_df["COUNT_RATE"])

        rebinned_df_name = f"{df_name}_rebinned_{bin_size}s"
        globals()[rebinned_df_name] = rebinned_df
        print(f"Rebinned dataframe stored as global variable: {rebinned_df_name}")
        return rebinned_df
    except KeyError:
        print(f"Dataframe '{df_name}' not found. Please ensure it exists before attempting to rebin.")
        return None

#=====End of Function Block ======================================================

#===== Main workflow begins. =====================================================
# Copy and paste the following commands (up to plt.show() and before the comment block) into your python command line to run as a single block. 
root = Tk()
root.withdraw()  # Hide the main Tkinter window

print("Please select a FITS file.")
file_path = filedialog.askopenfilename(filetypes=[("FITS files", "*.fits")])

if not file_path:
    print("No file selected. Exiting.")
    exit()

# Open the FITS file and select the last extension
with fits.open(file_path) as hdul:
    last_ext = hdul[-1]
    ext_name = last_ext.header["EXTNAME"]
    energy_range = ext_name.split("BAND_")[-1]

    #print(f"Selected extension: {ext_name}")
    print(f"Energy range being displayed: {energy_range}")

    # Extract data
    print(last_ext.data.dtype.names)  # Print the column names to verify
    time_mjd = last_ext.data["MJD"]
    counts = last_ext.data["CTR"]

    # Convert MJD to UTC
    time_utc = Time(time_mjd, format="mjd").to_datetime()
    time_utc = pd.Series(time_utc)

# Plot the light curve
plot_window = plt.figure()
plt.plot(time_utc, counts, label=energy_range)
plt.xlabel("Time (UTC)")
plt.ylabel("Count Rate")
plt.title("Light Curve: Please use the zoom tool and select the Time Range of Interest")
plt.legend()
plt.grid()

# Connect the click handler
binding_id = plot_window.canvas.mpl_connect('button_press_event', on_click)
plt.show()

""" You will see the following prompts,
Please select a FITS file.
Energy range being displayed: 18.00KEV_TO_160.00KEV
First left click detected, ignored (used for zooming)."""
# after the second left click, this will be displayed
"""
Start time selected: 2024-07-17 06:34:06.291524 """
# after the righ click, this will be displayed
"""
End time selected: 2024-07-17 06:37:17.358199
Are you satisfied with the selection [yes/no]?"""
# user will type here
"""yes"""
# these will be displayed
"""
Final selected times:
Start Time: 2024-07-17 06:34:06.291524
End Time: 2024-07-17 06:37:17.358199"""
# this will be displayed
"""
Which energy range would you like to plot?
1. 20.00KEV_TO_40.00KEV
2. 40.00KEV_TO_60.00KEV
3. 60.00KEV_TO_80.00KEV
4. 80.00KEV_TO_150.00KEV
Select an energy range by typing the corresponding number (or type 'done' to finish): 1
Data for 20.00KEV_TO_40.00KEV stored in a dataframe named 'df20keVto40keV'.
Select an energy range by typing the corresponding number (or type 'done' to finish): 2
Data for 40.00KEV_TO_60.00KEV stored in a dataframe named 'df40keVto60keV'.
Select an energy range by typing the corresponding number (or type 'done' to finish): 3
Data for 60.00KEV_TO_80.00KEV stored in a dataframe named 'df60keVto80keV'.
Select an energy range by typing the corresponding number (or type 'done' to finish): 4
Data for 80.00KEV_TO_150.00KEV stored in a dataframe named 'df80keVto150keV'.
Select an energy range by typing the corresponding number (or type 'done' to finish): done
Would you like to see plots of the selected energy ranges? [yes/no]"""
# user will type here
"""yes
Dataframes for all selected energy ranges are available as global variables for further analysis.
- df20keVto40keV
- df40keVto60keV
- df60keVto80keV
- df80keVto150keV
"""
# you can use the above dataframes for further analysis, or save them as .csv files; uncomment if you want to do so
# df.to_csv('CZT1_20to40keV.csv',index=False) # here we are creating a csv file without indices
# etc...


#===== End of the Main Workflow Block ============================================================

#===== Analysis Block Starts Here ================================================================

#========================================================================================
#using the saved dataframes for further analysis after the end of the Main Workflow
#========================================================================================
rebinned_df = rebin_dataframe('df20keVto40keV', 60) #binsize is in seconds 
# the name of the newdata frame will be printed below, 
# example: Rebinned dataframe stored as global variable: df20keVto40keV_rebinned_60s
# this is the code to plot and examine the rebinned dataframe
# df20keVto40keV_rebinned_60s.plot(marker='.',markerfacecolor='black',yerr='STAT_ERR',logy=True)
plt.plot(marker='.',markerfacecolor='black',yerr='STAT_ERR',logy=True)
plt.legend(['20-40 keV'],loc='best')
plt.show()

# you can 
# (1) re-run the rebin_dataframe command with any one of the other saved dataframes
# (2) change the binsize as well. 
#==============================================================
