from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_monthly_streamflow_apr_sep(
	monthly_flow,
	usgs_gage_id,
	watershed,
	output_path="./images/monthly_streamflow.png",
):
	"""Plot April-September monthly streamflow totals by year and save the figure."""
	plt.figure(figsize=(10, 6))
	for year in monthly_flow.index.get_level_values(0).unique():
		yearly_data = monthly_flow.loc[year]
		plt.plot(yearly_data.index, yearly_data.values, marker="o", label=str(year))

	plt.title(
		f"Monthly Streamflow (cfs) for April-September \n USGS Gage {usgs_gage_id} - {watershed}"
	)
	plt.xlabel("Month")
	plt.ylabel("Total Streamflow (cfs)")
	plt.xticks(range(4, 10), ["Apr", "May", "Jun", "Jul", "Aug", "Sep"])
	plt.legend(title="Year")
	plt.grid()
	plt.tight_layout()

	output = Path(output_path)
	output.parent.mkdir(parents=True, exist_ok=True)
	plt.savefig(output, dpi=300)
	plt.close()


def compare_peak_swe_vs_streamflow_by_month(
	data,
	site_code_map=None,
	snotel_dir="files/SNOTEL",
	output_path="images/peak_swe_vs_streamflow_by_month_dualsite.png",
):
	"""Create Apr-Sep parity plots of peak SWE vs monthly mean streamflow (cfs) for two SNOTEL sites."""
	if site_code_map is None:
		site_code_map = {"PARLEYS": "684_UT_SNTL", "THAYNES": "814_UT_SNTL"}

	peak_frames = []
	for site_name, site_code in site_code_map.items():
		sfile = Path(snotel_dir) / f"df_{site_code}_Utah_SNTL.csv"
		sraw = pd.read_csv(sfile)
		sraw["Date"] = pd.to_datetime(sraw["Date"])
		sraw["swe_in"] = sraw["Snow Water Equivalent (m) Start of Day Values"].fillna(0) * 39.3701
		sraw["WY"] = sraw["Date"].dt.year + (sraw["Date"].dt.month >= 10).astype(int)

		site_peak = sraw.groupby("WY", as_index=False)["swe_in"].max()
		site_peak.rename(columns={"swe_in": f"peak_swe_in_{site_name}"}, inplace=True)
		peak_frames.append(site_peak)

	peak_both = peak_frames[0].merge(peak_frames[1], on="WY", how="inner")

	flow = data.copy()
	flow.index = pd.to_datetime(flow.index)
	flow["WY"] = flow.index.year + (flow.index.month >= 10).astype(int)
	flow["month"] = flow.index.month

	monthly_flow = (
		flow[flow["month"].between(4, 9)]
		.groupby(["WY", "month"], as_index=False)["flow_cfs"]
		.mean()
		.rename(columns={"flow_cfs": "monthly_mean_flow_cfs"})
	)

	plot_df = monthly_flow.merge(
		peak_both[["WY", "peak_swe_in_PARLEYS", "peak_swe_in_THAYNES"]],
		on="WY",
		how="inner",
	)

	x_all = pd.concat([plot_df["peak_swe_in_PARLEYS"], plot_df["peak_swe_in_THAYNES"]], axis=0)
	y_all = plot_df["monthly_mean_flow_cfs"]
	x_pad = 0.05 * (x_all.max() - x_all.min()) if x_all.max() > x_all.min() else 1.0
	y_pad = 0.05 * (y_all.max() - y_all.min()) if y_all.max() > y_all.min() else 0.2
	xlim = (x_all.min() - x_pad, x_all.max() + x_pad)
	ylim = (max(0, y_all.min() - y_pad), y_all.max() + y_pad)

	month_names = {4: "April", 5: "May", 6: "June", 7: "July", 8: "August", 9: "September"}
	fig, axes = plt.subplots(2, 3, figsize=(15, 9), sharex=True, sharey=True)
	axes = axes.flatten()

	for i, month in enumerate(range(4, 10)):
		ax = axes[i]
		md = plot_df[plot_df["month"] == month].dropna()

		y = md["monthly_mean_flow_cfs"].values
		x_parleys = md["peak_swe_in_PARLEYS"].values
		x_thaynes = md["peak_swe_in_THAYNES"].values

		ax.scatter(x_parleys, y, color="royalblue", alpha=0.8, s=35)
		ax.scatter(x_thaynes, y, color="darkorange", alpha=0.8, s=35)

		if len(md) >= 2 and np.std(x_parleys) > 0:
			slope_p, intercept_p = np.polyfit(x_parleys, y, 1)
			xline_p = np.linspace(x_parleys.min(), x_parleys.max(), 100)
			yline_p = slope_p * xline_p + intercept_p
			ax.plot(xline_p, yline_p, color="royalblue", linewidth=1.8)

			yhat_p = slope_p * x_parleys + intercept_p
			ss_res_p = np.sum((y - yhat_p) ** 2)
			ss_tot_p = np.sum((y - y.mean()) ** 2)
			r2_p = 1 - (ss_res_p / ss_tot_p) if ss_tot_p != 0 else np.nan
			ax.text(0.03, 0.93, f"PARLEYS $R^2$={r2_p:.2f}", transform=ax.transAxes, va="top", fontsize=8, color="royalblue")

		if len(md) >= 2 and np.std(x_thaynes) > 0:
			slope_t, intercept_t = np.polyfit(x_thaynes, y, 1)
			xline_t = np.linspace(x_thaynes.min(), x_thaynes.max(), 100)
			yline_t = slope_t * xline_t + intercept_t
			ax.plot(xline_t, yline_t, color="darkorange", linewidth=1.8)

			yhat_t = slope_t * x_thaynes + intercept_t
			ss_res_t = np.sum((y - yhat_t) ** 2)
			ss_tot_t = np.sum((y - y.mean()) ** 2)
			r2_t = 1 - (ss_res_t / ss_tot_t) if ss_tot_t != 0 else np.nan
			ax.text(0.03, 0.84, f"THAYNES $R^2$={r2_t:.2f}", transform=ax.transAxes, va="top", fontsize=8, color="darkorange")

		ax.set_title(month_names[month])
		ax.grid(alpha=0.25)
		ax.set_xlim(xlim)
		ax.set_ylim(ylim)
		if i % 3 == 0:
			ax.set_ylabel("Monthly Mean Streamflow (cfs)")
		if i >= 3:
			ax.set_xlabel("Peak SWE (in)")

	legend_handles = [
		plt.Line2D([0], [0], marker="o", color="royalblue", linestyle="-", linewidth=1.8, markersize=6, label="PARLEYS"),
		plt.Line2D([0], [0], marker="o", color="darkorange", linestyle="-", linewidth=1.8, markersize=6, label="THAYNES"),
	]
	fig.legend(handles=legend_handles, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.02))

	fig.suptitle("Peak SWE vs Monthly Mean Streamflow by Summer Month (PARLEYS and THAYNES)", fontsize=13, y=1.06)
	fig.tight_layout()

	output = Path(output_path)
	output.parent.mkdir(parents=True, exist_ok=True)
	fig.savefig(output, dpi=300, bbox_inches="tight")
	plt.show()

	return peak_both


