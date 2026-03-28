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
	"""Create Apr-Sep parity plots of peak SWE vs monthly mean streamflow for two SNOTEL sites."""
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

	fig.suptitle("Peak SWE vs Streamflow by Summer Month (PARLEYS and THAYNES Separate)", fontsize=13, y=1.06)
	fig.tight_layout()

	output = Path(output_path)
	output.parent.mkdir(parents=True, exist_ok=True)
	fig.savefig(output, dpi=300, bbox_inches="tight")
	plt.show()

	return peak_both