def plot_monthly_streamflow_boxplot(
	data,
	output_path="./images/streamflow_monthly_volume_boxplots.png",
	show_plot=True,
):
	"""Plot Apr-Sep monthly mean streamflow distributions (cfs) in separate subplots."""
	working = data.copy()

	if "Date" in working.columns:
		dates = pd.to_datetime(working["Date"])
	elif isinstance(working.index, pd.DatetimeIndex):
		dates = pd.to_datetime(working.index)
	else:
		raise ValueError("Data must include a 'Date' column or a DatetimeIndex.")

	working["year"] = dates.year
	working["month"] = dates.month
	working = working[working["month"].between(4, 9)].copy()

	# Compute each water-year month's mean daily flow (cfs).
	monthly_mean = (
		working.groupby(["year", "month"], as_index=False)["flow_cfs"]
		.mean()
		.rename(columns={"flow_cfs": "monthly_mean_cfs"})
	)

	month_names = {
		4: "April",
		5: "May",
		6: "June",
		7: "July",
		8: "August",
		9: "September",
	}

	fig, axes = plt.subplots(2, 3, figsize=(8, 5), sharey=True)
	axes = axes.flatten()

	for i, month in enumerate(range(4, 10)):
		ax = axes[i]
		month_vals = monthly_mean.loc[
			monthly_mean["month"] == month,
			"monthly_mean_cfs",
		].dropna()

		if len(month_vals) > 0:
			ax.boxplot(
				month_vals.values,
				widths=0.28,
				patch_artist=True,
				boxprops=dict(facecolor="blue", color="navy", alpha=1.0),
				whiskerprops=dict(color="navy"),
				capprops=dict(color="navy"),
				medianprops=dict(color="white", linewidth=1.5),
				flierprops=dict(
					marker="o",
					markerfacecolor="blue",
					markeredgecolor="navy",
					markersize=4,
					alpha=0.6,
				),
			)
		else:
			ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)

		ax.set_title(month_names[month])
		ax.set_xticks([])
		ax.set_xlim(0.85, 1.15)
		ax.grid(False)
		if i % 3 == 0:
			ax.set_ylabel("Monthly Mean Flow (cfs)")

	fig.suptitle("Monthly Historical Mean Streamflow by Month", y=0.98)
	fig.subplots_adjust(left=0.07, right=0.98, top=0.90, bottom=0.08, wspace=0.14, hspace=0.22)

	if output_path:
		output = Path(output_path)
		output.parent.mkdir(parents=True, exist_ok=True)
		fig.savefig(output, dpi=300, bbox_inches="tight")

	if show_plot:
		plt.show()
	else:
		plt.close(fig)

	return fig, axes